# Database Repair Scripts

These scripts are used to reproduce local database fixes on another machine.

## Scripts

- `preview_repair_234_original.py`
  - Preview the 234 route section repair.
  - Does not modify the database.

- `apply_repair_234_original.py`
  - Repairs only the 234 route data.
  - Updates `section`, `section_driving`, and `section_driving_summary`.

- `apply_repair_all_original.py`
  - Repairs all routes that can be safely matched.
  - Rebuilds route sections using `route_station` as the authoritative station order.
  - Updates `section`, `section_driving`, and `section_driving_summary`.
  - Writes a report to `repair_all_report/repair_all_report.csv`.

- `create_car_table.py`
  - Builds derived vehicle tables from existing operation records.
  - Creates `car` from distinct `section_driving.car_id` and `station_parking.car_id`.
  - Creates `car_route` from `section_driving.car_id` joined with `section.route_number`.
  - Updates `car.route_count`, `car.primary_route_number`, and `car.primary_route_name`.

- `infer_station_parking_routes.py`
  - Adds route attribution fields to `station_parking`.
  - Infers each parking record route from the same car's nearby `section_driving` records.
  - Strict rule: same car + nearby time + station matches section start/end.
  - Fallback rule: same car + nearby time + the station belongs to that route.
  - Updates `station_parking.route_number`, `route_id`, `route_name`, `route_infer_method`, and `route_infer_gap_seconds`.

- `normalize_section_driving_ids.py`
  - Normalizes `section_driving.section_id` to the same format as `section.section_id`.
  - Example: `101_up0` becomes `101_up_00`.
  - Creates a backup table named `section_driving_section_id_backup_yyyyMMdd_HHmmss` before updating.

## Before Running

Make sure the target database has these fields/tables:

- `section.end_station_id`
- `section.route_number`
- `section_driving.duration_seconds`
- `section_driving_summary`
- `station_parking.duration_seconds`

Back up important tables first:

```powershell
mysqldump -uroot -p bus_analysis section > section.sql
mysqldump -uroot -p bus_analysis section_driving > section_driving.sql
mysqldump -uroot -p bus_analysis section_driving_summary > section_driving_summary.sql
mysqldump -uroot -p bus_analysis station_parking > station_parking.sql
```

## Commands

Run from the `backend` directory:

```powershell
pip install pymysql
python scripts\apply_repair_all_original.py
python scripts\normalize_section_driving_ids.py
python scripts\create_car_table.py
python scripts\infer_station_parking_routes.py
```

## Verified Local Result

On the local database:

- `car`: 3340 rows
- `car_route`: 7490 rows
- `section_driving.section_id`: 2286884 rows normalized to the `section.section_id` format
- `station_parking` route attribution: 2592172 / 2793403 rows, 92.8%
- The 159 repaired routes have section station chains aligned with `route_station`.
