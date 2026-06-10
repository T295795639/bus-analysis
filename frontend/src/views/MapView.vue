<template>
  <div class="map-page">
    <div id="map-container"></div>

    <!-- 左上角：模式切换 + 图例 + 排行入口 -->
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
      <button :class="['analysis-btn', { active: showRanking }]" @click="toggleRanking">热度分析</button>
      <button :class="['analysis-btn', { active: showParking }]" @click="toggleParking">停靠时间</button>
    </div>

    <!-- 停靠排行卡片 -->
    <div v-if="showRanking" class="ranking-card">
      <div class="panel-header">
        <div>
          <div class="station-name">站点停靠次数排行</div>
          <div class="meta">
            Top
            <select v-model="rankTopN" @change="loadRanking" class="topn-select">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
            </select>
          </div>
        </div>
        <button class="close" @click="showRanking = false">×</button>
      </div>
      <div ref="rankChartRef" class="rank-chart"></div>
    </div>

    <!-- 停靠时间分析卡片 -->
    <div v-if="showParking" class="ranking-card parking-card">
      <div class="panel-header">
        <div>
          <div class="station-name">站点平均停靠时长</div>
          <div class="meta">
            Top
            <select v-model="parkTopN" @change="loadParking" class="topn-select">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
            </select>
            <span class="anomaly-tip">
              <span class="dot-red"></span>红色为异常站点（超均值1.5倍）
            </span>
          </div>
        </div>
        <button class="close" @click="showParking = false">×</button>
      </div>
      <div ref="parkChartRef" class="rank-chart"></div>
    </div>

    <!-- 右侧线路信息面板 -->
    <div v-if="selectedStation" class="panel">
      <div class="panel-header">
        <div>
          <div class="station-name">{{ selectedStation.stationName }}</div>
          <div class="meta">编号：{{ selectedStation.stationId }} · 共 {{ routes.length }} 条线路途经</div>
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
import { onMounted, ref, onUnmounted, nextTick } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import * as echarts from 'echarts'
import { stationApi, sectionApi } from '../api'

const AMAP_KEY = '2991ac65a0c2afea3a704f59bac52f28'

let map = null
let AMap = null
let heatmap = null
let allStationsData = []           // 原始站点数据
const stationMarkers = []          // CircleMarker 列表
let highlightedMarkers = []
let routePolylines = []   // 支持同时绘制多条线路
let targetMarker = null

const loading = ref(true)
const displayMode = ref('heat')
const selectedStation = ref(null)
const routes = ref([])
const currentRouteId = ref(null)

// 排行卡片
const showRanking = ref(false)
const rankTopN = ref(20)
const rankChartRef = ref(null)
let rankChart = null

async function toggleRanking() {
  showRanking.value = !showRanking.value
  if (showRanking.value) {
    await nextTick()
    await loadRanking()
  } else {
    rankChart && rankChart.dispose()
    rankChart = null
  }
}

async function loadRanking() {
  const res = await stationApi.ranking(rankTopN.value)
  const data = res.data
  await nextTick()
  if (!rankChartRef.value) return
  if (!rankChart) rankChart = echarts.init(rankChartRef.value)
  const names = data.map(d => d.stationName).reverse()
  const counts = data.map(d => d.parkingCount).reverse()
  rankChart.setOption({
    grid: { left: 120, right: 50, top: 10, bottom: 20 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: p => `${p[0].name}<br/>停靠次数：${p[0].value.toLocaleString()}`
    },
    xAxis: {
      type: 'value',
      axisLabel: { fontSize: 10, formatter: v => v >= 10000 ? (v / 10000).toFixed(1) + '万' : v }
    },
    yAxis: { type: 'category', data: names, axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar',
      data: counts,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#93c5fd' }, { offset: 1, color: '#2563eb' }
        ]),
        borderRadius: [0, 4, 4, 0]
      },
      label: { show: true, position: 'right', fontSize: 10, formatter: p => p.value.toLocaleString() }
    }]
  }, true)
}

// 停靠时间卡片
const showParking = ref(false)
const parkTopN = ref(20)
const parkChartRef = ref(null)
let parkChart = null

async function toggleParking() {
  showParking.value = !showParking.value
  if (showParking.value) {
    await nextTick()
    await loadParking()
  } else {
    parkChart && parkChart.dispose()
    parkChart = null
  }
}

async function loadParking() {
  const res = await stationApi.parkingStats(parkTopN.value)
  const data = res.data
  await nextTick()
  if (!parkChartRef.value) return
  if (!parkChart) parkChart = echarts.init(parkChartRef.value)
  const names = data.map(d => d.stationName).reverse()
  const minutes = data.map(d => +(d.avgDurationSeconds / 60).toFixed(1)).reverse()
  const avg = minutes.reduce((a, b) => a + b, 0) / minutes.length
  parkChart.setOption({
    grid: { left: 120, right: 60, top: 10, bottom: 20 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: p => `${p[0].name}<br/>平均停靠：${p[0].value} 分钟`
    },
    xAxis: {
      type: 'value',
      axisLabel: { fontSize: 10, formatter: v => v + ' min' }
    },
    yAxis: { type: 'category', data: names, axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar',
      data: minutes.map(v => ({
        value: v,
        itemStyle: {
          color: v > avg * 1.5
            ? new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: '#fca5a5' }, { offset: 1, color: '#dc2626' }
              ])
            : new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: '#86efac' }, { offset: 1, color: '#16a34a' }
              ]),
          borderRadius: [0, 4, 4, 0]
        }
      })),
      label: { show: true, position: 'right', fontSize: 10, formatter: p => p.value + ' min' }
    }]
  }, true)
}

const ZOOM_TO_DOT  = 11   // 放大到此级别切换到站点图
const ZOOM_TO_HEAT = 11   // 缩小到此级别切回热力图

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
    if (zoom >= ZOOM_TO_DOT && displayMode.value === 'heat') {
      setMode('dot')
    } else if (zoom < ZOOM_TO_HEAT && displayMode.value === 'dot') {
      setMode('heat')
    }
  })

  // 热力图模式下点击地图 → 找最近站点
  map.on('click', (e) => {
    if (displayMode.value !== 'heat') return
    const clng = e.lnglat.getLng()
    const clat = e.lnglat.getLat()
    // 阈值随缩放级别缩放：zoom12 约 300m，zoom14 约 75m
    const threshold = 0.03 / Math.pow(2, map.getZoom() - 12)
    let nearest = null
    let minDist = Infinity
    allStationsData.forEach(s => {
      const d = Math.sqrt((s.lng - clng) ** 2 + (s.lat - clat) ** 2)
      if (d < minDist && d < threshold) { minDist = d; nearest = s }
    })
    if (nearest) onStationClick(nearest)
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
      zIndex: 50,
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
  targetMarker = new AMap.CircleMarker({
    center: [station.lng, station.lat],
    radius: 8,
    fillColor: '#f97316',
    fillOpacity: 1,
    strokeColor: '#ffffff',
    strokeWeight: 2,
    zIndex: 200
  })
  targetMarker.setMap(map)

  if (routes.value.length > 0) drawAllRoutes(routes.value)
}

// 多条线路颜色池
const ROUTE_COLORS = ['#2563eb','#dc2626','#16a34a','#9333ea','#ea580c','#0891b2','#be185d','#ca8a04']

function clearRoutes() {
  routePolylines.forEach(p => p.setMap(null))
  routePolylines = []
  highlightedMarkers.forEach(m => m.setMap(null))
  highlightedMarkers = []
}

async function buildPolyline(route, color, showStations = false) {
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
          fullPath = fullPath.length > 0 ? fullPath.concat(pts.slice(1)) : fullPath.concat(pts)
        }
      } catch (e) {}
    })
  }
  if (fullPath.length === 0) fullPath = stations.map(s => [s.lng, s.lat])

  const polyline = new AMap.Polyline({
    path: fullPath,
    strokeColor: color,
    strokeWeight: 4,
    strokeOpacity: 0.85,
    lineJoin: 'round',
    lineCap: 'round',
    zIndex: 10
  })
  polyline.setMap(map)
  routePolylines.push(polyline)

  // 只在查看单条线路时才显示沿线站点圆圈
  if (showStations) {
    stations.forEach(s => {
      if (s.stationId === selectedStation.value?.stationId) return
      const m = new AMap.CircleMarker({
        center: [s.lng, s.lat],
        radius: 5,
        fillColor: '#ffffff',
        fillOpacity: 1,
        strokeColor: color,
        strokeWeight: 2
      })
      m.setMap(map)
      highlightedMarkers.push(m)
    })
  }
}

// 点击站点时：并行绘制所有途经线路（只画线，不画沿线站点）
async function drawAllRoutes(routes) {
  clearRoutes()
  await Promise.all(routes.map((r, i) => buildPolyline(r, ROUTE_COLORS[i % ROUTE_COLORS.length], false)))
  map.setCenter([selectedStation.value.lng, selectedStation.value.lat])
}

// 点击面板里某条线路时：只显示该条，并显示沿线站点
async function drawRoute(route) {
  currentRouteId.value = route.routeId
  clearRoutes()
  await buildPolyline(route, '#2563eb', true)
  map.setCenter([selectedStation.value.lng, selectedStation.value.lat])
}

function closePanel() {
  selectedStation.value = null
  routes.value = []
  currentRouteId.value = null
  clearRoutes()
  if (targetMarker) { targetMarker.setMap(null); targetMarker = null }
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

.analysis-btn {
  padding: 7px 16px; border: none; border-radius: 6px;
  background: white; color: #6b7280; font-size: 13px; cursor: pointer;
  box-shadow: 0 2px 8px rgba(0,0,0,0.12); text-align: center;
  transition: background 0.15s;
}
.analysis-btn:hover { background: #f3f4f6; }
.analysis-btn.active { background: #2563eb; color: white; font-weight: 500; }

/* 停靠排行卡片 */
.ranking-card {
  position: absolute; top: 16px; left: 16px; margin-top: 100px;
  width: 360px; background: white; border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  display: flex; flex-direction: column; z-index: 100;
}
.rank-chart { height: 400px; padding: 8px; }
.topn-select {
  margin-left: 6px; padding: 1px 6px;
  border: 1px solid #d1d5db; border-radius: 4px; font-size: 12px;
}
.parking-card { margin-top: 230px; }
.anomaly-tip { margin-left: 10px; display: inline-flex; align-items: center; gap: 3px; }
.dot-red { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #dc2626; }

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
