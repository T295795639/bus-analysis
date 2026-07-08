import datetime

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


def main():
    suffix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_table = f"section_driving_section_id_backup_{suffix}"
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE TABLE {backup_table} AS SELECT id, section_id FROM section_driving")
            cur.execute(f"ALTER TABLE {backup_table} ADD PRIMARY KEY(id)")

            cur.execute(
                """
                UPDATE section_driving
                SET section_id = CASE
                    WHEN section_id LIKE '%\\_up\\_%' OR section_id LIKE '%\\_down\\_%' THEN section_id
                    WHEN section_id LIKE '%\\_up%' THEN CONCAT(
                        SUBSTRING_INDEX(section_id, '_up', 1),
                        '_up_',
                        LPAD(SUBSTRING_INDEX(section_id, '_up', -1), 2, '0')
                    )
                    WHEN section_id LIKE '%\\_down%' THEN CONCAT(
                        SUBSTRING_INDEX(section_id, '_down', 1),
                        '_down_',
                        LPAD(SUBSTRING_INDEX(section_id, '_down', -1), 2, '0')
                    )
                    ELSE section_id
                END
                WHERE (section_id LIKE '%\\_up%' OR section_id LIKE '%\\_down%')
                  AND NOT (section_id LIKE '%\\_up\\_%' OR section_id LIKE '%\\_down\\_%')
                """
            )
            updated = cur.rowcount

            cur.execute(
                """
                SELECT COUNT(*)
                FROM section_driving
                WHERE (section_id LIKE '%\\_up%' OR section_id LIKE '%\\_down%')
                  AND NOT (section_id LIKE '%\\_up\\_%' OR section_id LIKE '%\\_down\\_%')
                """
            )
            old_format_left = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*)
                FROM section_driving sd
                LEFT JOIN section s ON s.section_id = sd.section_id
                WHERE s.section_id IS NULL
                """
            )
            unmatched = cur.fetchone()[0]

        conn.commit()
        print(f"backup_table: {backup_table}")
        print(f"updated_rows: {updated}")
        print(f"old_format_left: {old_format_left}")
        print(f"rows_without_section: {unmatched}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
