<template>
  <div class="map-page">
    <div id="map-container"></div>

    <!-- 左上角：模式切换 + 图例 + 排行入口 -->
    <div class="toolbar">
      <div class="mode-btns">
        <button :class="{ active: displayMode === 'heat' }" @click="setMode('heat')">热力图</button>
        <button :class="{ active: displayMode === 'dot' }" @click="setMode('dot')">站点图</button>
        <button :class="{ active: displayMode === 'cluster' }" @click="setClusterMode">区域视图</button>
      </div>
      <div v-if="displayMode !== 'cluster'" class="legend">
        <div class="legend-title">途经线路数</div>
        <div class="legend-items">
          <span class="dot" style="background:#3b82f6"></span><span>1-2条</span>
          <span class="dot" style="background:#f59e0b"></span><span>3-5条</span>
          <span class="dot" style="background:#ea580c"></span><span>6-9条</span>
          <span class="dot" style="background:#dc2626"></span><span>10条+</span>
        </div>
      </div>
      <div v-else class="legend">
        <div class="legend-title">站点区域（共110个）</div>
        <div class="legend-items">
          <span v-for="(c, i) in CLUSTER_PALETTE" :key="i" class="dot" :style="{ background: c }"></span>
        </div>
      </div>
      <button :class="['analysis-btn', { active: showDwell }]" @click="toggleDwell">站点停留分析</button>
      <button :class="['analysis-btn', { active: showPeak }]" @click="togglePeak">高峰对比</button>
      <button :class="['analysis-btn', { active: showTransfer }]" @click="toggleTransfer">换乘枢纽</button>
      <button :class="['analysis-btn', { active: showClusterStat }]" @click="toggleClusterStat">区域时长</button>
      <button :class="['analysis-btn', { active: showGraph }]" @click="toggleGraph">网络图</button>
      <button :class="['analysis-btn', 'test-btn', { active: testMode }]" @click="toggleTestMode">路网底图</button>
    </div>

    <!-- 地图清除按钮 -->
    <button v-if="selectedStation" class="map-clear-btn" @click="closePanel">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="13" height="13"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      清除
    </button>

    <!-- 站点停留/枢纽分析卡片 -->
    <div v-if="showDwell" v-draggable class="ranking-card dwell-card">
      <div class="panel-header">
        <div style="flex:1;min-width:0">
          <div style="display:flex;align-items:center;gap:8px">
            <button :class="['dwell-tab-btn', { active: dwellTab === 'dwell' }]" @click="switchDwellTab('dwell')">停留分析</button>
            <button :class="['dwell-tab-btn', { active: dwellTab === 'hub' }]" @click="switchDwellTab('hub')">枢纽分析</button>
          </div>
          <div class="meta" style="display:flex;align-items:center;gap:5px;flex-wrap:wrap;margin-top:4px">
            <template v-if="dwellTab === 'dwell'">
              <span class="scatter-tag high-freq-short">高频短停</span>
              <span class="scatter-tag low-freq-long">低频长停</span>
              <span class="scatter-tag anomaly">双高异常</span>
            </template>
            <template v-else>
              <span class="scatter-tag anomaly">多线多客</span>
              <span class="scatter-tag high-freq-short">高客流少线</span>
              <span class="scatter-tag low-freq-long">多线少客</span>
            </template>
            <span v-if="selectedRankStation" class="rank-selected-pill" style="margin-left:4px">
              ◎ {{ selectedRankStation }}
              <span @click.stop="clearRankSelection" style="cursor:pointer;margin-left:4px;opacity:0.7">✕</span>
            </span>
          </div>
        </div>
        <button class="close" @click="showDwell = false">×</button>
      </div>

      <!-- 散点图区域 -->
      <div class="dwell-scatter-section">
        <div class="dwell-section-label">
          <span class="sec-dot" style="background:#8b5cf6"></span>
          {{ dwellTab === 'dwell' ? '停靠分布总览' : '客流-换乘分布' }}
          <span style="font-size:10px;color:#9ca3af;margin-left:6px">点击站点联动两侧排行</span>
        </div>
        <div ref="scatterChartRef" class="rank-chart dwell-scatter-chart"></div>
      </div>

      <!-- 双列排行 -->
      <div class="dwell-ranks">
        <div class="dwell-rank-col">
          <div class="dwell-section-label">
            <span class="sec-dot" style="background:#2563eb"></span>停靠次数排行
          </div>
          <div ref="rankScrollRef" class="dwell-rank-scroll">
            <div ref="rankChartRef" class="rank-chart"></div>
          </div>
        </div>
        <div class="dwell-rank-col">
          <!-- 停留分析：平均停靠时长 -->
          <template v-if="dwellTab === 'dwell'">
            <div class="dwell-section-label">
              <span class="sec-dot" style="background:#16a34a"></span>平均停靠时长
              <span class="anomaly-tip" style="margin-left:5px"><span class="dot-red"></span>超均值1.5倍</span>
            </div>
            <div ref="parkScrollRef" class="dwell-rank-scroll">
              <div ref="parkChartRef" class="rank-chart"></div>
            </div>
          </template>
          <!-- 枢纽分析：途经线路数 -->
          <template v-else>
            <div class="dwell-section-label">
              <span class="sec-dot" style="background:#0891b2"></span>途经线路数排行
            </div>
            <div ref="hubScrollRef" class="dwell-rank-scroll">
              <div ref="hubChartRef" class="rank-chart"></div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 高峰对比卡片 -->
    <div v-if="showPeak" v-draggable class="ranking-card peak-card">
      <div class="panel-header">
        <div>
          <div class="station-name">高峰 vs 平峰停靠对比</div>
          <div class="meta">Top <select v-model="peakTopN" @change="loadPeak" class="topn-select">
            <option :value="10">10</option><option :value="20">20</option><option :value="50">50</option>
          </select> · 按高峰比例排序</div>
        </div>
        <button class="close" @click="showPeak = false">×</button>
      </div>
      <div ref="peakChartRef" class="rank-chart"></div>
    </div>

    <!-- 换乘枢纽卡片 -->
    <div v-if="showTransfer" v-draggable class="ranking-card transfer-card">
      <div class="panel-header">
        <div>
          <div class="station-name">换乘枢纽识别</div>
          <div class="meta">Top <select v-model="transferTopN" @change="loadTransfer" class="topn-select">
            <option :value="10">10</option><option :value="20">20</option><option :value="30">30</option>
          </select> · 途经线路数 × 停靠次数</div>
        </div>
        <button class="close" @click="showTransfer = false">×</button>
      </div>
      <div ref="transferChartRef" class="rank-chart"></div>
    </div>

    <!-- 区域停靠时长卡片 -->
    <div v-if="showClusterStat" v-draggable class="ranking-card cluster-stat-card">
      <div class="panel-header">
        <div><div class="station-name">各区域平均停靠时长</div>
          <div class="meta">110个区域，按时长排序</div></div>
        <button class="close" @click="showClusterStat = false">×</button>
      </div>
      <div class="cluster-stat-scroll">
        <div ref="clusterStatChartRef" class="rank-chart"></div>
      </div>
    </div>

    <!-- 聚类网络图卡片 -->
    <div v-if="showGraph" v-draggable class="ranking-card graph-card">
      <div class="panel-header">
        <div>
          <div class="station-name">区域连通网络</div>
          <div class="meta">节点编号 = 区域编号，位置与地图地理方位对应</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="clear-btn" @click="clearClusterSelection">清除</button>
          <button class="close" @click="showGraph = false">×</button>
        </div>
      </div>
      <div ref="graphChartRef" class="rank-chart"></div>
    </div>

    <!-- 右侧站点分析面板 -->
    <div v-if="selectedStation" class="panel">

      <!-- ① 站点头部 -->
      <div class="panel-header">
        <div class="panel-hd-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
            <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
          </svg>
        </div>
        <div style="flex:1;min-width:0">
          <div class="station-name">{{ selectedStation.stationName }}</div>
          <div class="meta" style="display:flex;gap:8px;margin-top:3px">
            <span v-if="!selectedStation._isCluster" class="meta-tag">ID {{ selectedStation.stationId }}</span>
            <span v-else class="meta-tag">{{ selectedStation._stationCount }} 个站点</span>
            <span class="meta-tag blue">{{ routes.length }} 条线路</span>
          </div>
        </div>
        <button class="close" @click="closePanel">×</button>
      </div>

      <div class="panel-body">

        <!-- ② 途经线路 -->
        <div class="panel-section">
          <div class="panel-section-title">
            <span class="sec-dot" style="background:#2563eb"></span>途经线路
          </div>
          <div class="route-section-hint">选择一条线路，查看该线路的慢站点与拥堵路段</div>
          <ul class="route-list">
            <li v-for="r in routes" :key="r.routeId"
                :class="{ active: currentRouteId === r.routeId }"
                @click="drawRoute(r)">
              <span class="route-name">{{ r.routeName }}</span>
              <span class="route-action">{{ currentRouteId === r.routeId ? '分析中' : '查看瓶颈' }}</span>
            </li>
          </ul>
        </div>

        <!-- ③ 全天停靠量分布 -->
        <div v-if="!selectedStation._isCluster" class="panel-section">
          <div class="panel-section-title">
            <span class="sec-dot" style="background:#16a34a"></span>全天停靠量分布
          </div>
          <div ref="hourlyChartRef" class="hourly-chart"></div>
        </div>

        <!-- ④ 瓶颈分析 -->
        <div v-if="showAnalysis && analysisData" class="panel-section">
          <div class="panel-section-title" style="justify-content:space-between">
            <div style="display:flex;align-items:center;gap:6px">
              <span class="sec-dot" style="background:#f59e0b"></span>瓶颈分析
            </div>
            <div class="analysis-tabs">
              <button :class="['atab', { active: analysisTab==='station' }]"  @click="analysisTab='station'">慢站点</button>
              <button :class="['atab', { active: analysisTab==='section' }]" @click="analysisTab='section'">拥堵路段</button>
            </div>
          </div>
          <div class="analysis-legend">
            <span class="legend-dot" style="background:#22c55e"></span>正常
            <span class="legend-dot" style="background:#f59e0b;margin-left:8px"></span>偏慢
            <span class="legend-dot" style="background:#ef4444;margin-left:8px"></span>异常
          </div>
          <ul v-if="analysisTab==='station'" class="analysis-list">
            <li v-for="(s, idx) in analysisData.stations.filter(s=>s.avgDuration>0)"
                :key="s.stationId"
                class="analysis-item clickable"
                @mouseenter="highlightAnalysisStation(s)"
                @mouseleave="resetAnalysisStationHighlight"
                @click="focusAnalysisStation(s)">
              <span class="anomaly-bar" :style="{background: anomalyColor(s.anomalyScore)}"></span>
              <span class="analysis-index">{{ idx + 1 }}</span>
              <span class="analysis-name">{{ s.stationName }}</span>
              <span class="analysis-val">{{ (s.avgDuration/60).toFixed(1) }} 分钟</span>
            </li>
          </ul>
          <ul v-if="analysisTab==='section'" class="analysis-list">
            <li v-for="(s, idx) in [...analysisData.sections].filter(s=>s.avgDuration>0).sort((a,b)=>b.anomalyScore-a.anomalyScore).slice(0,10)"
                :key="s.sectionId"
                class="analysis-item clickable"
                @mouseenter="highlightAnalysisSection(s)"
                @mouseleave="resetAnalysisSectionHighlight"
                @click="focusAnalysisSection(s)">
              <span class="anomaly-bar" :style="{background: anomalyColor(s.anomalyScore)}"></span>
              <span class="analysis-index">{{ idx + 1 }}</span>
              <span class="analysis-name">{{ s.sectionName }}</span>
              <span class="analysis-val">{{ (s.avgDuration/60).toFixed(1) }} 分钟</span>
            </li>
          </ul>
        </div>

      </div>
    </div>

    <div v-if="loading" class="loading">加载站点数据...</div>
  </div>
</template>

<script setup>
import { onMounted, ref, onUnmounted, nextTick, reactive } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import * as echarts from 'echarts'
import { stationApi, sectionApi, routeApi } from '../api'

const AMAP_KEY = '2991ac65a0c2afea3a704f59bac52f28'

// WGS84 → GCJ02（火星坐标）转换，用于高德地图显示
function wgs84ToGcj02(lng, lat) {
  const a = 6378245.0, ee = 0.00669342162296594323
  const x = lng - 105.0, y = lat - 35.0
  let dlat = -100 + 2*x + 3*y + 0.2*y*y + 0.1*x*y + 0.2*Math.sqrt(Math.abs(x))
  dlat += (20*Math.sin(6*x*Math.PI) + 20*Math.sin(2*x*Math.PI)) * 2/3
  dlat += (20*Math.sin(y*Math.PI) + 40*Math.sin(y/3*Math.PI)) * 2/3
  dlat += (160*Math.sin(y/12*Math.PI) + 320*Math.sin(y/30*Math.PI)) * 2/3
  let dlng = 300 + x + 2*y + 0.1*x*x + 0.1*x*y + 0.1*Math.sqrt(Math.abs(x))
  dlng += (20*Math.sin(6*x*Math.PI) + 20*Math.sin(2*x*Math.PI)) * 2/3
  dlng += (20*Math.sin(x*Math.PI) + 40*Math.sin(x/3*Math.PI)) * 2/3
  dlng += (150*Math.sin(x/12*Math.PI) + 300*Math.sin(x/30*Math.PI)) * 2/3
  const radlat = lat / 180 * Math.PI
  let magic = Math.sin(radlat); magic = 1 - ee*magic*magic
  const sq = Math.sqrt(magic)
  return [
    lng + (dlng * 180) / (a / sq * Math.cos(radlat) * Math.PI),
    lat + (dlat * 180) / ((a*(1-ee)) / (magic*sq) * Math.PI)
  ]
}

let map = null
let AMap = null
let heatmap = null
let allStationsData = []           // 原始站点数据
const stationMarkers = []          // CircleMarker 列表
let highlightedMarkers = []
let routePolylines = []   // 支持同时绘制多条线路
let targetMarker = null

const loading = ref(true)
const displayMode = ref('cluster')
const selectedStation = ref(null)
const routes = ref([])
const currentRouteId = ref(null)

// ── 站点停留分析卡片（排行 + 时长 + 散点 三合一） ──
const showDwell = ref(false)
const rankChartRef = ref(null)
const rankScrollRef = ref(null)
let rankChart = null
const parkChartRef = ref(null)
const parkScrollRef = ref(null)
let parkChart = null
const hubChartRef = ref(null)
const hubScrollRef = ref(null)
let hubChart = null
const scatterChartRef = ref(null)
let scatterChart = null
const dwellTab = ref('dwell')

async function toggleDwell() {
  showDwell.value = !showDwell.value
  if (showDwell.value) {
    await nextTick()
    await loadDwellCharts()
  } else {
    rankChart && rankChart.dispose(); rankChart = null
    parkChart && parkChart.dispose(); parkChart = null
    hubChart && hubChart.dispose(); hubChart = null
    scatterChart && scatterChart.dispose(); scatterChart = null
  }
}

async function loadDwellCharts() {
  if (dwellTab.value === 'dwell') {
    await Promise.all([loadRanking(), loadParking(), loadScatter()])
  } else {
    await Promise.all([loadRanking(), loadHub(), loadScatter()])
  }
}

async function switchDwellTab(tab) {
  if (dwellTab.value === tab) return
  // 销毁当前右列图表，切换后重建
  if (tab === 'hub') { parkChart && parkChart.dispose(); parkChart = null }
  else              { hubChart  && hubChart.dispose();  hubChart  = null }
  dwellTab.value = tab
  await nextTick()
  await loadDwellCharts()
}

// 联动高亮状态
const selectedRankStation = ref(null)

function clearRankSelection() {
  selectedRankStation.value = null
  if (rankChart) loadRanking()
  if (scatterChart) loadScatter()
  if (dwellTab.value === 'dwell') { if (parkChart) loadParking() }
  else { if (hubChart) loadHub() }
}

// 渲染后滚动到被高亮的站点
function scrollToSelected(scrollEl, names) {
  if (!selectedRankStation.value || !scrollEl) return
  const idx = names.indexOf(selectedRankStation.value)
  if (idx < 0) return
  const rowH = 22
  const fromTop = (names.length - 1 - idx) * rowH + 10
  scrollEl.scrollTo({ top: Math.max(0, fromTop - scrollEl.clientHeight / 2), behavior: 'smooth' })
}

async function loadRanking() {
  const res = await stationApi.ranking()
  const data = res.data
  await nextTick()
  if (!rankChartRef.value) return
  const rankW = rankChartRef.value.parentElement?.offsetWidth || 320
  const rankH = data.length * 22 + 40
  // 用父容器宽度，避免 '100%' 在 flex/scroll 内被解析为 0
  rankChartRef.value.style.width  = rankW + 'px'
  rankChartRef.value.style.height = rankH + 'px'
  await new Promise(r => setTimeout(r, 0))   // 让浏览器提交布局
  if (!rankChart) rankChart = echarts.init(rankChartRef.value)
  else rankChart.resize({ width: rankW, height: rankH })
  const names = data.map(d => d.stationName).reverse()
  const counts = data.map(d => d.parkingCount).reverse()
  rankChart.setOption({
    grid: { left: 128, right: 40, top: 10, bottom: 20 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: p => `${p[0].name}<br/>停靠次数：${p[0].value.toLocaleString()}`
    },
    xAxis: {
      type: 'value',
      axisLabel: { fontSize: 10, formatter: v => v >= 10000 ? (v / 10000).toFixed(1) + '万' : v }
    },
    yAxis: {
      type: 'category', data: names,
      axisLabel: {
        fontSize: 11,
        color: '#111827',
        formatter: (name, idx) => {
          const rank = names.length - idx
          const label = name.length > 6 ? name.slice(0, 5) + '…' : name
          return name === selectedRankStation.value
            ? `{rk|${rank}}{hl| ${label}}`
            : `{rk|${rank}} ${label}`
        },
        rich: {
          rk: { color: '#9ca3af', fontSize: 10, width: 26, align: 'right' },
          hl: { color: '#f59e0b', fontWeight: 'bold', fontSize: 11 }
        }
      }
    },
    series: [{
      type: 'bar',
      data: counts.map((v, i) => ({
        value: v,
        itemStyle: {
          color: names[i] === selectedRankStation.value
            ? new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: '#fde68a' }, { offset: 1, color: '#f59e0b' }
              ])
            : new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: '#93c5fd' }, { offset: 1, color: '#2563eb' }
              ]),
          borderRadius: [0, 4, 4, 0]
        }
      })),
      label: { show: true, position: 'right', fontSize: 10, formatter: p => p.value.toLocaleString() }
    }]
  }, true)
  await nextTick()
  scrollToSelected(rankScrollRef.value, names)
}

async function loadParking() {
  const res = await stationApi.parkingStats()
  const data = res.data
  await nextTick()
  if (!parkChartRef.value) return
  const parkW = parkChartRef.value.parentElement?.offsetWidth || 320
  const parkH = data.length * 22 + 40
  // 用父容器宽度，避免 '100%' 在 flex/scroll 内被解析为 0
  parkChartRef.value.style.width  = parkW + 'px'
  parkChartRef.value.style.height = parkH + 'px'
  await new Promise(r => setTimeout(r, 0))   // 让浏览器提交布局
  if (!parkChart) parkChart = echarts.init(parkChartRef.value)
  else parkChart.resize({ width: parkW, height: parkH })
  const names = data.map(d => d.stationName).reverse()
  const minutes = data.map(d => +(d.avgDurationSeconds / 60).toFixed(1)).reverse()
  const avg = minutes.reduce((a, b) => a + b, 0) / minutes.length
  parkChart.setOption({
    grid: { left: 128, right: 50, top: 10, bottom: 20 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: p => `${p[0].name}<br/>平均停靠：${p[0].value} 分钟`
    },
    xAxis: {
      type: 'value',
      axisLabel: { fontSize: 10, formatter: v => v, hideOverlap: true },
      name: 'min', nameLocation: 'end', nameTextStyle: { fontSize: 10, color: '#6b7280' }
    },
    yAxis: {
      type: 'category', data: names,
      axisLabel: {
        fontSize: 11,
        color: '#111827',
        formatter: (name, idx) => {
          const rank = names.length - idx
          const label = name.length > 6 ? name.slice(0, 5) + '…' : name
          return name === selectedRankStation.value
            ? `{rk|${rank}}{hl| ${label}}`
            : `{rk|${rank}} ${label}`
        },
        rich: {
          rk: { color: '#9ca3af', fontSize: 10, width: 26, align: 'right' },
          hl: { color: '#f59e0b', fontWeight: 'bold', fontSize: 11 }
        }
      }
    },
    series: [{
      type: 'bar',
      data: minutes.map((v, i) => ({
        value: v,
        itemStyle: {
          color: names[i] === selectedRankStation.value
            ? new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: '#fde68a' }, { offset: 1, color: '#f59e0b' }
              ])
            : v > avg * 1.5
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
  await nextTick()
  scrollToSelected(parkScrollRef.value, names)
}

async function loadHub() {
  const res = await stationApi.hubRanking()
  const data = res.data
  await nextTick()
  if (!hubChartRef.value) return
  hubChartRef.value.style.height = (data.length * 22 + 40) + 'px'
  if (!hubChart) hubChart = echarts.init(hubChartRef.value)
  else hubChart.resize()
  const names = data.map(d => d.stationName).reverse()
  const counts = data.map(d => d.parkingCount).reverse()
  hubChart.setOption({
    grid: { left: 128, right: 40, top: 10, bottom: 20 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: p => `${p[0].name}<br/>途经线路：${p[0].value} 条`
    },
    xAxis: {
      type: 'value',
      axisLabel: { fontSize: 10 }
    },
    yAxis: {
      type: 'category', data: names,
      axisLabel: {
        fontSize: 11, color: '#111827',
        formatter: (name, idx) => {
          const rank = names.length - idx
          const label = name.length > 6 ? name.slice(0, 5) + '…' : name
          return name === selectedRankStation.value
            ? `{rk|${rank}}{hl| ${label}}`
            : `{rk|${rank}} ${label}`
        },
        rich: {
          rk: { color: '#9ca3af', fontSize: 10, width: 26, align: 'right' },
          hl: { color: '#f59e0b', fontWeight: 'bold', fontSize: 11 }
        }
      }
    },
    series: [{
      type: 'bar',
      data: counts.map((v, i) => ({
        value: v,
        itemStyle: {
          color: names[i] === selectedRankStation.value
            ? new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: '#fde68a' }, { offset: 1, color: '#f59e0b' }
              ])
            : new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: '#67e8f9' }, { offset: 1, color: '#0891b2' }
              ]),
          borderRadius: [0, 4, 4, 0]
        }
      })),
      label: { show: true, position: 'right', fontSize: 10, formatter: p => p.value + ' 条' }
    }]
  }, true)
  await nextTick()
  scrollToSelected(hubScrollRef.value, names)
}

async function loadScatter() {
  const res = await stationApi.parkingScatter()
  const data = res.data
  await nextTick()
  if (!scatterChartRef.value) return
  if (!scatterChart) scatterChart = echarts.init(scatterChartRef.value)

  const avgCount = data.reduce((s, d) => s + Number(d.parkingCount), 0) / data.length

  const isHub = dwellTab.value === 'hub'

  // 枢纽模式：用 allStationsData 的 routeCount 补充 Y 轴数据
  const routeCountMap = {}
  if (isHub) allStationsData.forEach(s => { routeCountMap[s.stationId] = s.routeCount || 0 })

  const avgY = isHub
    ? allStationsData.reduce((s, d) => s + (d.routeCount || 0), 0) / allStationsData.length
    : data.reduce((s, d) => s + d.avgDurationSeconds, 0) / data.length

  const points = data.map(d => {
    const isSelected = d.stationName === selectedRankStation.value
    const yVal = isHub ? (routeCountMap[d.stationId] || 0) : +(d.avgDurationSeconds / 60).toFixed(2)
    const highCount = Number(d.parkingCount) > avgCount
    const highY = isHub ? yVal > avgY : d.avgDurationSeconds > avgY
    const normalColor = highCount && highY ? '#dc2626' : highCount ? '#f59e0b' : highY ? '#8b5cf6' : '#94a3b8'
    return {
      value: [Number(d.parkingCount), yVal],
      name: d.stationName,
      symbolSize: isSelected ? 12 : 4,
      itemStyle: {
        color: isSelected ? '#f59e0b' : normalColor,
        opacity: isSelected ? 1 : 0.45,
        borderWidth: isSelected ? 2 : 0,
        borderColor: '#fff'
      }
    }
  })

  scatterChart.setOption({
    grid: { left: 60, right: 20, top: 30, bottom: 62 },
    tooltip: {
      trigger: 'item',
      formatter: p => isHub
        ? `${p.data.name}<br/>停靠次数：${p.data.value[0].toLocaleString()}<br/>途经线路：${p.data.value[1]} 条`
        : `${p.data.name}<br/>停靠次数：${p.data.value[0].toLocaleString()}<br/>平均时长：${p.data.value[1]} 分钟`
    },
    xAxis: {
      type: 'log',
      name: '停靠次数', nameLocation: 'middle', nameGap: 32,
      nameTextStyle: { fontSize: 12, fontWeight: 'bold', color: '#374151' },
      axisLabel: { formatter: v => v >= 10000 ? (v/10000).toFixed(1)+'万' : v }
    },
    yAxis: {
      type: 'value',
      name: isHub ? '途经线路数' : '平均时长(分)',
      nameLocation: 'end', nameRotate: 0,
      nameTextStyle: { fontSize: 12, fontWeight: 'bold', color: '#374151' }
    },
    series: [{
      type: 'scatter',
      data: points,
      symbolSize: 4,
      markLine: {
        silent: true,
        lineStyle: { color: '#9ca3af', type: 'dashed', width: 1 },
        data: [
          { xAxis: avgCount },
          { yAxis: isHub ? avgY : +(avgY / 60).toFixed(2) }
        ],
        label: { show: false }
      }
    }]
  }, true)

  scatterChart.off('click')
  scatterChart.on('click', params => {
    if (params.componentType !== 'series') return
    const name = params.data.name
    selectedRankStation.value = name
    const station = allStationsData.find(s => s.stationName === name)
    if (station) onStationClick(station)
    loadScatter()
    loadRanking()
    if (dwellTab.value === 'dwell') loadParking()
    else loadHub()
  })
}


// ── 高峰对比卡片 ──────────────────────────────────
const showPeak = ref(false)
const peakTopN = ref(20)
const peakChartRef = ref(null)
let peakChart = null

async function togglePeak() {
  showPeak.value = !showPeak.value
  if (showPeak.value) { await nextTick(); await loadPeak() }
  else { peakChart && peakChart.dispose(); peakChart = null }
}

async function loadPeak() {
  const res = await stationApi.peakComparison(peakTopN.value)
  const data = res.data
  await nextTick()
  if (!peakChartRef.value) return
  peakChartRef.value.style.height = (data.length * 22 + 70) + 'px'
  if (!peakChart) peakChart = echarts.init(peakChartRef.value)
  else peakChart.resize()
  const names = data.map(d => d.stationName).reverse()
  peakChart.setOption({
    grid: { left: 120, right: 20, top: 10, bottom: 50 },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: p => `${p[0].name}<br/>早高峰：${p[0].value}<br/>晚高峰：${p[1].value}<br/>平峰：${p[2].value}`
    },
    legend: { data: ['早高峰','晚高峰','平峰'], bottom: 4, itemWidth: 12, textStyle: { fontSize: 11 } },
    xAxis: { type: 'value', axisLabel: { fontSize: 10 } },
    yAxis: { type: 'category', data: names, axisLabel: { fontSize: 10 } },
    series: [
      { name: '早高峰', type: 'bar', stack: 'total', data: data.map(d => d.morningCount).reverse(), itemStyle: { color: '#f59e0b' } },
      { name: '晚高峰', type: 'bar', stack: 'total', data: data.map(d => d.eveningCount).reverse(), itemStyle: { color: '#ef4444' } },
      { name: '平峰',   type: 'bar', stack: 'total', data: data.map(d => d.offPeakCount).reverse(), itemStyle: { color: '#93c5fd' } },
    ]
  }, true)
}

// ── 换乘枢纽卡片 ──────────────────────────────────
const showTransfer = ref(false)
const transferTopN = ref(20)
const transferChartRef = ref(null)
let transferChart = null

async function toggleTransfer() {
  showTransfer.value = !showTransfer.value
  if (showTransfer.value) { await nextTick(); await loadTransfer() }
  else { transferChart && transferChart.dispose(); transferChart = null }
}

async function loadTransfer() {
  const res = await stationApi.transferHub(transferTopN.value)
  const data = res.data
  await nextTick()
  if (!transferChartRef.value) return
  transferChartRef.value.style.height = '300px'
  if (!transferChart) transferChart = echarts.init(transferChartRef.value)
  else transferChart.resize()
  transferChart.setOption({
    grid: { left: 55, right: 20, top: 30, bottom: 50 },
    tooltip: {
      trigger: 'item',
      formatter: p => `${p.data.name}<br/>途经线路：${p.data.value[0]} 条<br/>停靠次数：${p.data.value[1].toLocaleString()}`
    },
    xAxis: {
      type: 'value',
      name: '途经线路数（条）',
      nameLocation: 'end',
      nameTextStyle: { fontSize: 11, color: '#6b7280' },
      axisLabel: { fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: '停靠次数',
      nameLocation: 'end',
      nameTextStyle: { fontSize: 11, color: '#6b7280' },
      axisLabel: { fontSize: 10, formatter: v => v >= 10000 ? (v/10000).toFixed(1)+'万' : v }
    },
    series: [{
      type: 'scatter',
      data: data.map(d => ({
        name: d.stationName,
        value: [d.routeCount, d.parkingCount],
        symbolSize: Math.max(6, Math.sqrt(d.parkingCount) * 0.06),  // 缩小气泡
        itemStyle: {
          color: '#2563eb',
          opacity: 0.55,
          borderColor: '#ffffff',
          borderWidth: 1.5   // 白色描边，重叠时可区分
        }
      })),
      label: {
        show: true,
        formatter: p => p.data.name,
        fontSize: 9,
        color: '#374151',
        position: 'top',
        distance: 4
      }
    }]
  }, true)
}

// ── 区域停靠时长卡片 ──────────────────────────────
const showClusterStat = ref(false)
const clusterStatChartRef = ref(null)
let clusterStatChart = null

async function toggleClusterStat() {
  showClusterStat.value = !showClusterStat.value
  if (showClusterStat.value) { await nextTick(); await loadClusterStat() }
  else { clusterStatChart && clusterStatChart.dispose(); clusterStatChart = null }
}

async function loadClusterStat() {
  const res = await stationApi.clusterParkingStats()
  const data = res.data.filter(d => d.avgDurationSeconds > 0)
  await nextTick()
  if (!clusterStatChartRef.value) return
  const chartH = data.length * 18 + 30
  // 用父容器宽度，避免 '100%' 在 flex/scroll 内被解析为 0
  const chartW = clusterStatChartRef.value.parentElement?.offsetWidth || 320
  clusterStatChartRef.value.style.width  = chartW + 'px'
  clusterStatChartRef.value.style.height = chartH + 'px'
  await new Promise(r => setTimeout(r, 0))   // 让浏览器提交布局
  if (!clusterStatChart) {
    clusterStatChart = echarts.init(clusterStatChartRef.value)
  } else {
    clusterStatChart.resize({ width: chartW, height: chartH })
  }
  const avg = data.reduce((s, d) => s + d.avgDurationSeconds, 0) / data.length
  clusterStatChart.setOption({
    grid: { left: 50, right: 60, top: 10, bottom: 28 },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: p => `区域 ${p[0].name}<br/>平均停靠：${p[0].value} 分钟<br/>站点数：${data[data.length-1-p[0].dataIndex]?.stationCount}`
    },
    xAxis: {
      type: 'value',
      name: '分钟', nameLocation: 'end', nameTextStyle: { fontSize: 10, color: '#9ca3af' },
      axisLabel: { fontSize: 10, formatter: v => v, hideOverlap: true }
    },
    yAxis: { type: 'category', data: data.map(d => `区域${d.clusterId}`).reverse(), axisLabel: { fontSize: 10 } },
    series: [{
      type: 'bar',
      data: data.map(d => ({
        value: +(d.avgDurationSeconds / 60).toFixed(1),
        itemStyle: {
          color: d.avgDurationSeconds > avg * 1.5
            ? new echarts.graphic.LinearGradient(0,0,1,0,[{offset:0,color:'#fca5a5'},{offset:1,color:'#dc2626'}])
            : new echarts.graphic.LinearGradient(0,0,1,0,[{offset:0,color:'#93c5fd'},{offset:1,color:'#2563eb'}]),
          borderRadius: [0,4,4,0]
        }
      })).reverse(),
      label: { show: true, position: 'right', fontSize: 9, formatter: p => p.value + 'm' }
    }]
  }, true)
}

// ── 站点小时分布（站点面板内） ────────────────────
const hourlyChartRef = ref(null)
let hourlyChart = null

async function loadHourly(stationId) {
  const res = await stationApi.hourly(stationId)
  const data = res.data
  await nextTick()
  if (!hourlyChartRef.value) return
  // v-if 重建面板后 ref 指向新 DOM，旧实例必须销毁重建
  if (hourlyChart && hourlyChart.getDom() !== hourlyChartRef.value) {
    hourlyChart.dispose()
    hourlyChart = null
  }
  if (!hourlyChart) { hourlyChart = echarts.init(hourlyChartRef.value) }
  else { hourlyChart.resize() }
  const hours = Array.from({length: 24}, (_, i) => i)
  const counts = hours.map(h => (data.find(d => d.hour === h)?.count) || 0)
  hourlyChart.setOption({
    grid: { left: 35, right: 10, top: 22, bottom: 25 },
    tooltip: { trigger: 'axis', formatter: p => `${p[0].name}时：${p[0].value} 次` },
    xAxis: { type: 'category', data: hours.map(h => h+''), axisLabel: { fontSize: 9, interval: 2 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 9 } },
    series: [{
      type: 'line', data: counts, smooth: true, areaStyle: { opacity: 0.15 },
      lineStyle: { color: '#2563eb', width: 2 },
      itemStyle: { color: '#2563eb' },
      symbol: 'none',
      markArea: {
        silent: true,
        label: { fontSize: 9, position: 'insideTop' },
        data: [
          [{ name: '凌晨', xAxis: '0', itemStyle: { color: 'rgba(30,41,59,0.07)'    }, label: { color: '#94a3b8' } }, { xAxis: '6'  }],
          [{ name: '上午', xAxis: '6', itemStyle: { color: 'rgba(253,186,116,0.20)' }, label: { color: '#c2410c' } }, { xAxis: '12' }],
          [{ name: '下午', xAxis: '12', itemStyle: { color: 'rgba(125,211,252,0.18)' }, label: { color: '#0369a1' } }, { xAxis: '18' }],
          [{ name: '晚上', xAxis: '18', itemStyle: { color: 'rgba(196,181,253,0.22)' }, label: { color: '#6d28d9' } }, { xAxis: '23' }],
        ]
      }
    }]
  }, true)
}

// 聚类网络图卡片
let selectedClusterId = null  // 当前选中的区域
const showGraph = ref(true)
const graphChartRef = ref(null)
let graphChart = null

async function toggleGraph() {
  showGraph.value = !showGraph.value
  if (showGraph.value) {
    // 点网络图 → 自动切为聚类视图
    if (displayMode.value !== 'cluster') setMode('cluster')
    await nextTick()
    await loadGraph()
  } else {
    graphChart && graphChart.dispose()
    graphChart = null
    resetClusterHighlight()
  }
}

async function setClusterMode() {
  setMode('cluster')
  // 切聚类视图 → 自动打开网络图
  if (!showGraph.value) {
    showGraph.value = true
    await nextTick()
    await loadGraph()
  }
}

let graphNodes = []

function spreadGraphNodes(items) {
  const nodes = items.map(n => ({
    ...n,
    baseX: n.x,
    baseY: n.y,
    x: 50 + (n.x - 50) * 1.18,
    y: 50 + (n.y - 50) * 1.18
  }))
  const minDist = 5.8
  for (let iter = 0; iter < 90; iter++) {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i]
        const b = nodes[j]
        let dx = b.x - a.x
        let dy = b.y - a.y
        let dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 0.01) {
          dx = ((i % 5) - 2) * 0.01
          dy = ((j % 5) - 2) * 0.01
          dist = 0.01
        }
        if (dist >= minDist) continue
        const push = (minDist - dist) * 0.5
        const nx = dx / dist
        const ny = dy / dist
        a.x -= nx * push
        a.y -= ny * push
        b.x += nx * push
        b.y += ny * push
      }
    }
    nodes.forEach(n => {
      n.x += (n.baseX - n.x) * 0.015
      n.y += (n.baseY - n.y) * 0.015
      n.x = Math.max(1.5, Math.min(98.5, n.x))
      n.y = Math.max(1.5, Math.min(98.5, n.y))
    })
  }
  return nodes
}

async function loadGraph() {
  const res = await fetch('/cluster_graph.json')
  const { nodes, edges } = await res.json()
  graphNodes = nodes
  await nextTick()
  if (!graphChartRef.value) return
  if (!graphChart) graphChart = echarts.init(graphChartRef.value)
  else graphChart.resize()

  const xs = nodes.map(n => Number(n.x))
  const ys = nodes.map(n => Number(n.y))
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const spanX = maxX - minX || 1
  const spanY = maxY - minY || 1
  const graphData = spreadGraphNodes(nodes.map(n => ({
    ...n,
    x: 2 + ((Number(n.x) - minX) / spanX) * 96,
    y: 2 + ((Number(n.y) - minY) / spanY) * 96
  })))

  graphChart.setOption({
    tooltip: {
      formatter: p => {
        if (p.dataType === 'node') return `区域 ${p.data.id}<br/>站点数：${p.data.value}`
        if (p.dataType === 'edge') return `连通线路数：${p.data.value}`
        return ''
      }
    },
    series: [{
      type: 'graph',
      layout: 'none',
      coordinateSystem: undefined,
      data: graphData.map(n => ({
        id: n.id,
        name: String(n.id),
        x: n.x,
        y: n.y,
        value: n.size,
        symbolSize: 16,
        itemStyle: { color: n.color, borderColor: 'rgba(255,255,255,0.82)', borderWidth: 1.5 },
        select: { itemStyle: { borderColor: '#ffffff', borderWidth: 3, shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.4)' } },
        label: {
          show: true,
          position: 'inside',
          formatter: '{b}',
          color: '#ffffff',
          fontSize: 7,
          fontWeight: 700
        }
      })),
      edges: edges.map(e => ({
        source: e.source,
        target: e.target,
        value: e.routeCount || 1,
        lineStyle: {
          color: '#94a3b8',
          width: e.width || 0.8,
          opacity: Math.min(0.3 + (e.width || 1) * 0.1, 0.85)
        }
      })),
      roam: true,
      zoom: 0.98,
      selectedMode: 'single',
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 2, opacity: 0.9 }
      }
    }]
  }, true)

  // 点击节点 → 高亮地图 + 右侧面板显示途经线路，保持选中态
  graphChart.on('click', params => {
    if (params.dataType !== 'node') return
    const clusterId = Number(params.data.id)
    selectedClusterId = clusterId
    focusClusterOnMap(clusterId)
    highlightCluster(clusterId)
    onClusterClick(clusterId, params.data.value)
    // 图表内保持选中高亮
    graphChart.dispatchAction({ type: 'select', seriesIndex: 0, dataIndex: params.dataIndex })
  })
}

async function onClusterClick(clusterId, stationCount) {
  clearRoutes()
  clearAnalysis()
  // 复用右侧面板：用一个虚拟"站点"对象表示区域
  selectedStation.value = {
    stationId: null,
    stationName: `区域 ${clusterId}`,
    _isCluster: true,
    _clusterId: clusterId,
    _stationCount: stationCount,
  }
  const res = await routeApi.byCluster(clusterId)
  routes.value = res.data
  currentRouteId.value = null
  await drawRoutePreview(routes.value)
}

function highlightCluster(clusterId) {
  clusterMarkers.forEach(m => {
    const s = m.getExtData()
    if (s.clusterId === clusterId) {
      m.setOptions({ radius: 7, fillOpacity: 1, strokeColor: '#ffffff', strokeWeight: 2, zIndex: 100 })
    } else {
      m.setOptions({ radius: 3, fillOpacity: 0.15, strokeWeight: 0, zIndex: 50 })
    }
  })
}

function muteClusterMarkers() {
  clusterMarkers.forEach(m => {
    m.setOptions({ radius: 2.5, fillOpacity: 0.08, strokeWeight: 0, zIndex: 30 })
  })
}

function focusClusterOnMap(clusterId) {
  if (!map) return
  const stations = allStationsData.filter(s => Number(s.clusterId) === Number(clusterId))
  if (!stations.length) return

  const center = stations.reduce((acc, s) => {
    acc.lng += Number(s.lng)
    acc.lat += Number(s.lat)
    return acc
  }, { lng: 0, lat: 0 })
  center.lng /= stations.length
  center.lat /= stations.length

  map.setZoomAndCenter(Math.max(map.getZoom(), 14), [center.lng, center.lat])
}

function clearClusterSelection() {
  selectedClusterId = null
  resetClusterHighlight()
  clearRoutes()
  clearAnalysis()
  selectedStation.value = null
  routes.value = []
  currentRouteId.value = null
  if (graphChart) graphChart.dispatchAction({ type: 'unselect', seriesIndex: 0 })
}

function resetClusterHighlight() {
  clusterMarkers.forEach(m => {
    m.setOptions({ radius: 4, fillOpacity: 0.85, strokeColor: 'rgba(255,255,255,0.5)', strokeWeight: 0.5, zIndex: 50 })
  })
}

const ZOOM_TO_DOT  = 11
const ZOOM_TO_HEAT = 11

// 图着色结果：相邻区域颜色不同，16色覆盖110个区域
const CLUSTER_COLOR_MAP = {"0":"#e6194b","1":"#3cb44b","2":"#e6194b","3":"#3cb44b","4":"#e6194b","5":"#3cb44b","6":"#e6194b","7":"#4363d8","8":"#e6194b","9":"#3cb44b","10":"#4363d8","11":"#e6194b","12":"#e6194b","13":"#3cb44b","14":"#3cb44b","15":"#f58231","16":"#911eb4","17":"#3cb44b","18":"#911eb4","19":"#42d4f4","20":"#f032e6","21":"#f58231","22":"#f58231","23":"#e6194b","24":"#911eb4","25":"#42d4f4","26":"#bfef45","27":"#469990","28":"#4363d8","29":"#469990","30":"#e6194b","31":"#800000","32":"#f032e6","33":"#f58231","34":"#800000","35":"#42d4f4","36":"#aaffc3","37":"#4363d8","38":"#aaffc3","39":"#9a6324","40":"#f58231","41":"#911eb4","42":"#000075","43":"#f58231","44":"#4363d8","45":"#a9a9a9","46":"#bfef45","47":"#ffe119","48":"#f032e6","49":"#0082c8","50":"#000075","51":"#800000","52":"#42d4f4","53":"#9a6324","54":"#f032e6","55":"#911eb4","56":"#f58231","57":"#bfef45","58":"#f032e6","59":"#800000","60":"#911eb4","61":"#e6194b","62":"#aaffc3","63":"#4363d8","64":"#a9a9a9","65":"#3cb44b","66":"#4363d8","67":"#42d4f4","68":"#911eb4","69":"#3cb44b","70":"#42d4f4","71":"#bfef45","72":"#469990","73":"#ffe119","74":"#bfef45","75":"#4363d8","76":"#000075","77":"#4363d8","78":"#469990","79":"#0082c8","80":"#e6194b","81":"#9a6324","82":"#aaffc3","83":"#f58231","84":"#911eb4","85":"#3cb44b","86":"#f032e6","87":"#f032e6","88":"#42d4f4","89":"#9a6324","90":"#aaffc3","91":"#9a6324","92":"#469990","93":"#9a6324","94":"#bfef45","95":"#469990","96":"#e6194b","97":"#000075","98":"#4363d8","99":"#42d4f4","100":"#ffe119","101":"#000075","102":"#f032e6","103":"#bfef45","104":"#aaffc3","105":"#a9a9a9","106":"#aaffc3","107":"#9a6324","108":"#000075","109":"#ffe119"}
const CLUSTER_PALETTE = [...new Set(Object.values(CLUSTER_COLOR_MAP))]
let clusterMarkers = []

function colorByCluster(clusterId) {
  if (clusterId == null) return '#94a3b8'
  return CLUSTER_COLOR_MAP[String(clusterId)] ?? '#94a3b8'
}

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
    if (displayMode.value === 'cluster') return
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
  allStationsData = res.data.filter(s => s.lng && s.lat).map(s => {
    const [lng, lat] = wgs84ToGcj02(s.lng, s.lat)
    return { ...s, lng, lat }
  })

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

  // 默认聚类视图，和网络图形成区域联动入口
  setMode('cluster')
  loading.value = false
}

function setMode(mode) {
  displayMode.value = mode

  // 先全部清除
  heatmap && heatmap.hide()
  if (stationMarkers.length) map.remove(stationMarkers)
  if (clusterMarkers.length) {
    resetClusterHighlight()
    map.remove(clusterMarkers)
    clusterMarkers = []
  }

  if (mode === 'heat') {
    heatmap && heatmap.show()
  } else if (mode === 'dot') {
    map.add(stationMarkers)
  } else if (mode === 'cluster') {
    // 按 cluster_id 着色，懒创建
    if (clusterMarkers.length === 0) {
      allStationsData.forEach(s => {
        const m = new AMap.CircleMarker({
          center: [s.lng, s.lat],
          radius: 4,
          fillColor: colorByCluster(s.clusterId),
          fillOpacity: 0.85,
          strokeColor: 'rgba(255,255,255,0.5)',
          strokeWeight: 0.5,
          cursor: 'pointer',
          zIndex: 50,
          extData: s
        })
        m.on('click', () => onStationClick(s))
        clusterMarkers.push(m)
      })
    }
    map.add(clusterMarkers)
  }
}

async function onStationClick(station) {
  selectedStation.value = station

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

  // 并行获取路线名称表 + 路段数据
  const [routeRes, sectionRes] = await Promise.all([
    stationApi.listRoutes(station.stationId),
    sectionApi.pathsByStation(station.stationId)
  ])

  // 用 route_id → routeName 建立名称映射
  const nameMap = {}
  routeRes.data.forEach(r => { nameMap[String(r.routeId)] = r.routeName })

  // 从 section route_number 派生路线列表，按路线前缀去重（不区分上下行）
  const sections = sectionRes.data
  const seen = new Set()
  routes.value = []
  sections.forEach(sec => {
    const parts = sec.routeNumber.split('_')
    const prefix = parts.slice(0, -1).join('_')  // '135' or 'K210'
    if (seen.has(prefix)) return
    seen.add(prefix)
    const numId = parseInt(prefix)
    const routeName = nameMap[String(numId)] || prefix
    routes.value.push({ routeNumber: prefix, routeId: prefix, routeName })
  })

  drawAllRoutes(sections)
  if (station.stationId >= 1000) loadHourly(station.stationId)
}

// 多条线路颜色池
const ROUTE_COLORS = ['#2563eb','#dc2626','#16a34a','#9333ea','#ea580c','#0891b2','#be185d','#ca8a04']

function clearRoutes() {
  routePolylines.forEach(p => p.setMap(null))
  routePolylines = []
  highlightedMarkers.forEach(m => m.setMap(null))
  highlightedMarkers = []
}

function fitCurrentRouteView() {
  const overlays = [...routePolylines, ...highlightedMarkers]
  if (!map || overlays.length === 0) return
  map.setFitView(overlays, false, [72, 360, 72, 32])
}

async function drawRoutePreview(routeList) {
  const results = await Promise.allSettled(routeList.map(r => sectionApi.pathsByRoute(r.routeId)))

  results.forEach((result, i) => {
    if (result.status !== 'fulfilled') return
    const sections = result.value.data || []
    const color = ROUTE_COLORS[i % ROUTE_COLORS.length]

    sections.forEach(sec => {
      try {
        const pts = JSON.parse(sec.path).map(([lng, lat]) => wgs84ToGcj02(lng, lat))
        if (!pts || pts.length < 2) return
        const poly = new AMap.Polyline({
          path: pts,
          strokeColor: color,
          strokeWeight: 2.5,
          strokeOpacity: 0.28,
          lineJoin: 'round',
          lineCap: 'round',
          zIndex: 8
        })
        poly.setMap(map)
        routePolylines.push(poly)
      } catch (e) {}
    })
  })
}

async function buildPolyline(route, color, showStations = false) {
  const [stationRes, sectionRes] = await Promise.all([
    stationApi.listByRoute(route.routeId),
    sectionApi.pathsByRoute(route.routeId)
  ])
  const stations = stationRes.data.filter(s => s.lng && s.lat && s.stationId > 10000)
  const sections = sectionRes.data

  if (sections && sections.length > 0) {
    sections.forEach(sec => {
      try {
        const pts = JSON.parse(sec.path).map(([lng, lat]) => wgs84ToGcj02(lng, lat))
        if (!pts || pts.length < 2) return
        const poly = new AMap.Polyline({
          path: pts,
          strokeColor: color,
          strokeWeight: 3,
          strokeOpacity: 0.42,
          lineJoin: 'round',
          lineCap: 'round',
          zIndex: 10
        })
        poly.setMap(map)
        routePolylines.push(poly)
      } catch (e) {}
    })
  }

  // 只在查看单条线路时才显示沿线站点圆圈
  if (showStations) {
    stations.forEach(s => {
      if (s.stationId === selectedStation.value?.stationId) return
      const m = new AMap.CircleMarker({
        center: wgs84ToGcj02(s.lng, s.lat),
        radius: 3.8,
        fillColor: color,
        fillOpacity: 0.55,
        strokeColor: color,
        strokeOpacity: 0.35,
        strokeWeight: 0.8,
        zIndex: 60
      })
      m.setMap(map)
      highlightedMarkers.push(m)
    })
  }
}

async function drawRouteStations(route, color) {
  const stationRes = await stationApi.listByRoute(route.routeId)
  const stations = stationRes.data.filter(s => s.lng && s.lat && s.stationId > 10000)
  stations.forEach(s => {
    if (s.stationId === selectedStation.value?.stationId) return
    const m = new AMap.CircleMarker({
      center: wgs84ToGcj02(s.lng, s.lat),
      radius: 3.8,
      fillColor: color,
      fillOpacity: 0.55,
      strokeColor: color,
      strokeOpacity: 0.35,
      strokeWeight: 0.8,
      zIndex: 60
    })
    m.setMap(map)
    highlightedMarkers.push(m)
  })
}

// 绘制所有途经线路路段（sections 已由 onStationClick 获取，按 routeNumber 分组上色）
function drawAllRoutes(sections) {
  clearRoutes()
  const groups = {}
  sections.forEach(sec => {
    if (!groups[sec.routeNumber]) groups[sec.routeNumber] = []
    groups[sec.routeNumber].push(sec)
  })
  Object.values(groups).forEach((segs, i) => {
    const color = ROUTE_COLORS[i % ROUTE_COLORS.length]
    segs.forEach(sec => {
      try {
        const pts = JSON.parse(sec.path).map(([lng, lat]) => wgs84ToGcj02(lng, lat))
        if (!pts || pts.length < 2) return
        const poly = new AMap.Polyline({
          path: pts, strokeColor: color, strokeWeight: 4,
          strokeOpacity: 0.85, lineJoin: 'round', lineCap: 'round', zIndex: 10
        })
        poly.setMap(map)
        routePolylines.push(poly)
      } catch (e) {}
    })
  })
  const { lng, lat } = selectedStation.value
  map.setZoomAndCenter(Math.max(map.getZoom(), 15), [lng, lat])
}

// ── 瓶颈分析 ──────────────────────────────────────
const analysisData = ref(null)        // RouteAnalysisVO
const analysisMarkers = []            // 站点颜色 Marker
const analysisSections = []           // 路段颜色 Polyline
const analysisStationLabels = []      // 地图站点序号
const analysisStationMarkerMap = new Map()
const analysisSectionMap = new Map()
let activeAnalysisStationMarker = null
let activeAnalysisStationHalo = null
let activeAnalysisSection = null
const showAnalysis = ref(false)
const analysisTab = ref('station')    // 'station' | 'section'

function anomalyColor(score) {
  if (!score || score < 1.0) return '#22c55e'
  if (score < 1.5) return '#f59e0b'
  return '#ef4444'
}

function stationBottleneckStyle(score) {
  if (!score || score < 1.0) {
    return { radius: 4.5, fillOpacity: 0.78, strokeWeight: 1, zIndex: 115 }
  }
  if (score < 1.5) {
    return { radius: 6, fillOpacity: 0.88, strokeWeight: 1.4, zIndex: 120 }
  }
  return { radius: 7, fillOpacity: 0.94, strokeWeight: 1.8, zIndex: 125 }
}

function applyStationMarkerStyle(marker, station, active = false) {
  const color = anomalyColor(station.anomalyScore)
  const style = stationBottleneckStyle(station.anomalyScore)
  marker.setOptions({
    radius: active ? style.radius + 3 : style.radius,
    fillColor: color,
    fillOpacity: active ? 1 : style.fillOpacity,
    strokeColor: '#ffffff',
    strokeOpacity: active ? 1 : 0.9,
    strokeWeight: active ? 3 : style.strokeWeight,
    zIndex: active ? 180 : style.zIndex
  })
}

function resetAnalysisStationHighlight() {
  if (!activeAnalysisStationMarker) return
  const station = activeAnalysisStationMarker.getExtData()
  applyStationMarkerStyle(activeAnalysisStationMarker, station, false)
  activeAnalysisStationMarker = null
  if (activeAnalysisStationHalo) {
    activeAnalysisStationHalo.setMap(null)
    activeAnalysisStationHalo = null
  }
}

function highlightAnalysisStation(station) {
  resetAnalysisStationHighlight()
  const marker = analysisStationMarkerMap.get(Number(station.stationId))
  if (!marker) return
  activeAnalysisStationMarker = marker
  applyStationMarkerStyle(marker, station, true)
  const color = anomalyColor(station.anomalyScore)
  const style = stationBottleneckStyle(station.anomalyScore)
  activeAnalysisStationHalo = new AMap.CircleMarker({
    center: marker.getCenter(),
    radius: style.radius + 7,
    fillColor: color,
    fillOpacity: 0.16,
    strokeColor: color,
    strokeOpacity: 0.65,
    strokeWeight: 2,
    zIndex: 170,
    bubble: true
  })
  activeAnalysisStationHalo.setMap(map)
}

function focusAnalysisStation(station) {
  highlightAnalysisStation(station)
  const marker = analysisStationMarkerMap.get(Number(station.stationId))
  if (!marker || !map) return
  const pos = marker.getCenter()
  map.setZoomAndCenter(Math.max(map.getZoom(), 15), pos)
  selectedStation.value = station
  loadHourly(station.stationId)
}

function sectionBottleneckStyle(score, active = false) {
  const baseWeight = !score || score < 1.0 ? 4 : score < 1.5 ? 6 : 8
  return {
    strokeWeight: active ? baseWeight + 5 : baseWeight,
    strokeOpacity: active ? 1 : (!score || score < 1.0 ? 0.56 : 0.86),
    zIndex: active ? 260 : (!score || score < 1.0 ? 108 : 118)
  }
}

function applySectionStyle(poly, section, active = false) {
  const color = anomalyColor(section.anomalyScore)
  const style = sectionBottleneckStyle(section.anomalyScore, active)
  poly.setOptions({
    strokeColor: color,
    strokeWeight: style.strokeWeight,
    strokeOpacity: style.strokeOpacity,
    zIndex: style.zIndex,
    strokeStyle: 'solid'
  })
}

function resetAnalysisSectionHighlight() {
  if (!activeAnalysisSection) return
  const section = activeAnalysisSection.getExtData()
  applySectionStyle(activeAnalysisSection, section, false)
  activeAnalysisSection = null
}

function highlightAnalysisSection(section) {
  resetAnalysisSectionHighlight()
  const poly = analysisSectionMap.get(String(section.sectionId))
  if (!poly) return
  activeAnalysisSection = poly
  applySectionStyle(poly, section, true)
}

function focusAnalysisSection(section) {
  highlightAnalysisSection(section)
  const poly = analysisSectionMap.get(String(section.sectionId))
  if (!poly || !map) return
  const path = poly.getPath()
  if (!path?.length) return
  const mid = path[Math.floor(path.length / 2)]
  map.setZoomAndCenter(Math.max(map.getZoom(), 14), mid)
}

function clearAnalysis() {
  analysisMarkers.forEach(m => m.setMap(null))
  analysisSections.forEach(p => p.setMap(null))
  analysisStationLabels.forEach(t => t.setMap(null))
  if (activeAnalysisStationHalo) activeAnalysisStationHalo.setMap(null)
  analysisMarkers.length = 0
  analysisSections.length = 0
  analysisStationLabels.length = 0
  analysisStationMarkerMap.clear()
  analysisSectionMap.clear()
  activeAnalysisStationMarker = null
  activeAnalysisStationHalo = null
  activeAnalysisSection = null
  analysisData.value = null
  showAnalysis.value = false
}

async function runAnalysis(routeId) {
  clearAnalysis()
  const res = await routeApi.analysis(routeId)
  analysisData.value = res.data

  // 站点颜色 Marker
  let stationIndex = 0
  for (const s of res.data.stations) {
    if (!s.lng || !s.lat) continue
    if (s.avgDuration > 0) stationIndex += 1
    const color = anomalyColor(s.anomalyScore)
    const style = stationBottleneckStyle(s.anomalyScore)
    const center = wgs84ToGcj02(s.lng, s.lat)
    const m = new AMap.CircleMarker({
      center,
      radius: style.radius,
      fillColor: color,
      fillOpacity: style.fillOpacity,
      strokeColor: '#ffffff',
      strokeOpacity: 0.9,
      strokeWeight: style.strokeWeight,
      zIndex: style.zIndex,
      cursor: 'pointer',
      extData: s
    })
    m.on('click', () => focusAnalysisStation(s))
    m.setMap(map)
    analysisMarkers.push(m)
    analysisStationMarkerMap.set(Number(s.stationId), m)

    if (s.avgDuration > 0) {
      const label = new AMap.Text({
        text: String(stationIndex),
        position: center,
        offset: new AMap.Pixel(7, -17),
        zIndex: 190,
        cursor: 'pointer',
        style: {
          padding: '1px 4px',
          borderRadius: '8px',
          border: '1px solid rgba(37,99,235,0.28)',
          background: 'rgba(255,255,255,0.92)',
          color: '#1d4ed8',
          fontSize: '10px',
          fontWeight: '700',
          lineHeight: '14px',
          boxShadow: '0 1px 4px rgba(15,23,42,0.18)'
        }
      })
      label.on('click', () => focusAnalysisStation(s))
      label.setMap(map)
      analysisStationLabels.push(label)
    }
  }

  // 路段颜色 Polyline
  for (const sec of res.data.sections) {
    if (!sec.path || sec.path.length < 2) continue
    const color = anomalyColor(sec.anomalyScore)
    const style = sectionBottleneckStyle(sec.anomalyScore, false)
    const pts = sec.path.map(p => { const [lng, lat] = wgs84ToGcj02(p[0], p[1]); return new AMap.LngLat(lng, lat) })
    const poly = new AMap.Polyline({
      path: pts,
      strokeColor: color,
      strokeWeight: style.strokeWeight,
      strokeOpacity: style.strokeOpacity,
      zIndex: style.zIndex,
      cursor: 'pointer',
      extData: sec
    })
    poly.on('mouseover', () => highlightAnalysisSection(sec))
    poly.on('mouseout', resetAnalysisSectionHighlight)
    poly.on('click', () => {
      analysisTab.value = 'section'
      focusAnalysisSection(sec)
    })
    poly.setMap(map)
    analysisSections.push(poly)
    analysisSectionMap.set(String(sec.sectionId), poly)
  }

  showAnalysis.value = true
}

// 点击面板里某条线路时：只显示该条，并显示沿线站点
async function drawRoute(route) {
  currentRouteId.value = route.routeId
  clearRoutes()
  muteClusterMarkers()
  await drawRouteStations(route, '#2563eb')
  if (selectedStation.value?.lng && selectedStation.value?.lat) {
    map.setCenter([selectedStation.value.lng, selectedStation.value.lat])
  }
  await runAnalysis(route.routeId)
  fitCurrentRouteView()
}

function closePanel() {
  selectedStation.value = null
  routes.value = []
  currentRouteId.value = null
  clearRoutes()
  clearAnalysis()
  if (targetMarker) { targetMarker.setMap(null); targetMarker = null }
}

// ── 路段测试模式 ──────────────────────────────────
const testMode = ref(false)
let testPolylines = []

async function toggleTestMode() {
  testMode.value = !testMode.value
  if (testMode.value) {
    const res = await sectionApi.allPaths()
    res.data.forEach(sec => {
      try {
        const pts = JSON.parse(sec.path).map(([lng, lat]) => wgs84ToGcj02(lng, lat))
        if (pts.length < 2) return
        const poly = new AMap.Polyline({
          path: pts,
          strokeColor: '#60a5fa',
          strokeWeight: 1.5,
          strokeOpacity: 0.55,
          zIndex: 1
        })
        poly.setMap(map)
        testPolylines.push(poly)
      } catch (e) {}
    })
  } else {
    testPolylines.forEach(p => p.setMap(null))
    testPolylines = []
  }
}

onMounted(async () => {
  await initMap()
  // 默认只展示网络图，其他分析图表按需打开
  await nextTick()
  await loadGraph()
})
onUnmounted(() => map && map.destroy())

// ── 拖拽指令 ──────────────────────────────────────
// 初始位置由 CSS bottom/left 控制；首次拖拽时才转为 top/left 绝对定位，
// 避免卡片挂载时图表未渲染导致高度计算错误。
const vDraggable = {
  mounted(el) {
    const handle = el.querySelector('.panel-header') || el
    handle.style.cursor = 'move'
    handle.style.userSelect = 'none'

    let pinned = false  // 是否已转为 top/left 定位
    let startX, startY, startLeft, startTop

    function onMouseMove(e) {
      const dx = e.clientX - startX
      const dy = e.clientY - startY
      el.style.left = (startLeft + dx) + 'px'
      el.style.top  = (startTop  + dy) + 'px'
    }

    function onMouseUp() {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }

    handle.addEventListener('mousedown', e => {
      if (e.target.closest('button, select, input')) return
      e.preventDefault()

      // 首次拖拽：把当前渲染位置（含图表高度）固化为 top/left
      if (!pinned) {
        const rect = el.getBoundingClientRect()
        const parent = el.offsetParent || document.body
        const pr = parent.getBoundingClientRect()
        el.style.top    = (rect.top  - pr.top)  + 'px'
        el.style.left   = (rect.left - pr.left) + 'px'
        el.style.bottom = 'auto'
        pinned = true
      }

      startX    = e.clientX
      startY    = e.clientY
      startLeft = parseInt(el.style.left) || 0
      startTop  = parseInt(el.style.top)  || 0
      document.addEventListener('mousemove', onMouseMove)
      document.addEventListener('mouseup',   onMouseUp)
    })
  }
}
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
.test-btn { border: 1.5px dashed #d1d5db; color: #9ca3af; }
.test-btn.active { background: #7c3aed; border-color: #7c3aed; color: white; }
.dwell-tab-btn {
  padding: 2px 10px; font-size: 12px; font-weight: 600; border-radius: 6px;
  border: 1.5px solid #e5e7eb; background: transparent; color: #6b7280; cursor: pointer;
  transition: all .15s;
}
.dwell-tab-btn.active { background: #2563eb; border-color: #2563eb; color: #fff; }

/* 停靠排行卡片 — 底部并排布局，left 由各子类覆盖 */
.ranking-card {
  position: absolute; bottom: 16px; left: 16px; margin: 0;
  width: 320px; background: white; border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  display: flex; flex-direction: column; z-index: 100;
}
.ranking-card .panel-header {
  justify-content: space-between;
}
.ranking-card .panel-header > div:first-child {
  flex: 1;
  min-width: 0;
}
.rank-chart { min-height: 100px; padding: 8px; }
.topn-select {
  margin-left: 6px; padding: 1px 6px;
  border: 1px solid #d1d5db; border-radius: 4px; font-size: 12px;
}
/* 站点停留分析卡片 */
.dwell-card { left: 16px; width: 700px; }
.dwell-scatter-section { border-bottom: 1px solid #f3f4f6; }
.dwell-section-label {
  padding: 7px 12px 4px;
  font-size: 11px; font-weight: 600; color: #374151;
  display: flex; align-items: center; gap: 5px;
}
.dwell-scatter-chart { height: 240px !important; }
.dwell-ranks { display: flex; border-top: 1px solid #f3f4f6; }
.dwell-rank-col { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.dwell-rank-col:first-child { border-right: 1px solid #f3f4f6; }
.dwell-rank-scroll { height: 380px; overflow-y: auto; }
/* 兼容旧的 rank-scroll（用于非 dwell 卡片） */
.rank-scroll { height: 470px; overflow-y: auto; }
/* 联动高亮的站点 pill */
.rank-selected-pill {
  display: inline-flex; align-items: center;
  padding: 1px 7px; border-radius: 10px; font-size: 11px;
  background: #fef3c7; color: #92400e; border: 1px solid #fde68a;
}
.peak-card       { left: 1044px; width: 380px; }
.transfer-card   { left: 1440px; width: 340px; }
.cluster-stat-card { left: 1796px; width: 340px; }
.cluster-stat-scroll { max-height: 420px; overflow-y: auto; }
.graph-card {
  bottom: 18px;
  left: 16px;
  width: clamp(500px, 38vw, 600px);
}
.graph-card .rank-chart { height: 400px !important; }
.scatter-tag {
  display: inline-block; padding: 1px 7px; border-radius: 10px;
  font-size: 11px; margin-right: 6px; margin-top: 4px;
}
.high-freq-short { background: #fef3c7; color: #92400e; }
.low-freq-long   { background: #ede9fe; color: #5b21b6; }
.anomaly         { background: #fee2e2; color: #991b1b; }
.analysis-panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.analysis-tabs { display: flex; gap: 4px; }
.atab { padding: 2px 10px; font-size: 11px; border-radius: 4px; border: 1px solid #d1d5db; background: #f9fafb; cursor: pointer; color: #374151; }
.atab.active { background: #2563eb; color: #fff; border-color: #2563eb; }
.analysis-legend { font-size: 11px; color: #6b7280; margin-bottom: 6px; display: flex; align-items: center; }
.legend-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.analysis-list { list-style: none; padding: 0; margin: 0; }
.analysis-item { display: flex; align-items: center; gap: 6px; padding: 4px 0; border-bottom: 1px solid #f3f4f6; font-size: 12px; }
.analysis-item.clickable {
  cursor: pointer;
  border-radius: 5px;
  padding-left: 4px;
  padding-right: 4px;
}
.analysis-item.clickable:hover {
  background: #f8fafc;
}
.anomaly-bar { width: 4px; height: 24px; border-radius: 2px; flex-shrink: 0; }
.analysis-index {
  width: 18px;
  flex-shrink: 0;
  text-align: right;
  font-size: 11px;
  color: #9ca3af;
}
.analysis-name { flex: 1; color: #111827; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.analysis-val { color: #6b7280; flex-shrink: 0; }
.hourly-title { font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 6px; }
.hourly-chart { height: 120px; }
.clear-btn {
  padding: 2px 10px; font-size: 12px; border-radius: 4px; cursor: pointer;
  border: 1px solid #d1d5db; background: #f9fafb; color: #374151;
}
.clear-btn:hover { background: #f3f4f6; }
.map-clear-btn {
  position: absolute;
  top: 14px;
  right: 16px;
  z-index: 200;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 11px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  background: rgba(255,255,255,0.92);
  color: #64748b;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0,0,0,0.10);
  backdrop-filter: blur(4px);
  transition: all 0.15s;
  letter-spacing: 0.02em;
}
.map-clear-btn:hover {
  background: #fff;
  color: #374151;
  border-color: #cbd5e1;
  box-shadow: 0 3px 12px rgba(0,0,0,0.14);
}
.anomaly-tip { margin-left: 10px; display: inline-flex; align-items: center; gap: 3px; }
.dot-red { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #dc2626; }

/* 右侧面板 */
/* ── 右侧面板 ── */
.panel {
  position: absolute; top: 16px; right: 16px;
  width: 300px; max-height: calc(100vh - 32px);
  background: #fff; border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.13);
  display: flex; flex-direction: column; z-index: 100; overflow: hidden;
}
/* 头部 */
.panel-header {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 14px 14px 12px;
  background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%);
  border-bottom: 1px solid #e5e7eb; flex-shrink: 0;
}
.panel-hd-icon {
  width: 32px; height: 32px; border-radius: 8px;
  background: #2563eb; color: #fff;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.station-name { font-size: 15px; font-weight: 700; color: #111827; line-height: 1.3; }
.meta { font-size: 11px; color: #6b7280; margin-top: 4px; }
.meta-tag {
  display: inline-flex; align-items: center;
  padding: 1px 7px; border-radius: 8px; font-size: 11px;
  background: #f3f4f6; color: #374151;
}
.meta-tag.blue { background: #dbeafe; color: #1d4ed8; }
.close {
  background: none; border: none; font-size: 20px;
  color: #9ca3af; cursor: pointer; line-height: 1; padding: 0; flex-shrink: 0;
}
.close:hover { color: #374151; }
/* 内容区（可滚动） */
.panel-body { flex: 1; overflow-y: auto; }
/* 各功能分区 */
.panel-section { padding: 10px 14px 12px; border-bottom: 1px solid #f3f4f6; }
.panel-section:last-child { border-bottom: none; }
.panel-section-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 8px;
}
.sec-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
/* 线路列表 */
.route-section-hint {
  margin: -2px 0 8px;
  font-size: 11px;
  line-height: 1.5;
  color: #6b7280;
}
.route-list { list-style: none; max-height: 180px; overflow-y: auto; margin: 0; padding: 0; }
.route-list li {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 10px; cursor: pointer; border-radius: 6px;
  transition: background 0.1s; margin-bottom: 2px;
}
.route-list li:hover { background: #f9fafb; }
.route-list li.active { background: #eff6ff; }
.route-name { font-size: 13px; color: #111827; }
.route-list li.active .route-name { color: #2563eb; font-weight: 600; }
.route-action {
  margin-left: 10px;
  flex-shrink: 0;
  font-size: 11px;
  color: #9ca3af;
}
.route-list li:hover .route-action { color: #2563eb; }
.route-list li.active .route-action {
  color: #2563eb;
  font-weight: 600;
}
.direction { font-size: 11px; color: #9ca3af; }

.loading {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  padding: 12px 24px; background: rgba(0,0,0,0.7); color: white;
  border-radius: 6px; font-size: 14px; z-index: 200;
}
</style>
