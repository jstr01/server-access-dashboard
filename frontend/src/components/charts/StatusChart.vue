<script setup>
import { computed } from 'vue'
import ChartCard from './ChartCard.vue'
import { statusColor, activeChrome } from '../../lib/viz/palette'

const props = defineProps({
  points: { type: Array, default: () => [] },
  title: { type: String, default: 'Status Codes' },
  subtitle: { type: String, default: '' },
  height: { type: Number, default: 400 },
})

// Total counts per status code, summed over every time bucket.
const countsByCode = computed(() => {
  const totals = new Map()
  for (const p of props.points) {
    if (p.status_code != null) {
      totals.set(p.status_code, (totals.get(p.status_code) || 0) + p.count)
    }
  }
  return totals
})

const statusCodes = computed(() =>
  [...countsByCode.value.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15)
    .map((d) => d[0]),
)

const chartData = computed(() => {
  const c = activeChrome.value
  return {
    labels: statusCodes.value.map((s) => String(s)),
    datasets: [
      {
        label: 'Count',
        data: statusCodes.value.map((s) => countsByCode.value.get(s) || 0),
        backgroundColor: statusCodes.value.map((s) => statusColor(s)),
        borderColor: c.surface,
        borderWidth: 2,
        borderRadius: 2,
        borderSkipped: false,
      },
    ],
  }
})

const chartOptions = computed(() => {
  const c = activeChrome.value
  return {
    // Single series - the title names it, so no legend box.
    plugins: { legend: { display: false } },
    scales: {
      x: {
        title: { display: true, color: c.secondary, text: 'HTTP Status Code' },
        ticks: { maxRotation: 0, minRotation: 0 },
        grid: { display: false },
      },
      y: {
        title: { display: true, color: c.secondary, text: 'Count' },
        ticks: { callback: (v) => formatCompact(v) },
      },
    },
  }
})

const tableColumns = computed(() => [
  { key: 'status_code', label: 'Status Code' },
  { key: 'count', label: 'Count' },
])

const tableRows = computed(() =>
  props.points
    .filter((p) => p.status_code != null)
    .sort((a, b) => b.count - a.count)
    .slice(0, 20)
    .map((p) => ({
      status_code: p.status_code,
      count: formatCompact(p.count),
    })),
)

function formatCompact(v) {
  try {
    return new Intl.NumberFormat('en-US', { notation: 'compact', compactDisplay: 'short' }).format(v)
  } catch {
    return v
  }
}
</script>

<template>
  <ChartCard
    :title="title"
    :subtitle="subtitle"
    chart-type="bar"
    :chart-data="chartData"
    :chart-options="chartOptions"
    :table-columns="tableColumns"
    :table-rows="tableRows"
    :show-table-toggle="true"
    :height="height"
  />
</template>