import type { SeriesResponse } from '../../api/client.ts'

export const DEFAULT_EXPLORER_START = '2026-01-10'
export const DEFAULT_EXPLORER_END = '2026-01-16'
export const DEFAULT_HORIZON_HOURS = 24

const MONTHS = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
] as const

const mwFormat = new Intl.NumberFormat('en-GB', {
  maximumFractionDigits: 1,
})

export type SeriesPoint = SeriesResponse['points'][number]

export type ChartRow = {
  label: string
  time: string
  actualMw: number | null
  forecastMw: number | null
  errorMw: number | null
}

export function coverageBounds(
  days: readonly string[],
): { min: string; max: string } | null {
  if (days.length === 0) {
    return null
  }
  const sorted = [...days].sort()
  const min = sorted[0]
  const max = sorted[sorted.length - 1]
  if (!min || !max) {
    return null
  }
  return { min, max }
}

export function clampDay(day: string, min: string, max: string): string {
  if (day < min) {
    return min
  }
  if (day > max) {
    return max
  }
  return day
}

export function initialRange(days: readonly string[]): {
  start: string
  end: string
} {
  const bounds = coverageBounds(days)
  if (!bounds) {
    return { start: DEFAULT_EXPLORER_START, end: DEFAULT_EXPLORER_END }
  }
  const start = clampDay(DEFAULT_EXPLORER_START, bounds.min, bounds.max)
  const end = clampDay(DEFAULT_EXPLORER_END, bounds.min, bounds.max)
  if (start > end) {
    return { start, end: start }
  }
  return { start, end }
}

export function errorMw(
  forecastMw: number | null,
  actualMw: number | null,
): number | null {
  if (forecastMw === null || actualMw === null) {
    return null
  }
  return forecastMw - actualMw
}

export function toChartRows(points: readonly SeriesPoint[]): ChartRow[] {
  return points.map((point) => ({
    label: londonLabel(point.start_time_london, false),
    time: londonLabel(point.start_time_london, true),
    actualMw: point.actual_mw,
    forecastMw: point.forecast_mw,
    errorMw: errorMw(point.forecast_mw, point.actual_mw),
  }))
}

export function missingCounts(points: readonly SeriesPoint[]): {
  forecast: number
  actual: number
} {
  return {
    forecast: points.filter((point) => point.missing_forecast).length,
    actual: points.filter((point) => point.missing_actual).length,
  }
}

export function horizonCaption(hours: number): string {
  return `Latest forecast published at least ${hours} hours before each half-hour.`
}

export function formatMw(value: number | null, signed = false): string {
  if (value === null) {
    return '—'
  }
  const text = mwFormat.format(value)
  if (signed && value > 0) {
    return `+${text} MW`
  }
  return `${text} MW`
}

export function isChartRow(value: unknown): value is ChartRow {
  if (!value || typeof value !== 'object') {
    return false
  }
  return (
    'time' in value &&
    'actualMw' in value &&
    'forecastMw' in value &&
    'errorMw' in value
  )
}

function londonLabel(startTimeLondon: string, withYear: boolean): string {
  const [date, time] = startTimeLondon.split('T')
  if (!date || !time) {
    return startTimeLondon
  }
  const [year, monthText, dayText] = date.split('-')
  const month = MONTHS[Number(monthText) - 1]
  const clock = time.slice(0, 5)
  if (!year || !month || !dayText || clock.length < 5) {
    return startTimeLondon
  }
  const day = `${Number(dayText)} ${month}`
  return withYear ? `${day} ${year} ${clock}` : `${day} ${clock}`
}
