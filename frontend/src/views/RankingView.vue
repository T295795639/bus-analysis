<template>
  <div class="ranking-page">
    <div class="header">
      <h2>站点停靠次数 Top {{ topN }}</h2>
      <div class="controls">
        <label>Top N：</label>
        <select v-model="topN" @change="loadData">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </div>
    </div>
    <div ref="chartRef" class="chart"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { stationApi } from '../api'

const chartRef = ref(null)
const topN = ref(20)
let chart = null

async function loadData() {
  const res = await stationApi.ranking(topN.value)
  const data = res.data
  renderChart(data)
}

function renderChart(data) {
  if (!chart) chart = echarts.init(chartRef.value)

  const names = data.map(d => d.stationName).reverse()
  const counts = data.map(d => d.parkingCount).reverse()

  chart.setOption({
    grid: { left: 140, right: 60, top: 20, bottom: 40 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: params => {
        const p = params[0]
        return `${p.name}<br/>停靠次数：${p.value.toLocaleString()}`
      }
    },
    xAxis: {
      type: 'value',
      name: '停靠次数',
      axisLabel: { formatter: v => v >= 10000 ? (v/10000).toFixed(1) + '万' : v }
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { fontSize: 12 }
    },
    series: [{
      type: 'bar',
      data: counts,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#60a5fa' },
          { offset: 1, color: '#2563eb' }
        ]),
        borderRadius: [0, 4, 4, 0]
      },
      label: {
        show: true,
        position: 'right',
        formatter: p => p.value.toLocaleString()
      }
    }]
  })
}

function resize() { chart && chart.resize() }

onMounted(async () => {
  await nextTick()
  await loadData()
  window.addEventListener('resize', resize)
})
onUnmounted(() => {
  window.removeEventListener('resize', resize)
  chart && chart.dispose()
})
</script>

<style scoped>
.ranking-page { flex: 1; display: flex; flex-direction: column; padding: 24px; }
.header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px;
}
.header h2 { font-size: 18px; color: #111827; }
.controls { font-size: 14px; color: #4b5563; }
.controls select {
  margin-left: 8px; padding: 4px 12px;
  border: 1px solid #d1d5db; border-radius: 4px;
}
.chart { flex: 1; min-height: 600px; }
</style>
