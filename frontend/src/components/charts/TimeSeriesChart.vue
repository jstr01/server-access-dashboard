<script setup>
import { computed } from 'vue'
import ChartCard from './ChartCard.vue'
import { seriesColor, activeChrome } from '../../lib/viz/palette'

const props = defineProps({
  points: { type: Array, default: () => [] },
  title: { type: String, default: 'Accesses over time' },
  subtitle: { type: String, default: '' },
  height: { type: Number, default: 320 },
})

// Buckets in chronological order (the API returns them sorted).
const labels = computed(() => {
  const seen = new Set()
  const out = []
  for (const p of props.points) {
    if (!seen.has(p.bucket)) {
      seen.add(p.bucket)
      out.push(p.bucket)
    }
  }
  return out
})

// Total accesses per domain; keep the top 6 so the legend stays readable
// (the dataviz method caps categorical series past three for all-pairs safety,
// and six is the practical ceiling for a multi-line chart on this surface).
const domainTotals = computed(() => {
  const totals = new Map()
  for (const p of props.points) {
    totals.set(p.domain, (totals.get(p.domain) || 0) + p.count)
  }
  return [...totals.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map((d) => d[0])
})

const datasets = computed(() => {
  const buckets = labels.value
  return domainTotals.value.map((domain, i) => {
    const byBucket = new Map()
    for (const p of props.points) {
      if (p.domain === domain) byBucket.set(p.bucket, p.count)
    }
    const color = seriesColor(i)
    return {
      label: domain,
      data: buckets.map((b) => byBucket.get(b) || 0),
      borderColor: color,
      backgroundColor: color,
      borderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
      pointHoverBackgroundColor: color,
      tension: 0,
      fill: false,
    }
  })
})

const chartData = computed(() => ({
  labels: labels.value,
  datasets: datasets.value,
}))

const chartOptions = computed(() => {
  const c = activeChrome.value
  return {
    scales: {
      x: {
        title: { display: true, color: c.secondary, text: 'Time' },
      },
      y: {
        title: { display: true, color: c.secondary, text: 'Accesses' },
        ticks: {
          callback: (v) => formatCompact(v),
        },
      },
    },
  }
})

const tableColumns = computed(() => [
  { key: 'bucket', label: 'Time' },
  ...domainTotals.value.map((d) => ({ key: d, label: d })),
  { key: 'total', label: 'Total' },
])

const tableRows = computed(() => {
  const buckets = labels.value
  return buckets.map((b) => {
    const row = { bucket: b }
    let total = 0
    for (const d of domainTotals.value) {
      const count = props.points.find((p) => p.bucket === b && p.domain === d)?.count || 0
      row[d] = formatCompact(count)
      total += count
    }
    row.total = formatCompact(total)
    return row
  })
})

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
    chart-type="line"
    :chart-data="chartData"
    :chart-options="chartOptions"
    :table-columns="tableColumns"
    :table-rows="tableRows"
    :show-table-toggle="true"
    :height="height"
  />
</template>