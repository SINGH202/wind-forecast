import { expect, test } from 'vitest'

import { formatPercent } from '../../design/format.ts'
import {
  histogramCaption,
  horizonAccuracyCaption,
  horizonRows,
  hourCaption,
  levelCaption,
  quantileLabel,
  sortWorstDays,
  worstDayCaption,
  type BucketMetric,
  type HistogramBin,
  type WorstDay,
} from './accuracyView.ts'

const bucket = (name: string, mae: number | null, n = 10): BucketMetric => ({
  bucket: name,
  n,
  mae_mw: mae,
  bias_mw: mae,
})

test('horizon caption compares the shortest and longest ahead buckets', () => {
  expect(
    horizonAccuracyCaption([
      bucket('<0', 50),
      bucket('[0,6)', 100),
      bucket('[24,48)', 141),
      bucket('[36,48)', null, 0),
    ]),
  ).toBe(
    'Forecasts made 24–48 h ahead are 41% less accurate than those made 0–6 h ahead.',
  )
  expect(horizonRows([bucket('[0,6)', null, 0)])[0]?.maeMw).toBeNull()
})

test('hour and wind captions name the highest and lowest MAE', () => {
  expect(
    hourCaption([
      { hour: 5, n: 4, mae_mw: 20, bias_mw: 1 },
      { hour: 21, n: 4, mae_mw: 10, bias_mw: 1 },
      { hour: 0, n: 0, mae_mw: null, bias_mw: null },
    ]),
  ).toBe(
    'London 05:00 has the highest MAE, 20 MW. 21:00 is the lowest, at 10 MW.',
  )
  expect(
    levelCaption([
      bucket('[0,5000)', 30),
      bucket('[5000,10000)', 10),
      bucket('<0', null, 0),
    ]),
  ).toBe(
    'Actual wind 0–5,000 MW has the highest MAE, 30 MW. The 5,000–10,000 MW band is the lowest, at 10 MW.',
  )
})

test('histogram caption quotes P10, P90 and the fullest bin', () => {
  const bins: HistogramBin[] = [
    { edge_low_mw: -500, edge_high_mw: 0, count: 4 },
    { edge_low_mw: 0, edge_high_mw: 500, count: 12 },
  ]
  expect(histogramCaption(-400, 900, bins)).toBe(
    'P10 is -400 MW and P90 is +900 MW. The fullest bin holds 12 half-hours, from 0 to 500 MW.',
  )
  expect(quantileLabel(bins, -400)).toBe('-500')
  expect(quantileLabel(bins, 500)).toBe('0')
  expect(formatPercent(0.1837)).toBe('18.4')
})

test('worst days sort by the chosen column without changing values', () => {
  const rows: WorstDay[] = [
    { delivery_day: '2026-01-28', n: 24, mae_mw: 50, bias_mw: 40 },
    { delivery_day: '2026-01-02', n: 20, mae_mw: 10, bias_mw: -5 },
  ]
  expect(sortWorstDays(rows, 'delivery_day', 'asc')[0]?.delivery_day).toBe(
    '2026-01-02',
  )
  expect(sortWorstDays(rows, 'bias_mw', 'asc')[0]?.bias_mw).toBe(-5)
  expect(worstDayCaption(rows)).toBe(
    '2026-01-28 has the highest MAE, 50 MW, with bias +40 MW.',
  )
})
