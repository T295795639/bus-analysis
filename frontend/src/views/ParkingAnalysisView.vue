<template>
  <div class="page">
    <div class="header">
      <h2>站点平均停靠时长分析</h2>
      <div class="controls">
        <label>Top N：</label>
        <select v-model="topN" @change="loadData">
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </div>
    </div>
    <div class="legend">
      <span class="dot abnormal"></span>异常站点（超均值1.5倍）
      <span class="dot normal" style="margin-left:16px"></span>正常站点
    </div>
    <div v-if="loading" class="tip">加载中...</div>
    <div v-else-if="error" class="tip error">{{ error }}</div>
    <div v-else ref="chartRef" class="chart"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { stationApi } from '../api'

const chartRef = ref(null)
const topN = ref(20)
const loading = ref(false)
const error = ref('')
let chart = null

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await stationApi.parkingStats(topN.value)
    renderChart(res.data)
  } catch (e) {
    error.value = '数据加载失败，请检查后端服务'
  } finally {
    loading.value = false
  }
}

function renderChart(data) {
  if (!chart) chart = echarts.init(chartRef.value)

  const sorted = [...data].sort((a, b) => b.avgDurationSeconds - a.avgDurationSeconds)
  const avg = sorted.reduce((s, d) => s + d.avgDurationSeconds, 0) / sorted.length
  const threshold = avg * 1.5

  const names = sorted.map(d => d.stationName).reverse()
  const values = sorted.map(d => +(d.avgDurationSeconds / 60).toFixed(2)).reverse()
  const counts = sorted.map(d => d.parkingCount).reverse()

  chart.setOption({
    grid: { left: 150, right: 80, top: 20, bottom: 40 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: params => {
        const p = params[0]
        const idx = names.length - 1 - p.dataIndex
        const isAbnormal = sorted[idx].avgDurationSeconds >= threshold
        return `${p.name}${isAbnormal ? ' ⚠️ 异常' : ''}<br/>平均停靠：${p.value} 分钟<br/>停靠记录：${counts[idx].toLocaleString()}`
      }
    },
    xAxis: { type: 'value', name: '平均停靠时长(分钟)' },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { fontSize: 12 }
    },
    series: [{
      type: 'bar',
      data: values.map((v, i) => {
        const origIdx = names.length - 1 - i
        const isAbnormal = sorted[origIdx].avgDurationSeconds >= threshold
        return {
          value: v,
          itemStyle: {
            color: isAbnormal
              ? new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: '#fca5a5' }, { offset: 1, color: '#dc2626' }
                ])
              : new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: '#6ee7b7' }, { offset: 1, color: '#059669' }
                ])
          }
        }
      }),
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
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.header h2 { font-size: 18px; color: #111827; }
.controls { font-size: 14px; color: #4b5563; }
.controls select { margin-left: 8px; padding: 4px 12px; border: 1px solid #d1d5db; border-radius: 4px; }
.legend { font-size: 13px; color: #4b5563; margin-bottom: 12px; display: flex; align-items: center; }
.dot { display: inline-block; width: 12px; height: 12px; border-radius: 2px; margin-right: 6px; }
.dot.abnormal { background: #dc2626; }
.dot.normal { background: #059669; }
.chart { flex: 1; min-height: 500px; }
.tip { text-align: center; padding: 40px; color: #6b7280; }
.error { color: #dc2626; }
</style>
