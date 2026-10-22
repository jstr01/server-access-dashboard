/**
 * Chart color palette tokens for the dashboard.
 *
 * Values are the validated reference categorical palette (see
 * dataviz/references/palette.md) plus a sequential blue ramp and semantic
 * status colors. The light and dark palettes swap in one place, and the chart
 * components read them through the reactive `vizTheme` so a theme switch
 * repaints the canvases.
 *
 * The palette was validated with validate_palette.js against the app's
 * actual surfaces:
 *   light  #fafafa (page bg) / #ffffff (card bg)
 *   dark   #1f2937 (card bg, dark:bg-gray-800)
 *
 * Categorical slots 3-5 (aqua/yellow/magenta) sit below 3:1 contrast on the
 * light surface and slot 6 (green) below 3:1 on the dark surface. The relief
 * rule applies: legends + table views carry identity, and direct labels are
 * selective - never color-only encoding.
 */
import { reactive, computed } from 'vue'

// Categorical palette, light mode.
export const CATEGORICAL_LIGHT = [
  '#2a78d6', // 1 blue
  '#eb6834', // 2 orange
  '#1baf7a', // 3 aqua
  '#eda100', // 4 yellow
  '#e87ba4', // 5 magenta
  '#008300', // 6 green
  '#4a3aa7', // 7 violet
  '#e34948', // 8 red
]

// Categorical palette, dark mode - the same eight hues, stepped for the
// darker surface (see palette.md).
export const CATEGORICAL_DARK = [
  '#3987e5',
  '#d95926',
  '#199e70',
  '#c98500',
  '#d55181',
  '#008300',
  '#9085e9',
  '#e66767',
]

// Sequential blue ramp, light mode: low values are light, high values dark.
// Steps are spaced so the light end clears the surface (start at step 250).
export const SEQUENTIAL_LIGHT = [
  '#86b6ef',
  '#3987e5',
  '#2a78d6',
  '#1c5cab',
]

// Sequential blue ramp, dark mode: low values recede toward the dark surface,
// high values are bright. Steps are spaced so the dark end clears the surface.
export const SEQUENTIAL_DARK = [
  '#cde2fb',
  '#86b6ef',
  '#3987e5',
  '#1c5cab',
]

// Semantic status colors - reserved for status, never reused for a series.
// Good / warning / serious / critical (see palette.md). Fixed, never themed.
export const STATUS_COLORS = {
  good: '#0ca30c',
  warning: '#fab219',
  serious: '#ec835a',
  critical: '#d03b3b',
}

// Chart chrome (text, grid, axis, surface) - these are text tokens, never
// series colors, so labels/legends/axis text stay in primary/secondary ink.
export const CHROME_LIGHT = {
  surface: '#ffffff',
  text: '#0b0b0b',
  secondary: '#52514e',
  muted: '#898781',
  grid: '#e1e0d9',
  axis: '#c3c2b7',
  border: 'rgba(11,11,11,0.10)',
}

export const CHROME_DARK = {
  surface: '#1f2937',
  text: '#ffffff',
  secondary: '#c3c2b7',
  muted: '#898781',
  grid: '#2c2c2a',
  axis: '#383835',
  border: 'rgba(255,255,255,0.10)',
}

// --- Reactive theme state ---
//
// Canvas cannot resolve CSS custom properties in fillStyle/strokeStyle, so the
// chart components need concrete hex values. This reactive store is the single
// source of truth for which palette is active; `applyPalette` updates it and
// mirrors the values onto :root for the CSS-driven parts (table views, gaps).

export const vizTheme = reactive({
  dark: false,
})

export const activeCategorical = computed(() =>
  vizTheme.dark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT,
)

export const activeSequential = computed(() => (vizTheme.dark ? SEQUENTIAL_DARK : SEQUENTIAL_LIGHT))

export const activeChrome = computed(() => (vizTheme.dark ? CHROME_DARK : CHROME_LIGHT))

// Categorical color for series slot `index` (0-based). Hues are assigned in
// fixed order, never cycled - a 9th series folds into "Other" instead.
export function seriesColor(index) {
  const palette = activeCategorical.value
  if (index >= palette.length) return palette[palette.length - 1]
  return palette[index]
}

// Map an HTTP status code to a semantic status color.
export function statusColor(statusCode) {
  if (statusCode == null) return '#6c757d'
  if (statusCode >= 200 && statusCode < 300) return STATUS_COLORS.good
  if (statusCode >= 300 && statusCode < 400) return STATUS_COLORS.warning
  if (statusCode >= 400 && statusCode < 500) return STATUS_COLORS.critical
  return STATUS_COLORS.critical
}

// Apply the palette to the document as CSS custom properties and record the
// active mode for the canvas-backed charts.
export function applyPalette(dark) {
  vizTheme.dark = !!dark
  const root = document.documentElement
  const cat = dark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT
  const seq = dark ? SEQUENTIAL_DARK : SEQUENTIAL_LIGHT
  const chrome = dark ? CHROME_DARK : CHROME_LIGHT

  cat.forEach((c, i) => root.style.setProperty(`--series-${i + 1}`, c))
  seq.forEach((c, i) => root.style.setProperty(`--seq-${i + 1}`, c))
  Object.entries(chrome).forEach(([k, v]) => {
    root.style.setProperty(`--viz-${k}`, v)
  })
}
