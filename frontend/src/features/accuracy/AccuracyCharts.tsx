import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { ChartCard } from '../../components/ChartCard.tsx'
import { EmptyState } from '../../components/EmptyState.tsx'
import { Typography } from '../../components/Typography.tsx'
import { formatMw } from '../../design/format.ts'
import { chartStroke, color, space } from '../../design/tokens.ts'
import type { MetricsResponse } from '../../api/client.ts'
import {
  hasMae,
  histogramCaption,
  histogramRows,
  horizonAccuracyCaption,
  horizonRows,
  hourCaption,
  hourRows,
  levelCaption,
  levelRows,
  quantileLabel,
  sortWorstDays,
  worstDayCaption,
  type BarRow,
  type HistRow,
  type WorstDay,
  type WorstSortKey,
} from './accuracyView.ts'

type ChartsProps = {
  metrics: MetricsResponse
}

const axisTick = { fill: chartStroke.muted, fontSize: 11 }

export function AccuracyCharts({ metrics }: ChartsProps) {
  return (
    <div className={space.stack}>
      <div className={`flex flex-wrap ${space.md}`}>
        <Typography variant="small">
          {`${metrics.n} decision pairs. ${metrics.pairs_excluded_missing} half-hours excluded because a forecast or actual is missing.`}
        </Typography>
      </div>
      <ChartCard
        title={metrics.by_horizon.label}
        subtitle="Every forecast publication in the range. This is not the decision cutoff."
        caption={horizonAccuracyCaption(metrics.by_horizon.buckets)}
      >
        {hasMae(metrics.by_horizon.buckets) ? (
          <GroupedBars rows={horizonRows(metrics.by_horizon.buckets)} />
        ) : (
          <EmptyState
            message="No wind data for this selection."
            hint="No horizon bucket has pairs."
          />
        )}
      </ChartCard>
      <div className="grid min-w-0 gap-4 md:grid-cols-2">
        <ChartCard
          title="MAE by hour of day"
          subtitle="Decision forecast, Europe/London clock hour."
          caption={hourCaption(metrics.by_hour_london)}
        >
          {hasMae(metrics.by_hour_london) ? (
            <MaeBars
              rows={hourRows(metrics.by_hour_london)}
              label="Mean absolute error in MW by hour of day, Europe/London."
            />
          ) : (
            <EmptyState
              message="No wind data for this selection."
              hint="No London hour has pairs."
            />
          )}
        </ChartCard>
        <ChartCard
          title="MAE by wind level"
          subtitle="Decision forecast, by actual wind."
          caption={levelCaption(metrics.by_wind_level)}
        >
          {hasMae(metrics.by_wind_level) ? (
            <MaeBars
              rows={levelRows(metrics.by_wind_level)}
              angled
              label="Mean absolute error in MW by actual wind level."
            />
          ) : (
            <EmptyState
              message="No wind data for this selection."
              hint="No wind-level band has pairs."
            />
          )}
        </ChartCard>
      </div>
      <ChartCard
        title="Error histogram"
        subtitle="Decision-forecast errors in 500 MW bins."
        caption={histogramCaption(
          metrics.p10_error_mw,
          metrics.p90_error_mw,
          metrics.histogram,
        )}
      >
        {metrics.histogram.length > 0 ? (
          <Histogram
            rows={histogramRows(metrics.histogram)}
            p10Label={quantileLabel(metrics.histogram, metrics.p10_error_mw)}
            p90Label={quantileLabel(metrics.histogram, metrics.p90_error_mw)}
          />
        ) : (
          <EmptyState
            message="No wind data for this selection."
            hint="There are no decision-forecast errors in this range."
          />
        )}
      </ChartCard>
      <WorstDays rows={metrics.worst_days} />
    </div>
  )
}

function GroupedBars({ rows }: { rows: BarRow[] }) {
  return (
    <div className={space.stack}>
      <SeriesLegend />
      <div
        className="h-72 w-full min-w-0 overflow-x-auto"
        role="img"
        aria-label="Mean absolute error and bias in MW for all forecast vintages, grouped by horizon."
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            margin={{ top: 8, right: 8, left: 8, bottom: 8 }}
          >
            <CartesianGrid stroke={chartStroke.grid} vertical={false} />
            <XAxis
              dataKey="label"
              tick={axisTick}
              interval={0}
              angle={-28}
              textAnchor="end"
              height={72}
              tickLine={false}
            />
            <YAxis
              tick={axisTick}
              width={64}
              tickFormatter={(value: number) => formatMw(value)}
              tickLine={false}
              axisLine={false}
              label={mwLabel}
            />
            <Tooltip content={<BarTooltip />} />
            <Bar
              dataKey="maeMw"
              name="MAE"
              fill={chartStroke.actual}
              isAnimationActive={false}
            />
            <Bar
              dataKey="biasMw"
              name="Bias"
              fill={chartStroke.forecast}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function MaeBars({
  rows,
  angled = false,
  label,
}: {
  rows: BarRow[]
  angled?: boolean
  label: string
}) {
  return (
    <div
      className="h-72 w-full min-w-0 overflow-x-auto"
      role="img"
      aria-label={label}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          margin={{ top: 8, right: 8, left: 8, bottom: angled ? 16 : 8 }}
        >
          <CartesianGrid stroke={chartStroke.grid} vertical={false} />
          <XAxis
            dataKey="label"
            tick={axisTick}
            minTickGap={angled ? 0 : 16}
            interval={angled ? 0 : undefined}
            angle={angled ? -28 : 0}
            textAnchor={angled ? 'end' : 'middle'}
            height={angled ? 72 : 30}
            tickLine={false}
          />
          <YAxis
            tick={axisTick}
            width={64}
            tickFormatter={(value: number) => formatMw(value)}
            tickLine={false}
            axisLine={false}
            label={mwLabel}
          />
          <Tooltip content={<BarTooltip />} />
          <Bar
            dataKey="maeMw"
            name="MAE"
            fill={chartStroke.actual}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function Histogram({
  rows,
  p10Label,
  p90Label,
}: {
  rows: HistRow[]
  p10Label: string | null
  p90Label: string | null
}) {
  return (
    <div className={space.stack}>
      <ul className={`flex flex-wrap ${space.md}`}>
        <Typography variant="li" className="flex items-center gap-2">
          <span aria-hidden="true" className={`h-3 w-6 ${color.band}`} />
          Half-hours
        </Typography>
        <Typography variant="li" className="flex items-center gap-2">
          <span aria-hidden="true" className={`h-3 w-0.5 ${color.actual}`} />
          P10
        </Typography>
        <Typography variant="li" className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className={`h-3 w-0 border-l-2 border-dashed ${color.forecast}`}
          />
          P90
        </Typography>
      </ul>
      <div
        className="h-72 w-full min-w-0 overflow-x-auto"
        role="img"
        aria-label="Half-hours by forecast error in MW, with P10 and P90 marked."
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            margin={{ top: 16, right: 8, left: 8, bottom: 8 }}
          >
            <CartesianGrid stroke={chartStroke.grid} vertical={false} />
            <XAxis
              dataKey="label"
              tick={axisTick}
              minTickGap={24}
              tickLine={false}
            />
            <YAxis
              tick={axisTick}
              width={40}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <Tooltip content={<HistTooltip />} />
            <Bar
              dataKey="count"
              name="Half-hours"
              fill={chartStroke.forecast}
              fillOpacity={0.35}
              isAnimationActive={false}
            />
            {p10Label ? (
              <ReferenceLine
                x={p10Label}
                stroke={chartStroke.actual}
                strokeWidth={2}
                label={{ value: 'P10', fill: chartStroke.actual, fontSize: 11 }}
              />
            ) : null}
            {p90Label ? (
              <ReferenceLine
                x={p90Label}
                stroke={chartStroke.forecast}
                strokeDasharray="6 4"
                strokeWidth={2}
                label={{
                  value: 'P90',
                  fill: chartStroke.forecast,
                  fontSize: 11,
                }}
              />
            ) : null}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function WorstDays({ rows }: { rows: WorstDay[] }) {
  const [sortKey, setSortKey] = useState<WorstSortKey>('mae_mw')
  const [direction, setDirection] = useState<'asc' | 'desc'>('desc')
  const sorted = sortWorstDays(rows, sortKey, direction)

  function toggle(key: WorstSortKey) {
    if (key === sortKey) {
      setDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setDirection(key === 'delivery_day' ? 'asc' : 'desc')
  }

  return (
    <ChartCard
      title="Worst days"
      subtitle="Decision forecast. Each row is one delivery day."
      caption={worstDayCaption(rows)}
    >
      {rows.length === 0 ? (
        <EmptyState
          message="No wind data for this selection."
          hint="No delivery day has decision-forecast pairs."
        />
      ) : (
        <div className="min-w-0 overflow-x-auto">
          <table className="w-full min-w-[28rem] border-collapse text-left">
            <thead>
              <tr>
                <SortHeader
                  label="Day"
                  column="delivery_day"
                  sortKey={sortKey}
                  direction={direction}
                  onSort={toggle}
                />
                <SortHeader
                  label="MAE MW"
                  column="mae_mw"
                  sortKey={sortKey}
                  direction={direction}
                  onSort={toggle}
                />
                <SortHeader
                  label="Bias MW"
                  column="bias_mw"
                  sortKey={sortKey}
                  direction={direction}
                  onSort={toggle}
                />
                <SortHeader
                  label="Pairs"
                  column="n"
                  sortKey={sortKey}
                  direction={direction}
                  onSort={toggle}
                />
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr key={row.delivery_day} className="border-t border-line">
                  <td className="py-2 pr-3">
                    <Typography variant="bodyMedium">
                      {row.delivery_day}
                    </Typography>
                  </td>
                  <td className="py-2 pr-3">
                    <Typography variant="bodyMedium">
                      {formatMw(row.mae_mw)}
                    </Typography>
                  </td>
                  <td className="py-2 pr-3">
                    <Typography variant="bodyMedium">
                      {formatMw(row.bias_mw, true)}
                    </Typography>
                  </td>
                  <td className="py-2">
                    <Typography variant="bodyMedium">{row.n}</Typography>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ChartCard>
  )
}

function SortHeader({
  label,
  column,
  sortKey,
  direction,
  onSort,
}: {
  label: string
  column: WorstSortKey
  sortKey: WorstSortKey
  direction: 'asc' | 'desc'
  onSort: (key: WorstSortKey) => void
}) {
  const active = column === sortKey
  const arrow = active ? (direction === 'asc' ? ' ↑' : ' ↓') : ''
  return (
    <th
      scope="col"
      aria-sort={
        active ? (direction === 'asc' ? 'ascending' : 'descending') : 'none'
      }
      className="pb-2 pr-3"
    >
      <button
        type="button"
        className={`rounded-md ${color.focus}`}
        onClick={() => onSort(column)}
      >
        <Typography variant="button" className="text-ink">
          {`${label}${arrow}`}
        </Typography>
      </button>
    </th>
  )
}

function SeriesLegend() {
  return (
    <ul className={`flex flex-wrap ${space.md}`}>
      <Typography variant="li" className="flex items-center gap-2">
        <span aria-hidden="true" className={`h-3 w-6 ${color.actual}`} />
        MAE
      </Typography>
      <Typography variant="li" className="flex items-center gap-2">
        <span aria-hidden="true" className="h-3 w-6 bg-forecast" />
        Bias
      </Typography>
    </ul>
  )
}

const mwLabel = {
  value: 'MW',
  angle: -90,
  position: 'insideLeft' as const,
  fill: chartStroke.muted,
  fontSize: 12,
}

function BarTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: ReadonlyArray<{ payload?: unknown }>
}) {
  const row = payload?.[0]?.payload
  if (!active || !isBarRow(row)) {
    return null
  }
  return (
    <div className={`rounded-md border ${color.line} ${color.paper} px-3 py-2`}>
      <div className={space.stack}>
        <Typography variant="small">{row.label}</Typography>
        <Typography variant="bodyMedium">{`MAE ${formatMw(row.maeMw)} MW`}</Typography>
        <Typography variant="bodyMedium">
          {`Bias ${formatMw(row.biasMw, true)} MW`}
        </Typography>
      </div>
    </div>
  )
}

function HistTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: ReadonlyArray<{ payload?: unknown }>
}) {
  const row = payload?.[0]?.payload
  if (!active || !isHistRow(row)) {
    return null
  }
  return (
    <div className={`rounded-md border ${color.line} ${color.paper} px-3 py-2`}>
      <div className={space.stack}>
        <Typography variant="small">{row.range}</Typography>
        <Typography variant="bodyMedium">{`${row.count} half-hours`}</Typography>
      </div>
    </div>
  )
}

function isBarRow(value: unknown): value is BarRow {
  if (!value || typeof value !== 'object') {
    return false
  }
  return 'label' in value && 'maeMw' in value && 'biasMw' in value
}

function isHistRow(value: unknown): value is HistRow {
  if (!value || typeof value !== 'object') {
    return false
  }
  return 'range' in value && 'count' in value
}
