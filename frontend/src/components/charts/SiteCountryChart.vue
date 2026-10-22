<script setup>
import { computed } from 'vue'
import ChartCard from './ChartCard.vue'
import { seriesColor, activeChrome } from '../../lib/viz/palette'

const props = defineProps({
  pairs: { type: Array, default: () => [] },
  title: { type: String, default: 'Accesses by site and country' },
  subtitle: { type: String, default: '' },
  height: { type: Number, default: 360 },
})

// Top sites by total accesses (the rows of the matrix).
const topDomains = computed(() => {
  const totals = new Map()
  for (const p of props.pairs) {
    totals.set(p.domain, (totals.get(p.domain) || 0) + p.count)
  }
  return [...totals.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map((d) => d[0])
})

// Top countries by total accesses across the selected sites (the columns).
const topCountries = computed(() => {
  const totals = new Map()
  for (const p of props.pairs) {
    if (!topDomains.value.includes(p.domain)) continue
    const key = p.country || 'Unknown'
    totals.set(key, (totals.get(key) || 0) + p.count)
  }
  return [...totals.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map((c) => c[0])
})

const datasets = computed(() =>
  topCountries.value.map((country, i) => {
    const byDomain = new Map()
    for (const p of props.pairs) {
      const key = p.country || 'Unknown'
      if (key === country) byDomain.set(p.domain, p.count)
    }
    return {
      label: country,
      data: topDomains.value.map((d) => byDomain.get(d) || 0),
      backgroundColor: seriesColor(i),
      // 2px surface gap between stacked segments.
      borderColor: activeChrome.value.surface,
      borderWidth: 2,
      borderRadius: 2,
      borderSkipped: false,
    }
  }),
)

const chartData = computed(() => ({
  labels: topDomains.value,
  datasets: datasets.value,
}))

const chartOptions = computed(() => {
  const c = activeChrome.value
  return {
    indexAxis: 'y',
    scales: {
      x: {
        stacked: true,
        title: { display: true, color: c.secondary, text: 'Accesses' },
        ticks: { callback: (v) => formatCompact(v) },
      },
      y: {
        stacked: true,
        grid: { display: false },
        ticks: { color: c.muted },
      },
    },
  }
})

const tableColumns = computed(() => [
  { key: 'domain', label: 'Site' },
  ...topCountries.value.map((c) => ({ key: c, label: c })),
  { key: 'total', label: 'Total' },
])

const tableRows = computed(() =>
  topDomains.value.map((d) => {
    const row = { domain: d }
    let total = 0
    for (const c of topCountries.value) {
      const count =
        props.pairs.find((p) => p.domain === d && (p.country || 'Unknown') === c)?.count || 0
      row[c] = formatCompact(count)
      total += count
    }
    row.total = formatCompact(total)
    return row
  }),
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