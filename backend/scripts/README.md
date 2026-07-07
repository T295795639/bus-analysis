# 数据库修复脚本

这些脚本用于把本地已经验证过的线路 section / section_driving 修复逻辑同步到另一台机器的 `bus_analysis` 数据库。

## 脚本说明

- `preview_repair_234_original.py`
  - 只预览 234 路修复结果，不修改数据库。

- `apply_repair_234_original.py`
  - 只修复 234 路相关的 `section`、`section_driving`、`section_driving_summary` 数据。

- `apply_repair_all_original.py`
  - 全量同步修复所有可匹配线路。
  - 以 `route_station` 的真实站点顺序为准，重建对应线路的 `section`。
  - 同步迁移/重建对应的 `section_driving` 和 `section_driving_summary`。
  - 会生成 `repair_all_report/repair_all_report.csv`，记录哪些线路修改、跳过或无需修复。

## 执行前确认

先确认另一台机器的数据库已经具备这些字段：

- `section.end_station_id`
- `section.route_number`
- `section_driving.duration_seconds`
- `section_driving_summary`

执行前建议先备份：

```powershell
mysqldump -uroot -p bus_analysis section > section.sql
mysqldump -uroot -p bus_analysis section_driving > section_driving.sql
mysqldump -uroot -p bus_analysis section_driving_summary > section_driving_summary.sql
```

## 执行命令

在 `backend` 目录执行：

```powershell
pip install pymysql
python scripts\apply_repair_all_original.py
```

执行完成后查看报告：

```powershell
Get-Content ..\repair_all_report\repair_all_report.csv -TotalCount 20
```

## 当前已验证结果

在本机数据库执行后的结果：

- 修改线路：159 条
- 无需修改：9 条
- 跳过：260 条
- 修改后的 159 条线路，`section` 站点链已校验与 `route_station` 顺序一致。

