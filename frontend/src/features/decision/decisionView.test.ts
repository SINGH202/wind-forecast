import { expect, test } from 'vitest'

import {
  ageSpread,
  cutoffSentence,
  hasForecast,
  previousDay,
  toDecisionRows,
  type DecisionPoint,
} from './decisionView.ts'

const point = {
  start_time: '2026-01-15T00:00:00Z',
  start_time_london: '2026-01-15T00:00:00',
  forecast_mw: 100,
  actual_mw: 80,
  firm_mw: 70,
  band_low_mw: 70,
  band_high_mw: 120,
  publish_time: '2026-01-14T07:30:00Z',
  horizon_hours: 16.5,
  forecast_age_hours: 1.5,
  missing_forecast: false,
  missing_actual: false,
} satisfies DecisionPoint

test('the cutoff sentence uses the London timestamp from the API', () => {
  expect(previousDay('2026-01-15')).toBe('2026-01-14')
  expect(cutoffSentence('2026-01-14T09:00:00', 'Europe/London')).toBe(
    'Using forecasts published up to 09:00 Europe/London on 14 Jan 2026.',
  )
})

test('chart rows keep gaps null and pass the band through', () => {
  const rows = toDecisionRows([
    point,
    {
      ...point,
      start_time_london: '2026-01-15T00:30:00',
      forecast_mw: null,
      actual_mw: null,
      band_low_mw: null,
      band_high_mw: null,
      missing_forecast: true,
      forecast_age_hours: null,
    },
  ])
  expect(rows[0]).toMatchObject({
    label: '00:00',
    time: '15 Jan 2026 00:00',
    forecastMw: 100,
    actualMw: 80,
    band: [70, 120],
  })
  expect(rows[1]?.forecastMw).toBeNull()
  expect(rows[1]?.band).toBeNull()
  expect(hasForecast([point])).toBe(true)
  expect(hasForecast([{ ...point, forecast_mw: null }])).toBe(false)
})

test('age spread reads the median and oldest from the point ages', () => {
  const ages = [1, 2, 3, 4].map((age) => ({
    ...point,
    forecast_age_hours: age,
  }))
  expect(ageSpread(ages)).toEqual({ median: 2.5, oldest: 4 })
  expect(ageSpread([{ ...point, forecast_age_hours: null }])).toEqual({
    median: null,
    oldest: null,
  })
})
