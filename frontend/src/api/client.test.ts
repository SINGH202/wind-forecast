import { afterEach, expect, test, vi } from 'vitest'

import {
  getDecision,
  getHealth,
  getMeta,
  getMetrics,
  getSeries,
} from './client.ts'

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

test('each endpoint is requested on the relative /api path', async () => {
  const fetchMock = vi.fn(async () => jsonResponse())
  vi.stubGlobal('fetch', fetchMock)

  await getHealth()
  await getMeta()
  await getDecision({ delivery_day: '2026-01-15', cutoff: '09:00' })
  await getSeries({
    start_day: '2026-01-02',
    end_day: '2026-02-01',
    horizon_hours: 24,
  })
  await getMetrics({
    start_day: '2026-01-02',
    end_day: '2026-02-01',
    cutoff: '09:00',
  })

  const urls = fetchMock.mock.calls.map((call: readonly unknown[]) =>
    String(call[0]),
  )
  expect(urls).toEqual([
    '/api/health',
    '/api/meta',
    '/api/decision?delivery_day=2026-01-15&cutoff=09%3A00',
    '/api/series?start_day=2026-01-02&end_day=2026-02-01&horizon_hours=24',
    '/api/metrics?start_day=2026-01-02&end_day=2026-02-01&cutoff=09%3A00',
  ])
})

test('a server failure is retried 3 times with backoff, then succeeds', async () => {
  vi.useFakeTimers()
  const fetchMock = vi
    .fn()
    .mockRejectedValueOnce(new TypeError('offline'))
    .mockResolvedValueOnce(errorResponse(503))
    .mockResolvedValueOnce(errorResponse(502))
    .mockResolvedValueOnce(jsonResponse())
  vi.stubGlobal('fetch', fetchMock)

  const pending = getHealth()
  await vi.runAllTimersAsync()
  await pending

  expect(fetchMock).toHaveBeenCalledTimes(4)
  vi.useRealTimers()
})

test('a client error is not retried', async () => {
  const fetchMock = vi.fn(async () => errorResponse(400))
  vi.stubGlobal('fetch', fetchMock)

  await expect(getHealth()).rejects.toMatchObject({ status: 400 })
  expect(fetchMock).toHaveBeenCalledTimes(1)
})

test('gives up after 3 retries', async () => {
  vi.useFakeTimers()
  const fetchMock = vi.fn(async () => errorResponse(503))
  vi.stubGlobal('fetch', fetchMock)

  const pending = getHealth().then(
    () => 'ok',
    (error: unknown) => error,
  )
  await vi.runAllTimersAsync()
  const error = await pending

  expect(error).toMatchObject({ status: 503 })
  expect(fetchMock).toHaveBeenCalledTimes(4)
  vi.useRealTimers()
})

function jsonResponse(): Response {
  return new Response('{}', {
    status: 200,
    headers: { 'content-type': 'application/json' },
  })
}

function errorResponse(status: number): Response {
  return new Response('unavailable', { status })
}
