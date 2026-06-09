<template>
  <div class="map-page">
    <div id="map-container"></div>

    <!-- 左上角：模式切换 + 图例 -->
    <div class="toolbar">
      <div class="mode-btns">
        <button :class="{ active: displayMode === 'heat' }" @click="setMode('heat')">热力图</button>
        <button :class="{ active: displayMode === 'dot' }" @click="setMode('dot')">站点图</button>
      </div>
      <div class="legend">
        <div class="legend-title">途经线路数</div>
        <div class="legend-items">
          <span class="dot" style="background:#3b82f6"></span><span>1-2条</span>
          <span class="dot" style="background:#f59e0b"></span><span>3-5条</span>
          <span class="dot" style="background:#ea580c"></span><span>6-9条</span>
          <span class="dot" style="background:#dc2626"></span><span>10条+</span>
        </div>
      </div>
    </div>

    <!-- 右侧线路信息面板 -->
    <div v-if="selectedStation" class="panel">
      <div class="panel-header">
        <div>
          <div class="station-name">{{ selectedStation.stationName }}</div>
          <div class="meta">共 {{ routes.length }} 条线路途经</div>
        </div>
        <button class="close" @click="closePanel">×</button>
      </div>
      <ul class="route-list">
        <li
          v-for="r in routes"
          :key="r.routeId"
          :class="{ active: currentRouteId === r.routeId }"
          @click="drawRoute(r)"
        >
          <span class="route-name">{{ r.routeName }}</span>
          <span class="direction">{{ r.isUpOrDown }}</span>
        </li>
      </ul>
    </div>

    <div v-if="loading" class="loading">加载站点数据...</div>
  </div>
</template>

<script setup>
import { onMounted, ref, onUnmounted } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import { stationApi, sectionApi } from '../api'

const AMAP_KEY = '2991ac65a0c2afea3a704f59bac52f28'

let map = null
let AMap = null
let heatmap = null
let allStationsData = []           // 原始站点数据
const stationMarkers = []          // CircleMarker 列表
let highlightedMarkers = []
let routePolyline = null
let targetMarker = null

const loading = ref(true)
const displayMode = ref('heat')    // 'heat' | 'dot'
const selectedStation = ref(null)
const routes = ref([])
const currentRouteId = ref(null)

// 缩放级别 >= ZOOM_THRESHOLD 自动切换到站点图
const ZOOM_THRESHOLD = 14

function radiusByRouteCount(count) {
  if (count >= 10) return 5
  if (count >= 6)  return 4
  if (count >= 3)  return 3
  return 2
}

function colorByRouteCount(count) {
  if (count >= 10) return '#dc2626'
  if (count >= 6)  return '#ea580c'
  if (count >= 3)  return '#f59e0b'
  return '#3b82f6'
}

async function initMap() {
  AMap = await AMapLoader.load({
    key: AMAP_KEY,
    version: '2.0',
    plugins: ['AMap.ToolBar', 'AMap.HeatMap']
  })

  map = new AMap.Map('map-container', {
    zoom: 12,
    center: [115.858, 28.683],
    mapStyle: 'amap://styles/light'
  })
  map.addControl(new AMap.ToolBar({ position: 'RB' }))

  // 缩放时自动切换显示模式
  map.on('zoomend', () => {
    const zoom = map.getZoom()
    if (zoom >= ZOOM_THRESHOLD && displayMode.value === 'heat') {
      setMode('dot')
    } else if (zoom < ZOOM_THRESHOLD && displayMode.value === 'dot') {
      setMode('heat')
    }
  })

  await loadStations()
}

async function loadStations() {
  loading.value = true
  const res = await stationApi.listAll()
  allStationsData = res.data.filter(s => s.lng && s.lat)

  // 创建热力图
  heatmap = new AMap.HeatMap(map, {
    radius: 20,
    opacity: [0, 0.85],
    gradient: {
      0.3: '#93c5fd',
      0.55: '#f59e0b',
      0.75: '#ea580c',
      1.0:  '#dc2626'
    },
    blur: 0.85
  })
  heatmap.setDataSet({
    data: allStationsData.map(s => ({ lng: s.lng, lat: s.lat, count: s.routeCount })),
    max: Math.max(...allStationsData.map(s => s.routeCount))
  })

  // 创建独立圆点（默认隐藏，等切换到站点模式再加入地图）
  allStationsData.forEach(s => {
    const marker = new AMap.CircleMarker({
      center: [s.lng, s.lat],
      radius: radiusByRouteCount(s.routeCount),
      fillColor: colorByRouteCount(s.routeCount),
      fillOpacity: 0.75,
      strokeColor: 'rgba(255,255,255,0.6)',
      strokeWeight: 0.8,
      cursor: 'pointer',
      extData: s
    })
    marker.on('click', () => onStationClick(s))
    stationMarkers.push(marker)
  })

  // 默认热力图模式
  setMode('heat')
  loading.value = false
}

function setMode(mode) {
  displayMode.value = mode
  if (mode === 'heat') {
    heatmap && heatmap.show()
    if (stationMarkers.length) map.remove(stationMarkers)
  } else {
    heatmap && heatmap.hide()
    map.add(stationMarkers)
  }
}

async function onStationClick(station) {
  selectedStation.value = station
  const res = await stationApi.listRoutes(station.stationId)
  routes.value = res.data

  if (targetMarker) targetMarker.setMap(null)
  targetMarker = new AMap.Marker({
    position: [station.lng, station.lat],
    icon: new AMap.Icon({
      size: new AMap.Size(28, 28),
      image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png'
    }),
    offset: new AMap.Pixel(-14, -28)
  })
  targetMarker.setMap(map)

  if (routes.value.length > 0) drawRoute(routes.value[0])
}

async function drawRoute(route) {
  currentRouteId.value = route.routeId

  if (routePolyline) routePolyline.setMap(null)
  highlightedMarkers.forEach(m => m.setMap(null))
  highlightedMarkers = []

  const [stationRes, sectionRes] = await Promise.all([
    stationApi.listByRoute(route.routeId),
    sectionApi.pathsByRoute(route.routeId)
  ])

  const stations = stationRes.data.filter(s => s.lng && s.lat)
  const sections = sectionRes.data

  let fullPath = []
  if (sections && sections.length > 0) {
    sections.forEach(sec => {
      try {
        const pts = JSON.parse(sec.path)
        if (pts && pts.length > 0) {
          fullPath = fullPath.length > 0
            ? fullPath.concat(pts.slice(1))
            : fullPath.concat(pts)
        }
      } catch (e) {}
    })
  }
  if (fullPath.length === 0) {
    fullPath = stations.map(s => [s.lng, s.lat])
  }

  routePolyline = new AMap.Polyline({
    path: fullPath,
    strokeColor: '#2563eb',
    strokeWeight: 5,
    strokeOpacity: 0.9,
    lineJoin: 'round',
    lineCap: 'round'
  })
  routePolyline.setMap(map)

  // 沿线站点：白底蓝点
  stations.forEach(s => {
    if (s.stationId === selectedStation.value?.stationId) return
    const m = new AMap.CircleMarker({
      center: [s.lng, s.lat],
      radius: 5,
      fillColor: '#ffffff',
      fillOpacity: 1,
      strokeColor: '#2563eb',
      strokeWeight: 2
    })
    m.setMap(map)
    highlightedMarkers.push(m)
  })

  map.setFitView([routePolyline, ...highlightedMarkers, targetMarker].filter(Boolean))
}

function closePanel() {
  selectedStation.value = null
  routes.value = []
  currentRouteId.value = null
  if (routePolyline) { routePolyline.setMap(null); routePolyline = null }
  if (targetMarker)  { targetMarker.setMap(null);  targetMarker = null  }
  highlightedMarkers.forEach(m => m.setMap(null))
  highlightedMarkers = []
}

onMounted(initMap)
onUnmounted(() => map && map.destroy())
</script>

<style scoped>
.map-page { position: relative; flex: 1; overflow: hidden; }
#map-container { width: 100%; height: 100%; }

/* 左上工具栏 */
.toolbar {
  position: absolute; top: 16px; left: 16px; z-index: 100;
  display: flex; flex-direction: column; gap: 8px;
}
.mode-btns {
  display: flex; background: white; border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.12); overflow: hidden;
}
.mode-btns button {
  padding: 7px 16px; border: none; background: none;
  font-size: 13px; cursor: pointer; color: #6b7280;
  transition: background 0.15s;
}
.mode-btns button:hover { background: #f3f4f6; }
.mode-btns button.active { background: #2563eb; color: white; font-weight: 500; }

.legend {
  background: rgba(255,255,255,0.92); border-radius: 6px;
  padding: 8px 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  font-size: 12px; color: #4b5563;
}
.legend-title { font-weight: 600; margin-bottom: 6px; color: #111827; }
.legend-items { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.legend-items .dot {
  display: inline-block; width: 10px; height: 10px;
  border-radius: 50%; flex-shrink: 0;
}

/* 右侧面板 */
.panel {
  position: absolute; top: 16px; right: 16px;
  width: 300px; max-height: calc(100% - 32px);
  background: white; border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  display: flex; flex-direction: column; z-index: 100;
}
.panel-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 16px; border-bottom: 1px solid #e5e7eb; flex-shrink: 0;
}
.station-name { font-size: 16px; font-weight: 600; color: #111827; }
.meta { font-size: 12px; color: #6b7280; margin-top: 4px; }
.close {
  background: none; border: none; font-size: 22px;
  color: #9ca3af; cursor: pointer; line-height: 1; padding: 0 2px;
}
.route-list { list-style: none; overflow-y: auto; }
.route-list li {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; cursor: pointer; border-bottom: 1px solid #f3f4f6;
  transition: background 0.1s;
}
.route-list li:hover { background: #f9fafb; }
.route-list li.active { background: #eff6ff; }
.route-name { font-size: 14px; color: #111827; }
.route-list li.active .route-name { color: #2563eb; font-weight: 500; }
.direction { font-size: 12px; color: #6b7280; }

.loading {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  padding: 12px 24px; background: rgba(0,0,0,0.7); color: white;
  border-radius: 6px; font-size: 14px; z-index: 200;
}
</style>
