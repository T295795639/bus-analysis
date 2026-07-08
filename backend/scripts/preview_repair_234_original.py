import csv
import json
from pathlib import Path

import pymysql


DB = dict(
    host="localhost",
    port=3306,
    user="root",
    password="13603870586A8",
    database="bus_analysis",
    charset="utf8mb4",
)

ROUTE_ID = 234
OUT_DIR = Path(__file__).resolve().parents[2] / "repair_234_original_preview"


def reverse_path(path):
    if not path:
        return None
    pts = json.loads(path)
    pts.reverse()
    return json.dumps(pts, ensure_ascii=False, separators=(",", ":"))


def concat_paths(paths):
    out = []
    for path in paths:
        if not path:
            continue
        pts = json.loads(path)
        if not out:
            out.extend(pts)
        elif pts and out[-1] == pts[0]:
            out.extend(pts[1:])
        else:
            out.extend(pts)
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


def raw_id(section_id):
    return section_id


def norm_id(raw_section_id):
    if "_up" in raw_section_id:
        route_no, seq = raw_section_id.split("_up", 1)
        return f"{route_no}_up_{int(seq):02d}"
    if "_down" in raw_section_id:
        route_no, seq = raw_section_id.split("_down", 1)
        return f"{route_no}_down_{int(seq):02d}"
    return raw_section_id


def fetch_all(conn, sql, args=None):
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(sql, args or ())
        return cur.fetchall()


def build_repair_sections(conn):
    sections = {
        r["section_id"]: r
        for r in fetch_all(
            conn,
            "SELECT * FROM section WHERE route_number IN ('234_up','234_down')",
        )
    }
    station_ids = [
        118546,
        118545,
        118544,
        120131,
        144453,
        144454,
        144455,
        144456,
        144457,
        144458,
        144467,
        144459,
        144460,
        144462,
    ]
    station_names = {
        r["station_id"]: r["station_name"]
        for r in fetch_all(
            conn,
            "SELECT station_id, station_name FROM station WHERE station_id IN (%s)"
            % ",".join(map(str, station_ids)),
        )
    }

    # source_sections are normalized section.section_id values. If reverse=True,
    # source path is reversed and source order is reversed before concatenation.
    specs = [
        (0, 118546, 118545, ["234_down_00"], False, "copy_down"),
        (1, 118545, 118544, ["234_down_01"], False, "copy_down"),
        (2, 118544, 120131, ["234_down_02", "234_down_03"], False, "merge_down"),
        (3, 120131, 144453, ["234_up_15", "234_up_14"], True, "reverse_merge_up"),
        (4, 144453, 144454, ["234_up_13"], True, "reverse_up"),
        (5, 144454, 144455, ["234_up_12", "234_up_11", "234_up_10"], True, "reverse_merge_up"),
        (6, 144455, 144456, ["234_up_09", "234_up_08"], True, "reverse_merge_up"),
        (7, 144456, 144457, ["234_up_07"], True, "reverse_up"),
        (8, 144457, 144458, ["234_down_10"], False, "copy_down"),
        (9, 144458, 144467, ["234_up_04"], True, "reverse_up"),
        (10, 144467, 144459, ["234_up_03", "234_up_02"], True, "reverse_merge_up"),
        (11, 144459, 144460, ["234_up_01"], True, "reverse_up"),
        (12, 144460, 144462, ["234_up_00"], True, "reverse_up"),
    ]

    repaired = []
    for seq, start, end, sources, reverse, source_type in specs:
        ordered = sources
        paths = [
            reverse_path(sections[source]["path"]) if reverse else sections[source]["path"]
            for source in ordered
        ]
        repaired.append(
            {
                "section_id": f"234_down_{seq:02d}",
                "route_number": "234_down",
                "direction": "down",
                "section_name": f"{station_names[start]} -> {station_names[end]}",
                "start_station_id": start,
                "start_station_name": station_names[start],
                "end_station_id": end,
                "end_station_name": station_names[end],
                "source_sections": sources,
                "source_raw_ids": [raw_id(source) for source in sources],
                "reverse": reverse,
                "source_type": source_type,
                "path": concat_paths(paths),
            }
        )
    return repaired


def group_records_by_source(conn, source_raw_ids):
    if not source_raw_ids:
        return {}
    placeholders = ",".join(["%s"] * len(source_raw_ids))
    rows = fetch_all(
        conn,
        f"""
        SELECT id, section_id, car_id, path, start_date_time, end_date_time, duration_seconds
        FROM section_driving
        WHERE section_id IN ({placeholders})
        ORDER BY car_id, start_date_time, id
        """,
        source_raw_ids,
    )
    grouped = {}
    for row in rows:
        grouped.setdefault(row["section_id"], []).append(row)
    return grouped


def preview_driving_for_section(conn, repaired_section):
    source_raw_ids = repaired_section["source_raw_ids"]
    grouped = group_records_by_source(conn, source_raw_ids)

    if len(source_raw_ids) == 1:
        rows = grouped.get(source_raw_ids[0], [])
        return {
            "new_section_id": repaired_section["section_id"],
            "strategy": "copy_single_source_reverse_path" if repaired_section["reverse"] else "copy_single_source",
            "source_raw_ids": source_raw_ids,
            "source_record_count": len(rows),
            "preview_insert_count": len(rows),
            "notes": "可一对一复制；如 reverse=true，需要反转 path，但时间和 duration 保持原记录。",
        }

    # Multi-source preview: pair/chain by car_id and temporal adjacency.
    source_lists = [grouped.get(source_id, []) for source_id in source_raw_ids]
    source_counts = [len(items) for items in source_lists]
    by_car = {}
    for source_id, rows in zip(source_raw_ids, source_lists):
        for row in rows:
            by_car.setdefault(row["car_id"], {}).setdefault(source_id, []).append(row)

    chained_count = 0
    incomplete_count = 0
    max_gap_seconds = 300
    for _, per_source in by_car.items():
        first_source = source_raw_ids[0]
        for first in per_source.get(first_source, []):
            chain = [first]
            prev = first
            ok = True
            for source_id in source_raw_ids[1:]:
                candidates = [
                    item
                    for item in per_source.get(source_id, [])
                    if item["start_date_time"] >= prev["end_date_time"]
                ]
                candidates.sort(key=lambda item: item["start_date_time"])
                if not candidates:
                    ok = False
                    break
                nxt = candidates[0]
                gap = (nxt["start_date_time"] - prev["end_date_time"]).total_seconds()
                if gap > max_gap_seconds:
                    ok = False
                    break
                chain.append(nxt)
                prev = nxt
            if ok and len(chain) == len(source_raw_ids):
                chained_count += 1
            else:
                incomplete_count += 1

    return {
        "new_section_id": repaired_section["section_id"],
        "strategy": "chain_by_car_time_reverse_path" if repaired_section["reverse"] else "chain_by_car_time",
        "source_raw_ids": source_raw_ids,
        "source_record_count": sum(source_counts),
        "source_counts": dict(zip(source_raw_ids, source_counts)),
        "preview_insert_count": chained_count,
        "incomplete_chain_count": incomplete_count,
        "notes": "多源路段不能简单 update；需要按 car_id + 时间邻接拼接 path、start/end、duration。",
    }


def write_outputs(conn, repaired_sections):
    OUT_DIR.mkdir(exist_ok=True)

    with (OUT_DIR / "section_repair_preview.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "section_id",
                "section_name",
                "start_station_id",
                "start_station_name",
                "end_station_id",
                "end_station_name",
                "source_sections",
                "source_raw_ids",
                "reverse",
                "source_type",
            ],
        )
        writer.writeheader()
        for row in repaired_sections:
            writer.writerow(
                {
                    **{k: row[k] for k in writer.fieldnames if k in row},
                    "source_sections": "+".join(row["source_sections"]),
                    "source_raw_ids": "+".join(row["source_raw_ids"]),
                }
            )

    driving_preview = [preview_driving_for_section(conn, section) for section in repaired_sections]
    with (OUT_DIR / "section_driving_repair_preview.json").open("w", encoding="utf-8") as f:
        json.dump(driving_preview, f, ensure_ascii=False, indent=2, default=str)

    with (OUT_DIR / "section_repair_preview.sql").open("w", encoding="utf-8") as f:
        f.write("-- PREVIEW ONLY. Do not execute until section_driving strategy is confirmed.\n")
        f.write("START TRANSACTION;\n")
        f.write("DELETE FROM section WHERE route_number = '234_down';\n")
        for row in repaired_sections:
            esc = lambda value: "NULL" if value is None else "'" + str(value).replace("'", "''") + "'"
            f.write(
                "INSERT INTO section(section_id,start_station_id,end_station_id,direction,section_name,path,route_number) VALUES "
            )
            f.write(
                "("
                + ",".join(
                    [
                        esc(row["section_id"]),
                        str(row["start_station_id"]),
                        str(row["end_station_id"]),
                        esc(row["direction"]),
                        esc(row["section_name"]),
                        esc(row["path"]),
                        esc(row["route_number"]),
                    ]
                )
                + ");\n"
            )
        f.write("ROLLBACK;\n")

    print(f"Output directory: {OUT_DIR}")
    print("Generated:")
    print(" - section_repair_preview.csv")
    print(" - section_repair_preview.sql")
    print(" - section_driving_repair_preview.json")
    print("\nDriving preview summary:")
    for item in driving_preview:
        print(
            f"{item['new_section_id']}: {item['strategy']}, "
            f"sources={'+'.join(item['source_raw_ids'])}, "
            f"source_rows={item['source_record_count']}, "
            f"preview_rows={item['preview_insert_count']}"
        )


def main():
    conn = pymysql.connect(**DB)
    try:
        repaired_sections = build_repair_sections(conn)
        write_outputs(conn, repaired_sections)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
