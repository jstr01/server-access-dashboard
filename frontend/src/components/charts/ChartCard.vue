<script setup>
import { computed, ref } from 'vue'
import { Chart } from 'vue-chartjs'
import { activeChrome, vizTheme } from '../../lib/viz/palette'

const props = defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  chartType: { type: String, default: 'line' },
  chartData: { type: Object, default: () => ({ labels: [], datasets: [] }) },
  chartOptions: { type: Object, default: () => ({}) },
  tableColumns: { type: Array, default: () => [] },
  tableRows: { type: Array, default: () => [] },
  showTableToggle: { type: Boolean, default: true },
  height: { type: Number, default: 320 },
})

const showTable = ref(false)

// Use the reactive theme store so a toggle triggers a re-render.
const chrome = computed(() => activeChrome.value)

// Merge helper: plain objects merge key by key, everything else is replaced.
// Lets a chart override a single scale/plugin property without dropping the
// shared chrome (grid, tick colors, tooltip) set here.
function mergeDeep(base, override) {
  if (!override || typeof override !== 'object' || Array.isArray(override)) {
    return override === undefined ? base : override
  }
  const out = { ...base }
  for (const [key, value] of Object.entries(override)) {
    out[key] = mergeDeep(base?.[key], value)
  }
  return out
}

const chartOptions = computed(() => {
  const overrides = props.chartOptions || {}
  const base = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: chrome.value.text,
          boxWidth: 8,
          boxHeight: 8,
          usePointStyle: true,
          pointStyle: 'circle',
          padding: 16,
        },
      },
      tooltip: {
        enabled: true,
        backgroundColor: chrome.value.text,
        titleColor: chrome.value.surface,
        bodyColor: chrome.value.surface,
        borderColor: chrome.value.border,
        borderWidth: 1,
        padding: 10,
        displayColors: true,
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: chrome.value.muted } },
      y: {
        beginAtZero: true,
        grid: { color: chrome.value.grid, display: true },
        ticks: { color: chrome.value.muted },
      },
    },
  }
  const merged = mergeDeep(base, overrides)
  // Scales and plugins are merged per-axis/per-plugin so a chart can set
  // e.g. `scales.y.stacked` without dropping the x-axis grid settings.
  return merged
})

const chartHeight = computed(() => props.height)
const chartKey = computed(() => JSON.stringify({ data: props.chartData, dark: vizTheme.dark }))
</script>

<template>
  <div class="chart-card">
    <div class="chart-header">
      <div>
        <h3 class="chart-title">{{ title }}</h3>
        <p v-if="subtitle" class="chart-subtitle">{{ subtitle }}</p>
      </div>
      <button
        v-if="showTableToggle && tableRows.length > 0"
        type="button"
        class="chart-table-toggle"
        @click="showTable = !showTable"
      >
        {{ showTable ? 'Hide data table' : 'Show data table' }}
      </button>
    </div>
    <div class="chart-box" :style="{ height: chartHeight }">
      <Chart :key="chartKey" :type="chartType" :data="chartData" :options="chartOptions" />
    </div>
    <div v-if="showTable && tableRows.length > 0" class="chart-table-wrap">
      <table class="chart-table">
        <thead>
          <tr>
            <th v-for="col in tableColumns" :key="col.key" class="chart-table-th">
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in tableRows" :key="i">
            <td v-for="col in tableColumns" :key="col.key" class="chart-table-td">
              {{ row[col.key] }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.chart-card {
  background-color: var(--viz-surface, #ffffff);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 0.5rem;
  padding: 1rem;
}
.dark .chart-card {
  background-color: #1f2937;
  border-color: rgba(255, 255, 255, 0.05);
}
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.chart-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--viz-text, #0b0b0b);
}
.chart-subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.75rem;
  color: var(--viz-secondary, #52514e);
}
.chart-table-toggle {
  flex-shrink: 0;
  border: none;
  background: none;
  color: #2563eb;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
}
.chart-box {
  position: relative;
  width: 100%;
}
.chart-box :deep(canvas) {
  width: 100% !important;
}
.chart-table-wrap {
  margin-top: 0.75rem;
  overflow-x: auto;
}
.chart-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}
.chart-table-th,
.chart-table-td {
  padding: 0.25rem 0.5rem;
  text-align: left;
  border-bottom: 1px solid rgba(128, 128, 128, 0.2);
  color: var(--viz-text, #0b0b0b);
  white-space: nowrap;
}
</style>
