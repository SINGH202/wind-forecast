import { useState } from 'react'

import { ApiError } from '../../api/client.ts'
import { ChartCard } from '../../components/ChartCard.tsx'
import { DeskNotes } from '../../components/DeskNotes.tsx'
import { EmptyState } from '../../components/EmptyState.tsx'
import { ErrorState } from '../../components/ErrorState.tsx'
import { LoadingState } from '../../components/LoadingState.tsx'
import { Typography } from '../../components/Typography.tsx'
import { color, space } from '../../design/tokens.ts'
import { useDebouncedValue } from '../../shared/hooks/useDebouncedValue.ts'
import { SeriesChart } from './SeriesChart.tsx'
import {
  clampDay,
  coverageBounds,
  DEFAULT_HORIZON_HOURS,
  horizonCaption,
  initialRange,
  type SeriesPoint,
} from './seriesView.ts'
import { useSeries } from './useSeries.ts'

type ExplorerTabProps = {
  deliveryDays: readonly string[]
}

export function ExplorerTab({ deliveryDays }: ExplorerTabProps) {
  const bounds = coverageBounds(deliveryDays)
  const seeded = initialRange(deliveryDays)
  const [start, setStart] = useState(seeded.start)
  const [end, setEnd] = useState(seeded.end)
  const [horizon, setHorizon] = useState(DEFAULT_HORIZON_HOURS)
  const debouncedHorizon = useDebouncedValue(horizon, 400)
  const startDay = bounds ? clampDay(start, bounds.min, bounds.max) : start
  const endDay = bounds ? clampDay(end, bounds.min, bounds.max) : end
  const series = useSeries(startDay, endDay, debouncedHorizon)
  const plottedHorizon = series.data?.horizon_hours ?? debouncedHorizon
  const rangeReady = startDay <= endDay

  return (
    <div className={space.stack}>
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
        <label
          className="flex w-full min-w-0 flex-col gap-1 sm:w-auto"
          htmlFor="explorer-start"
        >
          <Typography variant="small">From</Typography>
          <input
            id="explorer-start"
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
          htmlFor="explorer-end"
        >
          <Typography variant="small">To</Typography>
          <input
            id="explorer-end"
            type="date"
            className={inputClass}
            min={bounds?.min}
            max={bounds?.max}
            value={endDay}
            onChange={(event) => setEnd(event.target.value)}
          />
        </label>
        <label
          className="flex w-full min-w-0 flex-1 flex-col gap-1 sm:min-w-56"
          htmlFor="explorer-horizon"
        >
          <Typography variant="small">{`Horizon ${horizon} h`}</Typography>
          <input
            id="explorer-horizon"
            type="range"
            min={0}
            max={48}
            step={1}
            value={horizon}
            aria-valuemin={0}
            aria-valuemax={48}
            aria-valuenow={horizon}
            aria-valuetext={`${horizon} hours`}
            className={`w-full accent-forecast ${color.focus}`}
            onChange={(event) => setHorizon(Number(event.target.value))}
          />
        </label>
      </div>
      <ChartCard
        title="Horizon view"
        subtitle="This is not the decision-cutoff view."
        caption={horizonCaption(plottedHorizon)}
      >
        {rangeReady ? (
          <SeriesBody
            isLoading={series.isLoading}
            isFetching={series.isFetching}
            isError={series.isError}
            error={series.error}
            points={series.data?.points}
            onRetry={() => {
              void series.refetch()
            }}
          />
        ) : (
          <EmptyState
            message="No wind data for this selection."
            hint="Choose an end day on or after the start day."
          />
        )}
      </ChartCard>
      <DeskNotes view="explorer" />
    </div>
  )
}

const inputClass = `w-full max-w-full rounded-md border border-line bg-paper px-2 py-1 text-sm text-ink sm:w-auto ${color.focus}`

type SeriesBodyProps = {
  isLoading: boolean
  isFetching: boolean
  isError: boolean
  error: unknown
  points: readonly SeriesPoint[] | undefined
  onRetry: () => void
}

function SeriesBody({
  isLoading,
  isFetching,
  isError,
  error,
  points,
  onRetry,
}: SeriesBodyProps) {
  if (isLoading) {
    return <LoadingState />
  }
  if (isError) {
    return <ErrorState message={errorMessage(error)} onRetry={onRetry} />
  }
  if (!points || points.length === 0) {
    return (
      <EmptyState
        message="No wind data for this selection."
        hint="Try another range inside the snapshot coverage."
      />
    )
  }
  return (
    <div className={space.stack} aria-busy={isFetching}>
      <SeriesChart points={points} />
    </div>
  )
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `Could not load wind data (${error.status}).`
  }
  return 'Could not load wind data.'
}
