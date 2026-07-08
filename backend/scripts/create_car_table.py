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


NORMALIZED_SECTION_ID = """
CASE
    WHEN sd.section_id LIKE '%%\\_up\\_%%' OR sd.section_id LIKE '%%\\_down\\_%%' THEN sd.section_id
    WHEN sd.section_id LIKE '%%\\_up%%' THEN CONCAT(
        SUBSTRING_INDEX(sd.section_id, '_up', 1),
        '_up_',
        LPAD(SUBSTRING_INDEX(sd.section_id, '_up', -1), 2, '0')
    )
    WHEN sd.section_id LIKE '%%\\_down%%' THEN CONCAT(
        SUBSTRING_INDEX(sd.section_id, '_down', 1),
        '_down_',
        LPAD(SUBSTRING_INDEX(sd.section_id, '_down', -1), 2, '0')
    )
    ELSE sd.section_id
END
"""


def main():
    route_suffix = "\u8def"
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            # car is a derived table. Rebuild it to keep the target database in sync.
            cur.execute("DROP TABLE IF EXISTS car_route")
            cur.execute("DROP TABLE IF EXISTS car")

            cur.execute(
                """
                CREATE TABLE car (
                    car_id INT NOT NULL COMMENT 'vehicle id from section_driving/station_parking',
                    driving_record_count BIGINT NOT NULL DEFAULT 0 COMMENT 'section driving record count',
                    parking_record_count BIGINT NOT NULL DEFAULT 0 COMMENT 'station parking record count',
                    route_count INT NOT NULL DEFAULT 0 COMMENT 'related route count',
                    primary_route_number VARCHAR(50) NULL COMMENT 'route_number with most driving records',
                    primary_route_name VARCHAR(100) NULL COMMENT 'route name with most driving records',
                    first_seen_time DATETIME NULL COMMENT 'first observed time',
                    last_seen_time DATETIME NULL COMMENT 'last observed time',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (car_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='car base table'
                """
            )

            cur.execute(
                """
                CREATE TABLE car_route (
                    id INT NOT NULL AUTO_INCREMENT,
                    car_id INT NOT NULL COMMENT 'vehicle id',
                    route_number VARCHAR(50) NOT NULL COMMENT 'route direction key, for example 13_down',
                    route_id INT NULL COMMENT 'route table id when matched',
                    route_name VARCHAR(100) NULL COMMENT 'route display name',
                    driving_record_count BIGINT NOT NULL DEFAULT 0 COMMENT 'driving records on this route',
                    first_seen_time DATETIME NULL COMMENT 'first observed time on this route',
                    last_seen_time DATETIME NULL COMMENT 'last observed time on this route',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY uk_car_route (car_id, route_number),
                    KEY idx_car_route_car (car_id),
                    KEY idx_car_route_number (route_number),
                    KEY idx_car_route_id (route_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='car-route relation table'
                """
            )

            cur.execute(
                """
                INSERT INTO car(car_id, driving_record_count, parking_record_count, first_seen_time, last_seen_time)
                SELECT
                    ids.car_id,
                    COALESCE(d.driving_record_count, 0),
                    COALESCE(p.parking_record_count, 0),
                    LEAST(
                        COALESCE(d.first_seen_time, p.first_seen_time),
                        COALESCE(p.first_seen_time, d.first_seen_time)
                    ),
                    GREATEST(
                        COALESCE(d.last_seen_time, p.last_seen_time),
                        COALESCE(p.last_seen_time, d.last_seen_time)
                    )
                FROM (
                    SELECT car_id FROM section_driving WHERE car_id IS NOT NULL
                    UNION
                    SELECT car_id FROM station_parking WHERE car_id IS NOT NULL
                ) ids
                LEFT JOIN (
                    SELECT car_id,
                           COUNT(*) AS driving_record_count,
                           MIN(start_date_time) AS first_seen_time,
                           MAX(end_date_time) AS last_seen_time
                    FROM section_driving
                    WHERE car_id IS NOT NULL
                    GROUP BY car_id
                ) d ON d.car_id = ids.car_id
                LEFT JOIN (
                    SELECT car_id,
                           COUNT(*) AS parking_record_count,
                           MIN(start_date_time) AS first_seen_time,
                           MAX(end_date_time) AS last_seen_time
                    FROM station_parking
                    WHERE car_id IS NOT NULL
                    GROUP BY car_id
                ) p ON p.car_id = ids.car_id
                """
            )

            cur.execute(
                f"""
                INSERT INTO car_route(
                    car_id,
                    route_number,
                    route_id,
                    route_name,
                    driving_record_count,
                    first_seen_time,
                    last_seen_time
                )
                SELECT
                    agg.car_id,
                    agg.route_number,
                    r.route_id,
                    COALESCE(r.route_name, CONCAT(SUBSTRING_INDEX(agg.route_number, '_', 1), %s)),
                    agg.driving_record_count,
                    agg.first_seen_time,
                    agg.last_seen_time
                FROM (
                    SELECT
                        sd.car_id,
                        s.route_number,
                        COUNT(*) AS driving_record_count,
                        MIN(sd.start_date_time) AS first_seen_time,
                        MAX(sd.end_date_time) AS last_seen_time
                    FROM section_driving sd
                    JOIN section s ON s.section_id = {NORMALIZED_SECTION_ID}
                    WHERE sd.car_id IS NOT NULL AND s.route_number IS NOT NULL
                    GROUP BY sd.car_id, s.route_number
                ) agg
                LEFT JOIN (
                    SELECT
                        route_number,
                        MIN(route_id) AS route_id,
                        MIN(route_name) AS route_name
                    FROM (
                        SELECT
                            CONCAT(
                                SUBSTRING_INDEX(route_name, %s, 1),
                                '_',
                                CASE is_up_or_down
                                    WHEN '上行' THEN 'up'
                                    WHEN '下行' THEN 'down'
                                    ELSE is_up_or_down
                                END
                            ) AS route_number,
                            route_id,
                            route_name
                        FROM route
                    ) route_candidates
                    GROUP BY route_number
                ) r ON r.route_number = agg.route_number
                """,
                (route_suffix, route_suffix),
            )

            cur.execute(
                """
                UPDATE car c
                LEFT JOIN (
                    SELECT car_id, COUNT(*) AS route_count
                    FROM car_route
                    GROUP BY car_id
                ) rc ON rc.car_id = c.car_id
                LEFT JOIN (
                    SELECT car_id, route_number, route_name
                    FROM (
                        SELECT car_id,
                               route_number,
                               route_name,
                               driving_record_count,
                               ROW_NUMBER() OVER (
                                   PARTITION BY car_id
                                   ORDER BY driving_record_count DESC, route_number
                               ) AS rn
                        FROM car_route
                    ) ranked
                    WHERE rn = 1
                ) pr ON pr.car_id = c.car_id
                SET c.route_count = COALESCE(rc.route_count, 0),
                    c.primary_route_number = pr.route_number,
                    c.primary_route_name = pr.route_name
                """
            )

            cur.execute("SELECT COUNT(*) FROM car")
            car_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM car_route")
            car_route_count = cur.fetchone()[0]
            print(f"car rows: {car_count}")
            print(f"car_route rows: {car_route_count}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
