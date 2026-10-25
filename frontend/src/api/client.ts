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

export function getHealth(): Promise<HealthResponse> {
  return getJson('/api/health')
}

export function getMeta(): Promise<MetaResponse> {
  return getJson('/api/meta')
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

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal })
  if (!response.ok) {
    throw new ApiError(response.status, await response.text())
  }
  return (await response.json()) as T
}
