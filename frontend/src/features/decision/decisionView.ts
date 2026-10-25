import type { DecisionResponse } from '../../api/client.ts'

export const DEFAULT_DELIVERY_DAY = '2026-01-15'
export const DEFAULT_CUTOFF = '09:00'

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

const numberFormat = new Intl.NumberFormat('en-GB', {
  maximumFractionDigits: 1,
})

export type DecisionPoint = DecisionResponse['points'][number]

export type DecisionChartRow = {
  label: string
  time: string
  forecastMw: number | null
  actualMw: number | null
  band: [number, number] | null
  publishTime: string | null
}

export type AgeSpread = {
  median: number | null
  oldest: number | null
}

export function initialDeliveryDay(days: readonly string[]): string {
  if (days.includes(DEFAULT_DELIVERY_DAY)) {
    return DEFAULT_DELIVERY_DAY
  }
  return days[0] ?? DEFAULT_DELIVERY_DAY
}

export function initialCutoff(
  defaultCutoff: string,
  options: readonly string[],
): string {
  if (options.includes(defaultCutoff)) {
    return defaultCutoff
  }
  if (options.includes(DEFAULT_CUTOFF)) {
    return DEFAULT_CUTOFF
  }
  return options[0] ?? DEFAULT_CUTOFF
}

export function previousDay(isoDate: string): string {
  const [yearText, monthText, dayText] = isoDate.split('-')
  const year = Number(yearText)
  const month = Number(monthText)
  const day = Number(dayText)
  if (!year || !month || !day) {
    return isoDate
  }
  const date = new Date(Date.UTC(year, month - 1, day))
  date.setUTCDate(date.getUTCDate() - 1)
  return date.toISOString().slice(0, 10)
}

export function cutoffSentence(
  cutoffLocal: string | null,
  timezone: string,
): string {
  if (!cutoffLocal) {
    return 'The cutoff time is unavailable.'
  }
  const [date, time] = cutoffLocal.split('T')
  if (!date || !time) {
    return 'The cutoff time is unavailable.'
  }
  return `Using forecasts published up to ${time.slice(0, 5)} ${timezone} on ${formatDay(date)}.`
}

export function toDecisionRows(
  points: readonly DecisionPoint[],
): DecisionChartRow[] {
  return points.map((point) => ({
    label: londonClock(point.start_time_london),
    time: londonTime(point.start_time_london),
    forecastMw: point.forecast_mw,
    actualMw: point.actual_mw,
    band: bandRange(point.band_low_mw, point.band_high_mw),
    publishTime: point.publish_time,
  }))
}

export function hasForecast(points: readonly DecisionPoint[]): boolean {
  return points.some((point) => point.forecast_mw !== null)
}

export function deliveryComplete(points: readonly DecisionPoint[]): boolean {
  return points.some((point) => point.actual_mw !== null)
}

export function missingCounts(points: readonly DecisionPoint[]): {
  forecast: number
  actual: number
} {
  return {
    forecast: points.filter((point) => point.missing_forecast).length,
    actual: points.filter((point) => point.missing_actual).length,
  }
}

/** Median and oldest age from the ages already attached to each half-hour. */
export function ageSpread(points: readonly DecisionPoint[]): AgeSpread {
  const ages = points
    .map((point) => point.forecast_age_hours)
    .filter((age): age is number => age !== null)
    .sort((left, right) => left - right)
  if (ages.length === 0) {
    return { median: null, oldest: null }
  }
  const mid = Math.floor(ages.length / 2)
  const lower = ages[mid - 1]
  const upper = ages[mid]
  const median =
    ages.length % 2 === 1 || lower === undefined || upper === undefined
      ? (upper ?? null)
      : (lower + upper) / 2
  return { median, oldest: ages[ages.length - 1] ?? null }
}

export function formatNumber(value: number | null): string {
  if (value === null) {
    return '—'
  }
  return numberFormat.format(value)
}

export function isDecisionRow(value: unknown): value is DecisionChartRow {
  if (!value || typeof value !== 'object') {
    return false
  }
  return 'time' in value && 'forecastMw' in value && 'actualMw' in value
}

function bandRange(
  low: number | null,
  high: number | null,
): [number, number] | null {
  if (low === null || high === null) {
    return null
  }
  return [low, high]
}

function londonClock(startTimeLondon: string): string {
  const time = startTimeLondon.split('T')[1]
  return time ? time.slice(0, 5) : startTimeLondon
}

function londonTime(startTimeLondon: string): string {
  const [date, time] = startTimeLondon.split('T')
  if (!date || !time) {
    return startTimeLondon
  }
  return `${formatDay(date)} ${time.slice(0, 5)}`
}

function formatDay(isoDate: string): string {
  const [year, monthText, dayText] = isoDate.split('-')
  const month = MONTHS[Number(monthText) - 1]
  if (!year || !month || !dayText) {
    return isoDate
  }
  return `${Number(dayText)} ${month} ${year}`
}
