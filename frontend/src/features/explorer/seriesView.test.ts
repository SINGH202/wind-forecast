import { expect, test } from 'vitest'

import {
  errorMw,
  horizonCaption,
  initialRange,
  toChartRows,
  type SeriesPoint,
} from './seriesView.ts'

const point = {
  start_time: '2026-01-10T00:00:00Z',
  start_time_london: '2026-01-10T00:00:00',
  publish_time: '2026-01-09T00:00:00Z',
  horizon_hours: 24,
  missing_forecast: false,
  missing_actual: false,
} satisfies Omit<SeriesPoint, 'forecast_mw' | 'actual_mw'>

test('chart rows keep gaps as null and define error as forecast minus actual', () => {
  const rows = toChartRows([
    { ...point, forecast_mw: 100, actual_mw: 80 },
    {
      ...point,
      start_time_london: '2026-01-10T00:30:00',
      forecast_mw: null,
      actual_mw: 0,
      missing_forecast: true,
    },
    {
      ...point,
      start_time_london: '2026-01-10T01:00:00',
      forecast_mw: 50,
      actual_mw: null,
      missing_actual: true,
    },
  ])

  expect(rows[0]).toMatchObject({
    label: '10 Jan 00:00',
    time: '10 Jan 2026 00:00',
    actualMw: 80,
    forecastMw: 100,
    errorMw: 20,
  })
  expect(rows[1]?.forecastMw).toBeNull()
  expect(rows[1]?.actualMw).toBe(0)
  expect(rows[1]?.errorMw).toBeNull()
  expect(rows[2]?.errorMw).toBeNull()
  expect(errorMw(10, 12)).toBe(-2)
})

test('the default range stays inside the snapshot coverage', () => {
  expect(initialRange(['2026-01-02', '2026-02-01'])).toEqual({
    start: '2026-01-10',
    end: '2026-01-16',
  })
  expect(initialRange(['2026-01-20', '2026-01-25'])).toEqual({
    start: '2026-01-20',
    end: '2026-01-20',
  })
  expect(initialRange([])).toEqual({
    start: '2026-01-10',
    end: '2026-01-16',
  })
  expect(horizonCaption(24)).toBe(
    'Latest forecast published at least 24 hours before each half-hour.',
  )
})
