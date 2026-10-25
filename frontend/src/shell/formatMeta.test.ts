import { expect, test } from 'vitest'

import type { MetaResponse } from '../api/client.ts'
import { formatCoverage, formatCutoff } from './formatMeta.ts'

const meta = {
  delivery_days: ['2026-01-01', '2026-01-31'],
  delivery_day_count: 31,
  min_start_time: '2026-01-01T00:00:00Z',
  max_start_time: '2026-01-31T23:30:00Z',
  default_cutoff: '09:00',
  cutoff_options: ['09:00'],
  timezone: 'Europe/London',
  power_unit: 'MW',
  energy_unit: 'MWh',
  resolution_minutes: 30,
  manifest: null,
  assumptions: [],
} satisfies MetaResponse

test('coverage and cutoff use the snapshot dates and the default clock', () => {
  expect(formatCoverage(meta)).toBe(
    '1 Jan 2026 – 31 Jan 2026 · 31 delivery days',
  )
  expect(formatCutoff(meta)).toBe('Default cutoff 09:00 Europe/London')
  expect(formatCoverage({ ...meta, delivery_days: [] })).toBe(
    'No delivery days in the snapshot',
  )
})
