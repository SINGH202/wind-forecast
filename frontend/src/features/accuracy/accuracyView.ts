import type { MetricsResponse } from '../../api/client.ts'
import { formatMw } from '../../design/format.ts'

export const DEFAULT_ACCURACY_START = '2026-01-01'
export const DEFAULT_ACCURACY_END = '2026-01-31'
export const DEFAULT_CUTOFF = '09:00'

export type BucketMetric = MetricsResponse['by_wind_level'][number]
export type HourMetric = MetricsResponse['by_hour_london'][number]
export type HistogramBin = MetricsResponse['histogram'][number]
export type WorstDay = MetricsResponse['worst_days'][number]

export type BarRow = {
  label: string
  maeMw: number | null
  biasMw: number | null
}

export type HistRow = {
  label: string
  range: string
  count: number
}

export type WorstSortKey = 'delivery_day' | 'mae_mw' | 'bias_mw' | 'n'

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

export function fullCoverageRange(days: readonly string[]): {
  start: string
  end: string
} {
  const bounds = coverageBounds(days)
  if (!bounds) {
    return { start: DEFAULT_ACCURACY_START, end: DEFAULT_ACCURACY_END }
  }
  return { start: bounds.min, end: bounds.max }
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

export function horizonRows(buckets: readonly BucketMetric[]): BarRow[] {
  return buckets.map((bucket) => ({
    label: horizonPhrase(bucket.bucket),
    maeMw: bucket.mae_mw,
    biasMw: bucket.bias_mw,
  }))
}

export function hourRows(hours: readonly HourMetric[]): BarRow[] {
  return hours.map((hour) => ({
    label: clockLabel(hour.hour),
    maeMw: hour.mae_mw,
    biasMw: hour.bias_mw,
  }))
}

export function levelRows(buckets: readonly BucketMetric[]): BarRow[] {
  return buckets.map((bucket) => ({
    label: windPhrase(bucket.bucket),
    maeMw: bucket.mae_mw,
    biasMw: bucket.bias_mw,
  }))
}

export function histogramRows(bins: readonly HistogramBin[]): HistRow[] {
  return bins.map((bin) => ({
    label: formatMw(bin.edge_low_mw),
    range: `${formatMw(bin.edge_low_mw)} to ${formatMw(bin.edge_high_mw)} MW`,
    count: bin.count,
  }))
}

export function quantileLabel(
  bins: readonly HistogramBin[],
  value: number | null,
): string | null {
  if (value === null) {
    return null
  }
  const bin = binContaining(bins, value)
  return bin ? formatMw(bin.edge_low_mw) : null
}

export function horizonAccuracyCaption(
  buckets: readonly BucketMetric[],
): string {
  const comparable = comparableBuckets(buckets)
  const first = comparable[0]
  const last = comparable[comparable.length - 1]
  if (!first || !last || first.mae_mw === null || last.mae_mw === null) {
    return 'No horizon bucket has pairs to compare.'
  }
  if (first.bucket === last.bucket) {
    return `MAE for forecasts ${horizonPhrase(first.bucket)} is ${formatMw(first.mae_mw)} MW.`
  }
  if (first.mae_mw === 0) {
    return `MAE is ${formatMw(first.mae_mw)} MW ${horizonPhrase(first.bucket)} and ${formatMw(last.mae_mw)} MW ${horizonPhrase(last.bucket)}.`
  }
  const pct = Math.round(
    (Math.abs(last.mae_mw - first.mae_mw) / Math.abs(first.mae_mw)) * 100,
  )
  if (pct === 0) {
    return `MAE is about ${formatMw(first.mae_mw)} MW both ${horizonPhrase(first.bucket)} and ${horizonPhrase(last.bucket)}.`
  }
  const direction =
    last.mae_mw > first.mae_mw ? 'less accurate' : 'more accurate'
  return `Forecasts made ${horizonPhrase(last.bucket)} are ${pct}% ${direction} than those made ${horizonPhrase(first.bucket)}.`
}

export function hourCaption(hours: readonly HourMetric[]): string {
  const usable = hours.filter(
    (hour): hour is HourMetric & { mae_mw: number } =>
      hour.n > 0 && hour.mae_mw !== null,
  )
  const highest = extreme(usable, 'max')
  const lowest = extreme(usable, 'min')
  if (!highest || !lowest) {
    return 'No London hour has decision-forecast pairs.'
  }
  if (highest.hour === lowest.hour) {
    return `London ${clockLabel(highest.hour)} has MAE ${formatMw(highest.mae_mw)} MW.`
  }
  return `London ${clockLabel(highest.hour)} has the highest MAE, ${formatMw(highest.mae_mw)} MW. ${clockLabel(lowest.hour)} is the lowest, at ${formatMw(lowest.mae_mw)} MW.`
}

export function levelCaption(buckets: readonly BucketMetric[]): string {
  const usable = buckets.filter(
    (bucket): bucket is BucketMetric & { mae_mw: number } =>
      bucket.n > 0 && bucket.mae_mw !== null,
  )
  const highest = extreme(usable, 'max')
  const lowest = extreme(usable, 'min')
  if (!highest || !lowest) {
    return 'No wind-level band has decision-forecast pairs.'
  }
  if (highest.bucket === lowest.bucket) {
    return `Actual wind ${windPhrase(highest.bucket)} has MAE ${formatMw(highest.mae_mw)} MW.`
  }
  return `Actual wind ${windPhrase(highest.bucket)} has the highest MAE, ${formatMw(highest.mae_mw)} MW. The ${windPhrase(lowest.bucket)} band is the lowest, at ${formatMw(lowest.mae_mw)} MW.`
}

export function histogramCaption(
  p10: number | null,
  p90: number | null,
  bins: readonly HistogramBin[],
): string {
  if (p10 === null || p90 === null) {
    return 'There are no decision-forecast errors to mark.'
  }
  const marks = `P10 is ${formatMw(p10, true)} MW and P90 is ${formatMw(p90, true)} MW.`
  const fullest = bins.reduce<HistogramBin | null>((best, bin) => {
    if (!best || bin.count > best.count) {
      return bin
    }
    return best
  }, null)
  if (!fullest) {
    return marks
  }
  return `${marks} The fullest bin holds ${fullest.count} half-hours, from ${formatMw(fullest.edge_low_mw)} to ${formatMw(fullest.edge_high_mw)} MW.`
}

export function worstDayCaption(rows: readonly WorstDay[]): string {
  const worst = rows.reduce<WorstDay | null>((best, row) => {
    if (!best || row.mae_mw > best.mae_mw) {
      return row
    }
    return best
  }, null)
  if (!worst) {
    return 'No delivery day has decision-forecast pairs.'
  }
  return `${worst.delivery_day} has the highest MAE, ${formatMw(worst.mae_mw)} MW, with bias ${formatMw(worst.bias_mw, true)} MW.`
}

export function sortWorstDays(
  rows: readonly WorstDay[],
  key: WorstSortKey,
  direction: 'asc' | 'desc',
): WorstDay[] {
  const sorted = [...rows]
  sorted.sort((left, right) => {
    const leftValue = left[key]
    const rightValue = right[key]
    const order = leftValue < rightValue ? -1 : leftValue > rightValue ? 1 : 0
    return direction === 'asc' ? order : -order
  })
  return sorted
}

export function hasMae(
  rows: readonly { n: number; mae_mw: number | null }[],
): boolean {
  return rows.some((row) => row.n > 0 && row.mae_mw !== null)
}

function comparableBuckets(buckets: readonly BucketMetric[]): BucketMetric[] {
  const usable = buckets.filter(
    (bucket): bucket is BucketMetric & { mae_mw: number } =>
      bucket.n > 0 && bucket.mae_mw !== null,
  )
  const ahead = usable.filter((bucket) => !bucket.bucket.startsWith('<'))
  return ahead.length >= 2 ? ahead : usable
}

function binContaining(
  bins: readonly HistogramBin[],
  value: number,
): HistogramBin | null {
  for (let index = 0; index < bins.length; index += 1) {
    const bin = bins[index]
    if (!bin) {
      continue
    }
    const last = index === bins.length - 1
    const belowHigh = last
      ? value <= bin.edge_high_mw
      : value < bin.edge_high_mw
    if (value >= bin.edge_low_mw && belowHigh) {
      return bin
    }
  }
  return null
}

function extreme<T extends { mae_mw: number }>(
  rows: readonly T[],
  which: 'min' | 'max',
): T | null {
  return rows.reduce<T | null>((best, row) => {
    if (!best) {
      return row
    }
    if (which === 'max') {
      return row.mae_mw > best.mae_mw ? row : best
    }
    return row.mae_mw < best.mae_mw ? row : best
  }, null)
}

function horizonPhrase(bucket: string): string {
  const range = bucket.match(/^\[([^,]+),([^)]+)\)$/)
  if (range?.[1] && range[2]) {
    return `${trimNumber(range[1])}–${trimNumber(range[2])} h ahead`
  }
  if (bucket.startsWith('>=')) {
    return `${trimNumber(bucket.slice(2))} h ahead and later`
  }
  if (bucket.startsWith('<')) {
    return `under ${trimNumber(bucket.slice(1))} h`
  }
  return bucket
}

function windPhrase(bucket: string): string {
  const range = bucket.match(/^\[([^,]+),([^)]+)\)$/)
  if (range?.[1] && range[2]) {
    return `${trimNumber(range[1])}–${trimNumber(range[2])} MW`
  }
  if (bucket.startsWith('>=')) {
    return `${trimNumber(bucket.slice(2))} MW and above`
  }
  if (bucket.startsWith('<')) {
    return `under ${trimNumber(bucket.slice(1))} MW`
  }
  return bucket
}

function trimNumber(raw: string): string {
  return formatMw(Number(raw))
}

function clockLabel(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`
}
