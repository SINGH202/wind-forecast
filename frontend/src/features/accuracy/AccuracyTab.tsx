import { useState } from 'react'

import { ApiError } from '../../api/client.ts'
import { DeskNotes } from '../../components/DeskNotes.tsx'
import { EmptyState } from '../../components/EmptyState.tsx'
import { ErrorState } from '../../components/ErrorState.tsx'
import { KpiCard } from '../../components/KpiCard.tsx'
import { LoadingState } from '../../components/LoadingState.tsx'
import { Typography } from '../../components/Typography.tsx'
import { formatMw, formatPercent } from '../../design/format.ts'
import { color, space } from '../../design/tokens.ts'
import { AccuracyCharts } from './AccuracyCharts.tsx'
import {
  clampDay,
  coverageBounds,
  fullCoverageRange,
  hasMae,
  initialCutoff,
} from './accuracyView.ts'
import { useMetrics } from './useMetrics.ts'

type AccuracyTabProps = {
  deliveryDays: readonly string[]
  cutoffOptions: readonly string[]
  defaultCutoff: string
  timezone: string
}

export function AccuracyTab({
  deliveryDays,
  cutoffOptions,
  defaultCutoff,
  timezone,
}: AccuracyTabProps) {
  const bounds = coverageBounds(deliveryDays)
  const seeded = fullCoverageRange(deliveryDays)
  const [start, setStart] = useState(seeded.start)
  const [end, setEnd] = useState(seeded.end)
  const [cutoff, setCutoff] = useState(() =>
    initialCutoff(defaultCutoff, cutoffOptions),
  )
  const startDay = bounds ? clampDay(start, bounds.min, bounds.max) : start
  const endDay = bounds ? clampDay(end, bounds.min, bounds.max) : end
  const metrics = useMetrics(startDay, endDay, cutoff)
  const rangeReady = startDay <= endDay
  const options = cutoffOptions.length > 0 ? cutoffOptions : [cutoff]

  return (
    <div className={space.stack}>
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
        <label
          className="flex w-full min-w-0 flex-col gap-1 sm:w-auto"
          htmlFor="accuracy-start"
        >
          <Typography variant="small">From</Typography>
          <input
            id="accuracy-start"
            type="date"
            className={inputClass}
            min={bounds?.min}
            max={bounds?.max}
            value={startDay}
            onChange={(event) => setStart(event.target.value)}
          />
        </label>
        <label
          className="flex w-full min-w-0 flex-col gap-1 sm:w-auto"
          htmlFor="accuracy-end"
        >
          <Typography variant="small">To</Typography>
          <input
            id="accuracy-end"
            type="date"
            className={inputClass}
            min={bounds?.min}
            max={bounds?.max}
            value={endDay}
            onChange={(event) => setEnd(event.target.value)}
          />
        </label>
        <label
          className="flex w-full min-w-0 flex-col gap-1 sm:w-auto"
          htmlFor="accuracy-cutoff"
        >
          <Typography variant="small">Cutoff</Typography>
          <select
            id="accuracy-cutoff"
            className={inputClass}
            value={cutoff}
            onChange={(event) => setCutoff(event.target.value)}
          >
            {options.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Typography variant="bodyMedium">
        {`Headline numbers use the decision forecast at ${cutoff} ${timezone}.`}
      </Typography>
      {rangeReady ? (
        <MetricsBody
          isLoading={metrics.isLoading}
          isFetching={metrics.isFetching}
          isError={metrics.isError}
          error={metrics.error}
          data={metrics.data}
          onRetry={() => {
            void metrics.refetch()
          }}
        />
      ) : (
        <EmptyState
          message="No wind data for this selection."
          hint="Choose an end day on or after the start day."
        />
      )}
      <DeskNotes view="accuracy" />
    </div>
  )
}

const inputClass = `w-full max-w-full rounded-md border border-line bg-paper px-2 py-1 text-sm text-ink sm:w-auto ${color.focus}`

type MetricsBodyProps = {
  isLoading: boolean
  isFetching: boolean
  isError: boolean
  error: unknown
  data: ReturnType<typeof useMetrics>['data']
  onRetry: () => void
}

function MetricsBody({
  isLoading,
  isFetching,
  isError,
  error,
  data,
  onRetry,
}: MetricsBodyProps) {
  if (isLoading) {
    return <LoadingState />
  }
  if (isError) {
    return <ErrorState message={errorMessage(error)} onRetry={onRetry} />
  }
  if (!data || (data.n === 0 && !hasMae(data.by_horizon.buckets))) {
    return (
      <EmptyState
        message="No wind data for this selection."
        hint="Try another range inside January 2026."
      />
    )
  }
  const biasHint =
    data.bias_mw === null
      ? 'Positive means the forecast is above actual wind.'
      : data.bias_mw > 0
        ? 'Positive: the forecast is above actual wind.'
        : data.bias_mw < 0
          ? 'Negative: the forecast is below actual wind.'
          : 'Bias is zero for this range.'
  return (
    <div className={space.stack} aria-busy={isFetching}>
      {isFetching ? (
        <Typography variant="small">Loading wind data.</Typography>
      ) : null}
      <div className={`flex flex-wrap ${space.md}`}>
        <KpiCard label="MAE" value={formatMw(data.mae_mw)} unit="MW" />
        <KpiCard label="RMSE" value={formatMw(data.rmse_mw)} unit="MW" />
        <KpiCard
          label="Bias"
          value={formatMw(data.bias_mw, true)}
          unit="MW"
          hint={biasHint}
        />
        <KpiCard
          label="Normalized MAE"
          value={formatPercent(data.nmae)}
          unit="%"
        />
      </div>
      <AccuracyCharts metrics={data} />
    </div>
  )
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `Could not load wind data (${error.status}).`
  }
  return 'Could not load wind data.'
}
