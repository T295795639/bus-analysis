import ast
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
    autocommit=False,
)

OUT_DIR = Path(__file__).resolve().parents[2] / "repair_all_report"


def parse_path(path):
    if not path:
        return []
    try:
        return json.loads(path)
    except json.JSONDecodeError:
        return ast.literal_eval(path)


def dump_path(points):
    return json.dumps(points, ensure_ascii=False, separators=(",", ":"))


def reverse_path(path):
    pts = parse_path(path)
    pts.reverse()
    return dump_path(pts)


def concat_paths(paths):
    out = []
    for path in paths:
        pts = parse_path(path)
        if not pts:
            continue
        if not out:
            out.extend(pts)
        elif out[-1] == pts[0]:
            out.extend(pts[1:])
        else:
            out.extend(pts)
    return dump_path(out)


def raw_id(section_id):
    return section_id


def fetch_all(cur, sql, args=None):
    cur.execute(sql, args or ())
    return cur.fetchall()


def route_key(route_name):
    return route_name.split("路", 1)[0]


def load_routes(cur):
    return fetch_all(cur, "SELECT route_id, route_name, is_up_or_down FROM route ORDER BY route_id")


def load_route_key_counts(cur):
    rows = fetch_all(cur, "SELECT route_id, route_name FROM route")
    counts = {}
    for row in rows:
        key = route_key(row["route_name"])
        counts.setdefault(key, []).append(row["route_id"])
    return counts


def load_sections(cur, key):
    return fetch_all(
        cur,
        """
        SELECT *
        FROM section
        WHERE route_number IN (%s, %s)
        ORDER BY route_number, CAST(SUBSTRING_INDEX(section_id, '_', -1) AS UNSIGNED)
        """,
        (f"{key}_up", f"{key}_down"),
    )


def load_route_stations(cur, route_id):
    return fetch_all(
        cur,
        """
        SELECT rs.station_id, s.station_name, s.lng, s.lat
        FROM route_station rs
        JOIN station s ON s.station_id = rs.station_id
        WHERE rs.route_id = %s
          AND rs.station_id > 10000
          AND s.lng IS NOT NULL
          AND s.lat IS NOT NULL
        ORDER BY rs.id
        """,
        (route_id,),
    )


def endpoint_chain(sections):
    chain = []
    for sec in sorted(sections, key=lambda s: int(s["section_id"].split("_")[-1])):
        chain.append((sec["start_station_id"], sec["section_id"], "start"))
        chain.append((sec["end_station_id"], sec["section_id"], "end"))
    return chain


def first_real_station(sections):
    for sid, _, _ in endpoint_chain(sections):
        if sid and sid > 10000:
            return sid
    return None


def group_sections_by_route_number(sections):
    grouped = {}
    for sec in sections:
        grouped.setdefault(sec["route_number"], []).append(sec)
    return grouped


def station_names(route_stations):
    return {row["station_id"]: row["station_name"] for row in route_stations}


def find_source_for_pair(grouped_sections, start_id, end_id):
    best = None
    for route_number, sections in grouped_sections.items():
        sections = sorted(sections, key=lambda s: int(s["section_id"].split("_")[-1]))
        chain = endpoint_chain(sections)
        positions_start = [i for i, (sid, _, _) in enumerate(chain) if sid == start_id]
        positions_end = [i for i, (sid, _, _) in enumerate(chain) if sid == end_id]
        for ps in positions_start:
            for pe in positions_end:
                if ps == pe:
                    continue
                lo, hi = sorted((ps, pe))
                source_indices = []
                ok = True
                for pos in range(lo // 2, (hi + 1) // 2):
                    if pos < 0 or pos >= len(sections):
                        ok = False
                        break
                    source_indices.append(pos)
                if not ok or not source_indices:
                    continue
                source_ids = [sections[i]["section_id"] for i in source_indices]
                reverse = ps > pe
                score = len(source_ids)
                if best is None or score < best["score"]:
                    best = {
                        "route_number": route_number,
                        "source_ids": source_ids,
                        "reverse": reverse,
                        "score": score,
                    }
    return best


def build_new_sections(route_number, desired_stations, grouped_sections):
    names = station_names(desired_stations)
    source_lookup = {
        sec["section_id"]: sec
        for items in grouped_sections.values()
        for sec in items
    }
    rows = []
    for idx in range(len(desired_stations) - 1):
        start = desired_stations[idx]
        end = desired_stations[idx + 1]
        source = find_source_for_pair(grouped_sections, start["station_id"], end["station_id"])
        if not source:
            return None, f"无法映射相邻站点: {start['station_name']} -> {end['station_name']}"

        ordered = list(reversed(source["source_ids"])) if source["reverse"] else source["source_ids"]
        paths = [
            reverse_path(source_lookup[sid]["path"]) if source["reverse"] else source_lookup[sid]["path"]
            for sid in ordered
        ]
        rows.append(
            {
                "section_id": f"{route_number}_{idx:02d}",
                "raw_section_id": f"{route_number}_{idx:02d}",
                "route_number": route_number,
                "direction": route_number.split("_")[-1],
                "section_name": f"{names[start['station_id']]} -> {names[end['station_id']]}",
                "start_station_id": start["station_id"],
                "end_station_id": end["station_id"],
                "source_ids": ordered,
                "source_raw_ids": [raw_id(sid) for sid in ordered],
                "reverse": source["reverse"],
                "path": concat_paths(paths),
            }
        )
    return rows, None


def load_driving_grouped(cur, raw_ids):
    if not raw_ids:
        return {}
    placeholders = ",".join(["%s"] * len(raw_ids))
    rows = fetch_all(
        cur,
        f"""
        SELECT section_id, car_id, path, start_date_time, end_date_time, duration_seconds
        FROM section_driving
        WHERE section_id IN ({placeholders})
        ORDER BY car_id, start_date_time, id
        """,
        raw_ids,
    )
    grouped = {}
    for row in rows:
        grouped.setdefault(row["section_id"], []).append(row)
    return grouped


def build_driving_rows(cur, section_rows):
    all_raw_ids = sorted({rid for row in section_rows for rid in row["source_raw_ids"]})
    grouped = load_driving_grouped(cur, all_raw_ids)
    new_rows = []
    stats = []
    for row in section_rows:
        chain_sources = row["source_raw_ids"]
        if row["reverse"]:
            # Keep source section order as path order, but reverse each path. Do not reverse the list.
            chain_sources = row["source_raw_ids"]

        if len(chain_sources) == 1:
            rows = grouped.get(chain_sources[0], [])
            for item in rows:
                path = reverse_path(item["path"]) if row["reverse"] else item["path"]
                new_rows.append((row["raw_section_id"], item["car_id"], path, item["start_date_time"], item["end_date_time"], item["duration_seconds"]))
            stats.append((row["raw_section_id"], "+".join(chain_sources), len(rows), len(rows)))
            continue

        by_car = {}
        for source in chain_sources:
            for item in grouped.get(source, []):
                by_car.setdefault(item["car_id"], {}).setdefault(source, []).append(item)

        inserted = 0
        source_count = sum(len(grouped.get(source, [])) for source in chain_sources)
        max_gap_seconds = 300
        for _, per_source in by_car.items():
            first_source = chain_sources[0]
            for first in per_source.get(first_source, []):
                chain = [first]
                prev = first
                ok = True
                for source in chain_sources[1:]:
                    candidates = [item for item in per_source.get(source, []) if item["start_date_time"] >= prev["end_date_time"]]
                    candidates.sort(key=lambda item: item["start_date_time"])
                    if not candidates:
                        ok = False
                        break
                    nxt = candidates[0]
                    if (nxt["start_date_time"] - prev["end_date_time"]).total_seconds() > max_gap_seconds:
                        ok = False
                        break
                    chain.append(nxt)
                    prev = nxt
                if not ok:
                    continue
                path = concat_paths([item["path"] for item in chain])
                if row["reverse"]:
                    path = reverse_path(path)
                duration = sum(item["duration_seconds"] or 0 for item in chain)
                new_rows.append((row["raw_section_id"], chain[0]["car_id"], path, chain[0]["start_date_time"], chain[-1]["end_date_time"], duration))
                inserted += 1
        stats.append((row["raw_section_id"], "+".join(chain_sources), source_count, inserted))
    return new_rows, stats


def rebuild_summary(cur, route_number):
    raw_prefix = route_number
    cur.execute("DELETE FROM section_driving_summary WHERE section_id LIKE %s", (f"{raw_prefix}\\_%",))
    cur.execute(
        """
        INSERT INTO section_driving_summary(section_id, avg_duration_seconds, record_count)
        SELECT
            CASE
                WHEN section_id LIKE '%%\\_up\\_%%' OR section_id LIKE '%%\\_down\\_%%' THEN section_id
                WHEN section_id LIKE '%%\\_up%%' THEN CONCAT(SUBSTRING_INDEX(section_id, '_up', 1), '_up_', LPAD(SUBSTRING_INDEX(section_id, '_up', -1), 2, '0'))
                WHEN section_id LIKE '%%\\_down%%' THEN CONCAT(SUBSTRING_INDEX(section_id, '_down', 1), '_down_', LPAD(SUBSTRING_INDEX(section_id, '_down', -1), 2, '0'))
                ELSE section_id
            END AS section_id,
            AVG(duration_seconds),
            COUNT(*)
        FROM section_driving
        WHERE section_id LIKE %s
        GROUP BY 1
        """,
        (f"{raw_prefix}%",),
    )


def main():
    OUT_DIR.mkdir(exist_ok=True)
    conn = pymysql.connect(**DB)
    report = []
    changed = 0
    skipped = 0
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            routes = load_routes(cur)
            key_counts = load_route_key_counts(cur)
            for route in routes:
                key = route_key(route["route_name"])
                if len(key_counts.get(key, [])) > 1:
                    skipped += 1
                    report.append({"route_id": route["route_id"], "route_name": route["route_name"], "status": "skip", "reason": f"线路号 {key} 对应多个 route_id"})
                    continue

                sections = load_sections(cur, key)
                if not sections:
                    skipped += 1
                    report.append({"route_id": route["route_id"], "route_name": route["route_name"], "status": "skip", "reason": "无 section"})
                    continue
                grouped = group_sections_by_route_number(sections)
                route_stations = load_route_stations(cur, route["route_id"])
                if len(route_stations) < 2:
                    skipped += 1
                    report.append({"route_id": route["route_id"], "route_name": route["route_name"], "status": "skip", "reason": "route_station真实站点不足"})
                    continue

                selected = None
                for rn, items in grouped.items():
                    if first_real_station(items) == route_stations[0]["station_id"]:
                        selected = rn
                        break
                if not selected:
                    skipped += 1
                    report.append({"route_id": route["route_id"], "route_name": route["route_name"], "status": "skip", "reason": "无法匹配方向首站"})
                    continue

                current_chain_ids = []
                seen = set()
                for sid, _, _ in endpoint_chain(grouped[selected]):
                    if sid and sid > 10000 and sid not in seen:
                        seen.add(sid)
                        current_chain_ids.append(sid)
                desired_ids = [s["station_id"] for s in route_stations]
                if current_chain_ids == desired_ids:
                    report.append({"route_id": route["route_id"], "route_name": route["route_name"], "status": "ok", "reason": "无需修复"})
                    continue

                new_sections, reason = build_new_sections(selected, route_stations, grouped)
                if reason:
                    skipped += 1
                    report.append({"route_id": route["route_id"], "route_name": route["route_name"], "status": "skip", "reason": reason})
                    continue

                driving_rows, driving_stats = build_driving_rows(cur, new_sections)
                cur.execute("DELETE FROM section WHERE route_number = %s", (selected,))
                cur.executemany(
                    """
                    INSERT INTO section(section_id,start_station_id,end_station_id,direction,section_name,path,route_number)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    [(r["section_id"], r["start_station_id"], r["end_station_id"], r["direction"], r["section_name"], r["path"], r["route_number"]) for r in new_sections],
                )
                cur.execute("DELETE FROM section_driving WHERE section_id LIKE %s", (f"{selected}%",))
                if driving_rows:
                    cur.executemany(
                        """
                        INSERT INTO section_driving(section_id,car_id,path,start_date_time,end_date_time,duration_seconds)
                        VALUES (%s,%s,%s,%s,%s,%s)
                        """,
                        driving_rows,
                    )
                rebuild_summary(cur, selected)
                changed += 1
                report.append({
                    "route_id": route["route_id"],
                    "route_name": route["route_name"],
                    "status": "changed",
                    "route_number": selected,
                    "old_station_count": len(current_chain_ids),
                    "new_station_count": len(desired_ids),
                    "new_section_count": len(new_sections),
                    "new_driving_rows": len(driving_rows),
                    "reason": "; ".join(f"{s[0]}:{s[3]}/{s[2]}" for s in driving_stats[:6]),
                })
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    with (OUT_DIR / "repair_all_report.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = ["route_id", "route_name", "status", "route_number", "old_station_count", "new_station_count", "new_section_count", "new_driving_rows", "reason"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in report:
            writer.writerow({field: row.get(field, "") for field in fields})
    print(f"changed={changed}, skipped={skipped}, report={OUT_DIR / 'repair_all_report.csv'}")


if __name__ == "__main__":
    main()
