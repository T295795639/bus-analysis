# 南昌公交可视化

## 技术栈

| 端 | 技术 |
|---|---|
| 后端 | Spring Boot 3.2 · MyBatis-Plus · MySQL 8.0 · JDK 17+ |
| 前端 | Vue 3 · Vite · Vue Router · Axios · ECharts · 高德地图 JS API 2.0 |

## 功能概览

| 页面 | 路由 | 说明 |
|---|---|---|
| 线路站点地图 | `/map` | 热力图/站点图双模式，点击站点查看途经线路并绘制真实路形 |
| 站点热度排行 | `/ranking` | 按停靠次数 Top N 柱状图 |
| 路段行驶分析 | `/section` | 各路段平均耗时，支持早/晚高峰筛选，红色标注瓶颈路段 |
| 站点停靠分析 | `/parking` | 各站点平均停靠时长，红色标注异常站点 |
| 线路详情 | `/route` | 线路搜索 + 有序站点列表 + 各站停靠次数柱状图 |

## 数据库表

| 表 | 说明 | 数据量 |
|---|---|---|
| `route` | 线路 | 428 |
| `station` | 站点 | 3997 |
| `route_station` | 线路-站点关联 | 38942 |
| `section` | 路段（含真实坐标 path） | 3199 |
| `section_driving` | 路段行驶记录 | 253 万 |
| `station_parking` | 站点停靠记录 | 279 万 |

## 接口列表

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/station/all` | 所有站点 + 途经线路数 |
| GET | `/api/station/{id}/routes` | 某站点的途经线路 |
| GET | `/api/station/by-route/{routeId}` | 某线路的有序站点 |
| GET | `/api/station/ranking?topN=20` | 停靠次数 Top N |
| GET | `/api/station/parking/stats?topN=20` | 平均停靠时长 Top N |
| GET | `/api/section/driving/stats?timeRange=all&topN=50` | 路段平均行驶时长 |
| GET | `/api/section/by-route/{routeId}` | 某线路的路段真实 path |
| GET | `/api/route/list` | 所有线路 |
| GET | `/api/route/{routeId}/detail` | 线路有序站点 + 停靠次数 |

## 启动步骤

### 1. 数据库准备

```sql
CREATE INDEX idx_sp_station ON station_parking(station_id);
CREATE INDEX idx_sp_time    ON station_parking(start_date_time);
CREATE INDEX idx_sd_section ON section_driving(section_id);
CREATE INDEX idx_sd_time    ON section_driving(start_date_time);
```

### 2. 后端

修改 `backend/src/main/resources/application.yml`：
- `spring.datasource.url` 中的数据库名
- `spring.datasource.password`

```bash
cd backend
mvn spring-boot:run
# 启动后监听 http://localhost:8080
```

### 3. 前端

修改 `frontend/src/views/MapView.vue` 第 37 行的 `AMAP_KEY`。

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```
