import type { paths } from './schema.ts'

type JsonOf<Path extends keyof paths> =
  paths[Path]['get']['responses'][200]['content']['application/json']

type QueryOf<Path extends keyof paths> =
  paths[Path]['get']['parameters']['query']

export type HealthResponse = JsonOf<'/api/health'>
export type MetaResponse = JsonOf<'/api/meta'>
export type DecisionQuery = QueryOf<'/api/decision'>
export type DecisionResponse = JsonOf<'/api/decision'>
export type SeriesQuery = QueryOf<'/api/series'>
export type SeriesResponse = JsonOf<'/api/series'>
export type MetricsQuery = QueryOf<'/api/metrics'>
export type MetricsResponse = JsonOf<'/api/metrics'>

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
  }
}

const DEFAULT_RETRIES = 3
const WAKE_RETRIES = 5
const ATTEMPT_TIMEOUT_MS = 15_000

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return getJson('/api/health', signal)
}

/** Ping the API until it answers. Used when Render may still be waking. */
export function wakeApi(signal?: AbortSignal): Promise<HealthResponse> {
  return getJson('/api/health', signal, WAKE_RETRIES)
}

export function getMeta(signal?: AbortSignal): Promise<MetaResponse> {
  return getJson('/api/meta', signal)
}

export function getDecision(
  query: DecisionQuery,
  signal?: AbortSignal,
): Promise<DecisionResponse> {
  return getJson(
    `/api/decision${toQuery([
      ['delivery_day', query.delivery_day],
      ['cutoff', query.cutoff],
    ])}`,
    signal,
  )
}

export function getSeries(
  query: SeriesQuery,
  signal?: AbortSignal,
): Promise<SeriesResponse> {
  return getJson(
    `/api/series${toQuery([
      ['start_day', query.start_day],
      ['end_day', query.end_day],
      ['horizon_hours', query.horizon_hours],
    ])}`,
    signal,
  )
}

export function getMetrics(
  query: MetricsQuery,
  signal?: AbortSignal,
): Promise<MetricsResponse> {
  return getJson(
    `/api/metrics${toQuery([
      ['start_day', query.start_day],
      ['end_day', query.end_day],
      ['cutoff', query.cutoff],
    ])}`,
    signal,
  )
}

type QueryValue = string | number | null | undefined

function toQuery(
  entries: ReadonlyArray<readonly [string, QueryValue]>,
): string {
  const params = new URLSearchParams()
  for (const [key, value] of entries) {
    if (value === undefined || value === null) {
      continue
    }
    params.set(key, String(value))
  }
  const text = params.toString()
  return text.length > 0 ? `?${text}` : ''
}

async function getJson<T>(
  path: string,
  signal?: AbortSignal,
  maxRetries: number = DEFAULT_RETRIES,
): Promise<T> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await readJson<T>(path, signal)
    } catch (error) {
      if (attempt >= maxRetries || !canRetry(error, signal)) {
        throw error
      }
      await wait(backoffMs(attempt), signal)
    }
  }
}

async function readJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), ATTEMPT_TIMEOUT_MS)
  const onParentAbort = () => controller.abort()
  if (signal) {
    if (signal.aborted) {
      controller.abort()
    } else {
      signal.addEventListener('abort', onParentAbort, { once: true })
    }
  }
  try {
    const response = await fetch(path, { signal: controller.signal })
    if (!response.ok) {
      throw new ApiError(response.status, await response.text())
    }
    return (await response.json()) as T
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', onParentAbort)
  }
}

function backoffMs(attempt: number): number {
  return 1000 * 2 ** attempt
}

function canRetry(error: unknown, signal?: AbortSignal): boolean {
  if (signal?.aborted || isAbortError(error)) {
    // Per-attempt timeouts abort a hung cold start; keep retrying those.
    return isTimeoutAbort(error) && !signal?.aborted
  }
  if (error instanceof ApiError) {
    return error.status >= 500 || error.status === 404 || error.status === 408
  }
  return error instanceof TypeError
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

function isTimeoutAbort(error: unknown): boolean {
  return isAbortError(error) && error instanceof DOMException
}

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(abortError())
      return
    }
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort)
      resolve()
    }, ms)
    const onAbort = () => {
      clearTimeout(timer)
      reject(abortError())
    }
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}

function abortError(): DOMException {
  return new DOMException('The operation was aborted.', 'AbortError')
}
