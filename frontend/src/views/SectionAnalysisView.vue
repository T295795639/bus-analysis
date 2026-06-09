<template>
  <div class="page">
    <div class="header">
      <h2>路段行驶时长分析</h2>
      <div class="controls">
        <label>时间段：</label>
        <select v-model="timeRange" @change="loadData">
          <option value="all">全天</option>
          <option value="morning_peak">早高峰（7-9时）</option>
          <option value="evening_peak">晚高峰（17-19时）</option>
        </select>
        <label style="margin-left:16px">Top N：</label>
        <select v-model="topN" @change="loadData">
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </div>
    </div>
    <div v-if="loading" class="tip">加载中...</div>
    <div v-else-if="error" class="tip error">{{ error }}</div>
    <div v-else ref="chartRef" class="chart"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { sectionApi } from '../api'

const chartRef = ref(null)
const timeRange = ref('all')
const topN = ref(50)
const loading = ref(false)
const error = ref('')
let chart = null

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await sectionApi.drivingStats(timeRange.value, topN.value)
    renderChart(res.data)
  } catch (e) {
    error.value = '数据加载失败，请检查后端服务'
  } finally {
    loading.value = false
  }
}

function renderChart(data) {
  if (!chart) chart = echarts.init(chartRef.value)

  // 按耗时从大到小，取前 N 条
  const sorted = [...data].sort((a, b) => b.avgDurationSeconds - a.avgDurationSeconds)
  const names = sorted.map(d => d.sectionName || `路段${d.sectionId}`).reverse()
  const values = sorted.map(d => +(d.avgDurationSeconds / 60).toFixed(2)).reverse()
  const counts = sorted.map(d => d.recordCount).reverse()

  // 超过均值 1.5 倍视为拥堵瓶颈
  const avg = values.reduce((a, b) => a + b, 0) / values.length
  const threshold = avg * 1.5

  chart.setOption({
    grid: { left: 180, right: 80, top: 20, bottom: 40 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: params => {
        const p = params[0]
        const idx = names.length - 1 - params[0].dataIndex
        return `${p.name}<br/>平均耗时：${p.value} 分钟<br/>记录数：${counts[idx].toLocaleString()}`
      }
    },
    xAxis: {
      type: 'value',
      name: '平均耗时(分钟)',
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { fontSize: 11, width: 160, overflow: 'truncate' }
    },
    series: [{
      type: 'bar',
      data: values.map(v => ({
        value: v,
        itemStyle: {
          color: v >= threshold
            ? new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: '#fca5a5' }, { offset: 1, color: '#dc2626' }
              ])
            : new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: '#93c5fd' }, { offset: 1, color: '#2563eb' }
              ])
        }
      })),
      label: { show: true, position: 'right', formatter: p => p.value + ' min' },
      borderRadius: [0, 4, 4, 0]
    }]
  }, true)
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
.page { flex: 1; display: flex; flex-direction: column; padding: 24px; overflow: hidden; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.header h2 { font-size: 18px; color: #111827; }
.controls { font-size: 14px; color: #4b5563; }
.controls select {
  margin-left: 8px; padding: 4px 12px;
  border: 1px solid #d1d5db; border-radius: 4px;
}
.chart { flex: 1; min-height: 500px; }
.tip { text-align: center; padding: 40px; color: #6b7280; }
.error { color: #dc2626; }
</style>
