import json
import ast
from datetime import datetime

import pymysql


DB = dict(
    host="localhost",
    port=3306,
    user="root",
    password="13603870586A8",
    database="bus_analysis",
    charset="utf8mb4",
    autocommit=False,
)

SOURCE_SECTION_TABLE = "section_backup_234_20260707_072832"
SOURCE_DRIVING_TABLE = "section_driving_backup_234_20260707_072832"


def reverse_path(path):
    if not path:
        return None
    pts = parse_path(path)
    pts.reverse()
    return json.dumps(pts, ensure_ascii=False, separators=(",", ":"))


def concat_paths(paths):
    out = []
    for path in paths:
        if not path:
            continue
        pts = parse_path(path)
        if not out:
            out.extend(pts)
        elif pts and out[-1] == pts[0]:
            out.extend(pts[1:])
        else:
            out.extend(pts)
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


def parse_path(path):
    try:
        return json.loads(path)
    except json.JSONDecodeError:
        return ast.literal_eval(path)


def raw_id(section_id):
    return section_id


def norm_id(raw_section_id):
    if "_down_" in raw_section_id or "_up_" in raw_section_id:
        return raw_section_id
    if "_down" in raw_section_id:
        route_no, seq = raw_section_id.split("_down", 1)
        return f"{route_no}_down_{int(seq):02d}"
    if "_up" in raw_section_id:
        route_no, seq = raw_section_id.split("_up", 1)
        return f"{route_no}_up_{int(seq):02d}"
    return raw_section_id


def fetch_all(cur, sql, args=None):
    cur.execute(sql, args or ())
    return cur.fetchall()


def load_repair_specs(cur):
    sections = {
        row["section_id"]: row
        for row in fetch_all(
            cur,
            f"SELECT * FROM {SOURCE_SECTION_TABLE} WHERE route_number IN ('234_up','234_down')",
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
        row["station_id"]: row["station_name"]
        for row in fetch_all(
            cur,
            "SELECT station_id, station_name FROM station WHERE station_id IN (%s)"
            % ",".join(map(str, station_ids)),
        )
    }

    return sections, station_names, [
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


def build_section_rows(sections, station_names, specs):
    rows = []
    for seq, start, end, sources, reverse, source_type in specs:
        ordered = sources
        paths = [
            reverse_path(sections[source]["path"]) if reverse else sections[source]["path"]
            for source in ordered
        ]
        rows.append(
            dict(
                section_id=f"234_down_{seq:02d}",
                raw_section_id=f"234_down_{seq:02d}",
                route_number="234_down",
                direction="down",
                section_name=f"{station_names[start]} -> {station_names[end]}",
                start_station_id=start,
                end_station_id=end,
                source_sections=sources,
                reverse=reverse,
                source_type=source_type,
                path=concat_paths(paths),
            )
        )
    return rows


def load_driving_rows(cur, source_raw_ids):
    if not source_raw_ids:
        return {}
    placeholders = ",".join(["%s"] * len(source_raw_ids))
    rows = fetch_all(
        cur,
        f"""
        SELECT section_id, car_id, path, start_date_time, end_date_time, duration_seconds
        FROM {SOURCE_DRIVING_TABLE}
        WHERE section_id IN ({placeholders})
        ORDER BY car_id, start_date_time, id
        """,
        source_raw_ids,
    )
    grouped = {}
    for row in rows:
        grouped.setdefault(row["section_id"], []).append(row)
    return grouped


def build_driving_rows(cur, section_rows):
    all_source_ids = sorted({raw_id(source) for row in section_rows for source in row["source_sections"]})
    grouped = load_driving_rows(cur, all_source_ids)
    new_rows = []
    stats = []

    for row in section_rows:
        target = row["raw_section_id"]
        raw_sources = [raw_id(source) for source in row["source_sections"]]
        chain_sources = list(reversed(raw_sources)) if row["reverse"] else raw_sources

        if len(chain_sources) == 1:
            source = chain_sources[0]
            rows = grouped.get(source, [])
            for item in rows:
                path = reverse_path(item["path"]) if row["reverse"] else item["path"]
                new_rows.append(
                    (
                        target,
                        item["car_id"],
                        path,
                        item["start_date_time"],
                        item["end_date_time"],
                        item["duration_seconds"],
                    )
                )
            stats.append((target, "+".join(raw_sources), len(rows), len(rows), "single"))
            continue

        by_car = {}
        for source in chain_sources:
            for item in grouped.get(source, []):
                by_car.setdefault(item["car_id"], {}).setdefault(source, []).append(item)

        inserted = 0
        source_count = sum(len(grouped.get(source, [])) for source in chain_sources)
        max_gap_seconds = 300
        for _, per_source in by_car.items():
            used_ids = set()
            for first in per_source.get(chain_sources[0], []):
                chain = [first]
                prev = first
                ok = True
                for source in chain_sources[1:]:
                    candidates = [
                        item
                        for item in per_source.get(source, [])
                        if id(item) not in used_ids and item["start_date_time"] >= prev["end_date_time"]
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
                if not ok:
                    continue
                for item in chain:
                    used_ids.add(id(item))

                paths = [item["path"] for item in chain]
                path = concat_paths(paths)
                if row["reverse"]:
                    path = reverse_path(path)
                duration = sum((item["duration_seconds"] or 0) for item in chain)
                new_rows.append(
                    (
                        target,
                        chain[0]["car_id"],
                        path,
                        chain[0]["start_date_time"],
                        chain[-1]["end_date_time"],
                        duration,
                    )
                )
                inserted += 1
        stats.append((target, "+".join(raw_sources), source_count, inserted, "chain_reverse" if row["reverse"] else "chain"))

    return new_rows, stats


def main():
    backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            print(f"Creating in-database backup tables with suffix {backup_suffix}...")
            cur.execute(
                f"CREATE TABLE section_backup_234_{backup_suffix} AS "
                "SELECT * FROM section WHERE route_number IN ('234_down','234_up')"
            )
            cur.execute(
                f"CREATE TABLE section_driving_backup_234_{backup_suffix} AS "
                "SELECT * FROM section_driving WHERE section_id LIKE '234\\_down%' OR section_id LIKE '234\\_up%'"
            )
            cur.execute(
                f"CREATE TABLE section_driving_summary_backup_234_{backup_suffix} AS "
                "SELECT * FROM section_driving_summary WHERE section_id LIKE '234\\_down\\_%' OR section_id LIKE '234\\_up\\_%'"
            )

            sections, station_names, specs = load_repair_specs(cur)
            section_rows = build_section_rows(sections, station_names, specs)
            driving_rows, driving_stats = build_driving_rows(cur, section_rows)

            print("Applying section repair...")
            cur.execute("DELETE FROM section WHERE route_number = '234_down'")
            cur.executemany(
                """
                INSERT INTO section(section_id,start_station_id,end_station_id,direction,section_name,path,route_number)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                [
                    (
                        row["section_id"],
                        row["start_station_id"],
                        row["end_station_id"],
                        row["direction"],
                        row["section_name"],
                        row["path"],
                        row["route_number"],
                    )
                    for row in section_rows
                ],
            )

            print("Replacing 234_down section_driving rows...")
            cur.execute("DELETE FROM section_driving WHERE section_id LIKE '234\\_down%'")
            if driving_rows:
                cur.executemany(
                    """
                    INSERT INTO section_driving(section_id,car_id,path,start_date_time,end_date_time,duration_seconds)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    """,
                    driving_rows,
                )

            print("Rebuilding 234_down section_driving_summary rows...")
            cur.execute("DELETE FROM section_driving_summary WHERE section_id LIKE '234\\_down\\_%'")
            cur.execute(
                """
                INSERT INTO section_driving_summary(section_id, avg_duration_seconds, record_count)
                SELECT
                    CASE
                        WHEN section_id LIKE '%\\_down\\_%' THEN section_id
                        WHEN section_id LIKE '%\\_down%' THEN CONCAT(SUBSTRING_INDEX(section_id, '_down', 1), '_down_', LPAD(SUBSTRING_INDEX(section_id, '_down', -1), 2, '0'))
                        ELSE section_id
                    END AS section_id,
                    AVG(duration_seconds) AS avg_duration_seconds,
                    COUNT(*) AS record_count
                FROM section_driving
                WHERE section_id LIKE '234\\_down%'
                GROUP BY 1
                """
            )

            conn.commit()
            print("Committed.")
            print("\nDriving conversion stats:")
            for target, sources, source_count, inserted, strategy in driving_stats:
                print(f"{target}: {strategy}, sources={sources}, source_rows={source_count}, inserted_rows={inserted}")
            print("\nBackup tables:")
            print(f"section_backup_234_{backup_suffix}")
            print(f"section_driving_backup_234_{backup_suffix}")
            print(f"section_driving_summary_backup_234_{backup_suffix}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
