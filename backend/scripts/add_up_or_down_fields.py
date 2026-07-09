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


def fetch_column_names(cur, table_name):
    cur.execute(f"SHOW COLUMNS FROM {table_name}")
    return {row[0] for row in cur.fetchall()}


def fetch_index_names(cur, table_name):
    cur.execute(f"SHOW INDEX FROM {table_name}")
    return {row[2] for row in cur.fetchall()}


def ensure_column(cur, table_name, column_name, ddl):
    if column_name not in fetch_column_names(cur, table_name):
        cur.execute(ddl)


def ensure_index(cur, table_name, index_name, ddl):
    if index_name not in fetch_index_names(cur, table_name):
        cur.execute(ddl)


def id_bounds(cur, table_name):
    cur.execute(f"SELECT MIN(id), MAX(id) FROM {table_name}")
    return cur.fetchone()


def update_in_batches(conn, table_name, column_name, source_column, batch_size=100000):
    min_id, max_id = id_bounds(conn.cursor(), table_name)
    if min_id is None or max_id is None:
        return 0

    updated = 0
    current = min_id
    while current <= max_id:
        end = current + batch_size - 1
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE {table_name}
                SET {column_name} = CASE
                    WHEN {source_column} LIKE '%%!_up%%' ESCAPE '!' THEN 'up'
                    WHEN {source_column} LIKE '%%!_down%%' ESCAPE '!' THEN 'down'
                    ELSE NULL
                END
                WHERE id BETWEEN %s AND %s
                  AND (
                      {column_name} IS NULL
                      OR {column_name} <> CASE
                          WHEN {source_column} LIKE '%%!_up%%' ESCAPE '!' THEN 'up'
                          WHEN {source_column} LIKE '%%!_down%%' ESCAPE '!' THEN 'down'
                          ELSE ''
                      END
                  )
                """,
                (current, end),
            )
            updated += cur.rowcount
        conn.commit()
        print(f"{table_name}: id {current}-{end}, updated={updated}")
        current = end + 1
    return updated


def main():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            ensure_column(
                cur,
                "section_driving",
                "up_or_down",
                """
                ALTER TABLE section_driving
                ADD COLUMN up_or_down VARCHAR(10) NULL
                COMMENT 'direction inferred from section.route_number: up/down'
                AFTER section_id
                """,
            )
            ensure_column(
                cur,
                "station_parking",
                "up_or_down",
                """
                ALTER TABLE station_parking
                ADD COLUMN up_or_down VARCHAR(10) NULL
                COMMENT 'direction inferred from route_number: up/down'
                AFTER route_number
                """,
            )

        conn.commit()

        section_driving_updated = update_in_batches(
            conn,
            "section_driving",
            "up_or_down",
            "section_id",
        )
        station_parking_updated = update_in_batches(
            conn,
            "station_parking",
            "up_or_down",
            "route_number",
        )

        with conn.cursor() as cur:
            ensure_index(
                cur,
                "section_driving",
                "idx_sd_up_or_down",
                "CREATE INDEX idx_sd_up_or_down ON section_driving(up_or_down)",
            )
            ensure_index(
                cur,
                "station_parking",
                "idx_sp_up_or_down",
                "CREATE INDEX idx_sp_up_or_down ON station_parking(up_or_down)",
            )

            cur.execute(
                """
                SELECT up_or_down, COUNT(*)
                FROM section_driving
                GROUP BY up_or_down
                ORDER BY up_or_down
                """
            )
            section_driving_counts = cur.fetchall()

            cur.execute(
                """
                SELECT up_or_down, COUNT(*)
                FROM station_parking
                GROUP BY up_or_down
                ORDER BY up_or_down
                """
            )
            station_parking_counts = cur.fetchall()

        conn.commit()
        print(f"section_driving_updated: {section_driving_updated}")
        print(f"station_parking_updated: {station_parking_updated}")
        print("section_driving_counts:")
        for row in section_driving_counts:
            print(row)
        print("station_parking_counts:")
        for row in station_parking_counts:
            print(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
