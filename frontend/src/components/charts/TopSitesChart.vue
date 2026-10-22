<script setup>
import { computed } from 'vue'
import ChartCard from './ChartCard.vue'
import { seriesColor, activeChrome } from '../../lib/viz/palette'

const props = defineProps({
  points: { type: Array, default: () => [] },
  title: { type: String, default: 'Top Sites' },
  subtitle: { type: String, default: '' },
  height: { type: Number, default: 400 },
})

// Total accesses per domain, summed over every time bucket.
const totalsByDomain = computed(() => {
  const totals = new Map()
  for (const p of props.points) {
    const key = p.domain || '(no domain)'
    totals.set(key, (totals.get(key) || 0) + p.count)
  }
  return totals
})

// Top 10 domains by total accesses.
const topDomains = computed(() =>
  [...totalsByDomain.value.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map((d) => d[0]),
)

const datasets = computed(() => ({
  label: 'Accesses',
  data: topDomains.value.map((d) => totalsByDomain.value.get(d) || 0),
  backgroundColor: seriesColor(0),
}))

const chartData = computed(() => ({
  labels: topDomains.value,
  datasets: [datasets.value],
}))

const chartOptions = computed(() => {
  const c = activeChrome.value
  return {
    indexAxis: 'y',
    // Single series - the title names it, so no legend box.
    plugins: { legend: { display: false } },
    scales: {
      x: {
        title: { display: true, color: c.secondary, text: 'Accesses' },
        ticks: { callback: (v) => formatCompact(v) },
      },
      y: {
        grid: { display: false },
        ticks: { color: c.muted },
      },
    },
  }
})

const tableColumns = computed(() => [
  { key: 'domain', label: 'Site' },
  { key: 'count', label: 'Count' },
])

const tableRows = computed(() =>
  topDomains.value.map((d) => ({
    domain: d,
    count: formatCompact(totalsByDomain.value.get(d) || 0),
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