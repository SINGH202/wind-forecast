import type { MetaResponse } from '../api/client.ts'

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

export function formatCoverage(meta: MetaResponse): string {
  const first = meta.delivery_days[0]
  const last = meta.delivery_days[meta.delivery_days.length - 1]
  if (!first || !last) {
    return 'No delivery days in the snapshot'
  }
  const count = `${meta.delivery_day_count} delivery days`
  return `${formatDay(first)} – ${formatDay(last)} · ${count}`
}

export function formatCutoff(meta: MetaResponse): string {
  return `Default cutoff ${meta.default_cutoff} ${meta.timezone}`
}

function formatDay(isoDate: string): string {
  const [year, monthText, dayText] = isoDate.split('-')
  const monthIndex = Number(monthText) - 1
  const month = MONTHS[monthIndex]
  if (!year || !month || !dayText) {
    return isoDate
  }
  return `${Number(dayText)} ${month} ${year}`
}
