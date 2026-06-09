<template>
  <div class="page">
    <div class="sidebar">
      <div class="sidebar-title">选择线路</div>
      <input
        v-model="search"
        class="search-input"
        placeholder="搜索线路名称..."
      />
      <ul class="route-list">
        <li
          v-for="r in filteredRoutes"
          :key="r.routeId"
          :class="{ active: selectedRoute && selectedRoute.routeId === r.routeId }"
          @click="selectRoute(r)"
        >
          <span>{{ r.routeName }}</span>
          <span class="dir">{{ r.isUpOrDown }}</span>
        </li>
      </ul>
    </div>

    <div class="main">
      <div v-if="!selectedRoute" class="empty">请在左侧选择一条线路</div>
      <template v-else>
        <div class="detail-header">
          <h2>{{ selectedRoute.routeName }} · {{ selectedRoute.isUpOrDown }}</h2>
          <span class="station-count">共 {{ stations.length }} 站</span>
        </div>
        <div v-if="loadingDetail" class="tip">加载中...</div>
        <div v-else class="content-grid">
          <!-- 站点停靠次数柱状图 -->
          <div ref="barRef" class="chart-area"></div>
          <!-- 站点表格 -->
          <div class="table-area">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>站点名称</th>
                  <th>停靠次数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(s, i) in stations" :key="s.stationId">
                  <td>{{ i + 1 }}</td>
                  <td>{{ s.stationName }}</td>
                  <td>{{ s.parkingCount.toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { routeApi } from '../api'

const routes = ref([])
const search = ref('')
const selectedRoute = ref(null)
const stations = ref([])
const loadingDetail = ref(false)
const barRef = ref(null)
let chart = null

const filteredRoutes = computed(() => {
  if (!search.value) return routes.value
  return routes.value.filter(r =>
    r.routeName.includes(search.value) || r.isUpOrDown.includes(search.value)
  )
})

onMounted(async () => {
  const res = await routeApi.list()
  routes.value = res.data
})

async function selectRoute(route) {
  selectedRoute.value = route
  loadingDetail.value = true
  stations.value = []
  const res = await routeApi.detail(route.routeId)
  stations.value = res.data
  loadingDetail.value = false
  await nextTick()
  renderChart()
}

function renderChart() {
  if (!barRef.value) return
  if (!chart) {
    chart = echarts.init(barRef.value)
  } else {
    chart.resize()
  }

  const names = stations.value.map(s => s.stationName)
  const counts = stations.value.map(s => s.parkingCount)

  chart.setOption({
    grid: { left: 14, right: 14, top: 30, bottom: 60, containLabel: true },
    tooltip: {
      trigger: 'axis',
      formatter: params => `${params[0].name}<br/>停靠次数：${params[0].value.toLocaleString()}`
    },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { rotate: 45, fontSize: 10, interval: Math.floor(names.length / 20) }
    },
    yAxis: { type: 'value', name: '停靠次数' },
    series: [{
      type: 'bar',
      data: counts,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#60a5fa' }, { offset: 1, color: '#2563eb' }
        ]),
        borderRadius: [3, 3, 0, 0]
      }
    }]
  }, true)
}

function resize() { chart && chart.resize() }

onMounted(() => window.addEventListener('resize', resize))
onUnmounted(() => {
  window.removeEventListener('resize', resize)
  chart && chart.dispose()
})
</script>

<style scoped>
.page { flex: 1; display: flex; overflow: hidden; }

.sidebar {
  width: 240px; flex-shrink: 0; border-right: 1px solid #e5e7eb;
  display: flex; flex-direction: column; background: #f9fafb;
}
.sidebar-title { padding: 16px 16px 8px; font-weight: 600; font-size: 14px; color: #374151; }
.search-input {
  margin: 0 12px 8px; padding: 6px 10px;
  border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px;
}
.route-list { flex: 1; overflow-y: auto; list-style: none; }
.route-list li {
  display: flex; justify-content: space-between; align-items: center;
  padding: 9px 16px; cursor: pointer; font-size: 13px; border-bottom: 1px solid #f3f4f6;
}
.route-list li:hover { background: #f3f4f6; }
.route-list li.active { background: #eff6ff; color: #2563eb; font-weight: 500; }
.dir { font-size: 11px; color: #6b7280; }

.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; padding: 20px; }
.empty { flex: 1; display: flex; align-items: center; justify-content: center; color: #9ca3af; font-size: 15px; }
.detail-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 16px; }
.detail-header h2 { font-size: 18px; color: #111827; }
.station-count { font-size: 13px; color: #6b7280; }
.content-grid { flex: 1; display: grid; grid-template-rows: 280px 1fr; gap: 16px; overflow: hidden; }
.chart-area { width: 100%; height: 100%; }
.table-area { overflow-y: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead th { background: #f3f4f6; padding: 8px 12px; text-align: left; font-weight: 600; position: sticky; top: 0; }
tbody td { padding: 7px 12px; border-bottom: 1px solid #f3f4f6; }
.tip { text-align: center; padding: 40px; color: #6b7280; }
</style>
