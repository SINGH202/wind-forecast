import { afterEach, expect, test, vi } from 'vitest'

import {
  getDecision,
  getHealth,
  getMeta,
  getMetrics,
  getSeries,
} from './client.ts'

afterEach(() => {
  vi.unstubAllGlobals()
})

test('each endpoint is requested on the relative /api path', async () => {
  const fetchMock = vi.fn(async () => jsonResponse())
  vi.stubGlobal('fetch', fetchMock)

  await getHealth()
  await getMeta()
  await getDecision({ delivery_day: '2026-01-15', cutoff: '09:00' })
  await getSeries({
    start_day: '2026-01-01',
    end_day: '2026-01-31',
    horizon_hours: 24,
  })
  await getMetrics({
    start_day: '2026-01-01',
    end_day: '2026-01-31',
    cutoff: '09:00',
  })

  const urls = fetchMock.mock.calls.map((call: readonly unknown[]) =>
    String(call[0]),
  )
  expect(urls).toEqual([
    '/api/health',
    '/api/meta',
    '/api/decision?delivery_day=2026-01-15&cutoff=09%3A00',
    '/api/series?start_day=2026-01-01&end_day=2026-01-31&horizon_hours=24',
    '/api/metrics?start_day=2026-01-01&end_day=2026-01-31&cutoff=09%3A00',
  ])
})

function jsonResponse(): Response {
  return new Response('{}', {
    status: 200,
    headers: { 'content-type': 'application/json' },
  })
}
