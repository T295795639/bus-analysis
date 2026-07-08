from bisect import bisect_left, bisect_right

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

MAX_GAP_SECONDS = 1800
MAX_FALLBACK_GAP_SECONDS = 300
BATCH_SIZE = 2000
ROUTE_SUFFIX = "\u8def"
UP = "\u4e0a\u884c"
DOWN = "\u4e0b\u884c"


def fetch_all(cur, sql, args=None):
    cur.execute(sql, args or ())
    return cur.fetchall()


def normalize_section_id(section_id):
    if not section_id:
        return None
    if "_up_" in section_id or "_down_" in section_id:
        return section_id
    if "_up" in section_id:
        prefix, seq = section_id.rsplit("_up", 1)
        return f"{prefix}_up_{int(seq):02d}"
    if "_down" in section_id:
        prefix, seq = section_id.rsplit("_down", 1)
        return f"{prefix}_down_{int(seq):02d}"
    return section_id


def route_name_from_number(route_number):
    if not route_number:
        return None
    return f"{route_number.split('_', 1)[0]}{ROUTE_SUFFIX}"


def ensure_schema(cur):
    columns = {row[0] for row in fetch_all(cur, "SHOW COLUMNS FROM station_parking")}
    ddl = [
        ("route_number", "ALTER TABLE station_parking ADD COLUMN route_number VARCHAR(50) NULL COMMENT 'inferred route direction key' AFTER duration_seconds"),
        ("route_id", "ALTER TABLE station_parking ADD COLUMN route_id INT NULL COMMENT 'inferred route id' AFTER route_number"),
        ("route_name", "ALTER TABLE station_parking ADD COLUMN route_name VARCHAR(100) NULL COMMENT 'inferred route name' AFTER route_id"),
        ("route_infer_method", "ALTER TABLE station_parking ADD COLUMN route_infer_method VARCHAR(20) NULL COMMENT 'route inference method' AFTER route_name"),
        ("route_infer_gap_seconds", "ALTER TABLE station_parking ADD COLUMN route_infer_gap_seconds INT NULL COMMENT 'time gap used for route inference' AFTER route_infer_method"),
    ]
    for name, sql in ddl:
        if name not in columns:
            cur.execute(sql)

    indexes = {row[2] for row in fetch_all(cur, "SHOW INDEX FROM station_parking")}
    if "idx_sp_car_start" not in indexes:
        cur.execute("CREATE INDEX idx_sp_car_start ON station_parking(car_id, start_date_time)")
    if "idx_sp_route" not in indexes:
        cur.execute("CREATE INDEX idx_sp_route ON station_parking(route_number)")

    sd_indexes = {row[2] for row in fetch_all(cur, "SHOW INDEX FROM section_driving")}
    if "idx_sd_car_start" not in sd_indexes:
        cur.execute("CREATE INDEX idx_sd_car_start ON section_driving(car_id, start_date_time)")
    if "idx_sd_car_end" not in sd_indexes:
        cur.execute("CREATE INDEX idx_sd_car_end ON section_driving(car_id, end_date_time)")


def load_section_meta(cur):
    rows = fetch_all(
        cur,
        """
        SELECT section_id, start_station_id, end_station_id, route_number
        FROM section
        WHERE route_number IS NOT NULL
        """,
    )
    return {
        section_id: {
            "start_station_id": start_station_id,
            "end_station_id": end_station_id,
            "route_number": route_number,
        }
        for section_id, start_station_id, end_station_id, route_number in rows
    }


def load_route_meta(cur):
    rows = fetch_all(cur, "SELECT route_id, route_name, is_up_or_down FROM route")
    meta = {}
    for route_id, route_name, direction in rows:
        direction_key = {UP: "up", DOWN: "down"}.get(direction, direction)
        route_number = f"{route_name.split(ROUTE_SUFFIX, 1)[0]}_{direction_key}"
        if route_number not in meta or route_id < meta[route_number]["route_id"]:
            meta[route_number] = {"route_id": route_id, "route_name": route_name}
    return meta


def load_route_station_prefixes(cur):
    rows = fetch_all(
        cur,
        """
        SELECT DISTINCT SUBSTRING_INDEX(r.route_name, %s, 1) AS route_prefix, rs.station_id
        FROM route_station rs
        JOIN route r ON r.route_id = rs.route_id
        WHERE rs.station_id IS NOT NULL
        """,
        (ROUTE_SUFFIX,),
    )
    prefixes = {}
    for route_prefix, station_id in rows:
        prefixes.setdefault(str(route_prefix), set()).add(station_id)
    return prefixes


def pack_events(items):
    items.sort(key=lambda item: item["time"])
    return {"times": [item["time"] for item in items], "events": items}


def load_car_events(cur, car_id, section_meta, route_meta):
    rows = fetch_all(
        cur,
        """
        SELECT section_id, start_date_time, end_date_time
        FROM section_driving
        WHERE car_id = %s
        ORDER BY start_date_time, id
        """,
        (car_id,),
    )
    prev_by_station = {}
    next_by_station = {}
    prev_any = []
    next_any = []

    for section_id, start_time, end_time in rows:
        meta = section_meta.get(normalize_section_id(section_id))
        if not meta:
            continue
        route_number = meta["route_number"]
        route = route_meta.get(route_number, {})
        event_base = {
            "route_number": route_number,
            "route_id": route.get("route_id"),
            "route_name": route.get("route_name") or route_name_from_number(route_number),
        }
        if meta["end_station_id"] is not None and end_time is not None:
            event = {**event_base, "time": end_time}
            prev_by_station.setdefault(meta["end_station_id"], []).append(event)
            prev_any.append(event)
        if meta["start_station_id"] is not None and start_time is not None:
            event = {**event_base, "time": start_time}
            next_by_station.setdefault(meta["start_station_id"], []).append(event)
            next_any.append(event)

    return (
        {station_id: pack_events(items) for station_id, items in prev_by_station.items()},
        {station_id: pack_events(items) for station_id, items in next_by_station.items()},
        pack_events(prev_any),
        pack_events(next_any),
    )


def load_car_parking(cur, car_id):
    return [
        {
            "id": row[0],
            "station_id": row[1],
            "start_date_time": row[2],
            "end_date_time": row[3],
        }
        for row in fetch_all(
            cur,
            """
            SELECT id, station_id, start_date_time, end_date_time
            FROM station_parking
            WHERE car_id = %s
            ORDER BY start_date_time, id
            """,
            (car_id,),
        )
    ]


def choose_strict(parking, prev_by_station, next_by_station):
    station_id = parking["station_id"]
    start_time = parking["start_date_time"]
    end_time = parking["end_date_time"]
    best = None

    prev_group = prev_by_station.get(station_id)
    if prev_group:
        idx = bisect_right(prev_group["times"], start_time) - 1
        if idx >= 0:
            event = prev_group["events"][idx]
            gap = int((start_time - event["time"]).total_seconds())
            if 0 <= gap <= MAX_GAP_SECONDS:
                best = {**event, "method": "prev_end", "gap": gap}

    next_group = next_by_station.get(station_id)
    if next_group:
        idx = bisect_left(next_group["times"], end_time)
        if idx < len(next_group["events"]):
            event = next_group["events"][idx]
            gap = int((event["time"] - end_time).total_seconds())
            if 0 <= gap <= MAX_GAP_SECONDS and (best is None or gap < best["gap"]):
                best = {**event, "method": "next_start", "gap": gap}

    return best


def choose_fallback(parking, prev_any, next_any, route_station_prefixes):
    station_id = parking["station_id"]
    start_time = parking["start_date_time"]
    end_time = parking["end_date_time"]
    best = None

    idx = bisect_right(prev_any["times"], start_time) - 1
    if idx >= 0:
        event = prev_any["events"][idx]
        gap = int((start_time - event["time"]).total_seconds())
        prefix = event["route_number"].split("_", 1)[0]
        if 0 <= gap <= MAX_FALLBACK_GAP_SECONDS and station_id in route_station_prefixes.get(prefix, set()):
            best = {**event, "method": "prev_any", "gap": gap}

    idx = bisect_left(next_any["times"], end_time)
    if idx < len(next_any["events"]):
        event = next_any["events"][idx]
        gap = int((event["time"] - end_time).total_seconds())
        prefix = event["route_number"].split("_", 1)[0]
        if (
            0 <= gap <= MAX_FALLBACK_GAP_SECONDS
            and station_id in route_station_prefixes.get(prefix, set())
            and (best is None or gap < best["gap"])
        ):
            best = {**event, "method": "next_any", "gap": gap}

    return best


def choose_candidate(parking, prev_by_station, next_by_station, prev_any, next_any, route_station_prefixes):
    return (
        choose_strict(parking, prev_by_station, next_by_station)
        or choose_fallback(parking, prev_any, next_any, route_station_prefixes)
    )


def update_batch(cur, rows):
    if not rows:
        return
    cur.executemany(
        """
        UPDATE station_parking
        SET route_number = %s,
            route_id = %s,
            route_name = %s,
            route_infer_method = %s,
            route_infer_gap_seconds = %s
        WHERE id = %s
        """,
        rows,
    )


def main():
    conn = pymysql.connect(**DB)
    updated = 0
    total = 0
    try:
        with conn.cursor() as cur:
            ensure_schema(cur)
            conn.commit()

            section_meta = load_section_meta(cur)
            route_meta = load_route_meta(cur)
            route_station_prefixes = load_route_station_prefixes(cur)

            cur.execute(
                """
                UPDATE station_parking
                SET route_number = NULL,
                    route_id = NULL,
                    route_name = NULL,
                    route_infer_method = NULL,
                    route_infer_gap_seconds = NULL
                """
            )
            conn.commit()

            car_ids = [
                row[0]
                for row in fetch_all(
                    cur,
                    """
                    SELECT car_id
                    FROM station_parking
                    WHERE car_id IS NOT NULL
                    GROUP BY car_id
                    ORDER BY car_id
                    """,
                )
            ]

            batch = []
            for index, car_id in enumerate(car_ids, 1):
                prev_by_station, next_by_station, prev_any, next_any = load_car_events(cur, car_id, section_meta, route_meta)
                parking_rows = load_car_parking(cur, car_id)
                total += len(parking_rows)
                for parking in parking_rows:
                    candidate = choose_candidate(
                        parking,
                        prev_by_station,
                        next_by_station,
                        prev_any,
                        next_any,
                        route_station_prefixes,
                    )
                    if not candidate:
                        continue
                    batch.append(
                        (
                            candidate["route_number"],
                            candidate["route_id"],
                            candidate["route_name"],
                            candidate["method"],
                            candidate["gap"],
                            parking["id"],
                        )
                    )
                    updated += 1
                    if len(batch) >= BATCH_SIZE:
                        update_batch(cur, batch)
                        batch.clear()

                if index % 100 == 0:
                    update_batch(cur, batch)
                    batch.clear()
                    conn.commit()
                    print(f"cars={index}/{len(car_ids)}, updated={updated}, total={total}")

            update_batch(cur, batch)
            conn.commit()
            print(f"done cars={len(car_ids)}, updated={updated}, total={total}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
