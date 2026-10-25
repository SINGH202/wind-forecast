import {
  Brush,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { formatMw as formatMwValue } from '../../design/format.ts'
import { chart, chartStroke, color, space } from '../../design/tokens.ts'
import { Typography } from '../../components/Typography.tsx'
import {
  formatMw,
  isChartRow,
  missingCounts,
  toChartRows,
  type SeriesPoint,
} from './seriesView.ts'

type SeriesChartProps = {
  points: readonly SeriesPoint[]
}

type TooltipEntry = {
  payload?: unknown
}

type SeriesTooltipProps = {
  active?: boolean
  payload?: ReadonlyArray<TooltipEntry>
}

export function SeriesChart({ points }: SeriesChartProps) {
  const rows = toChartRows(points)
  const gaps = missingCounts(points)

  return (
    <div className={space.stack}>
      <ul className={`flex flex-wrap ${space.md}`}>
        <Typography variant="li" className="flex items-center gap-2">
          <span aria-hidden="true" className={`h-0.5 w-6 ${color.actual}`} />
          {chart.actual}
        </Typography>
        <Typography variant="li" className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className={`h-0 w-6 border-t-2 border-dashed ${color.forecast}`}
          />
          {chart.forecast}
        </Typography>
      </ul>
      <div className="h-80 w-full min-w-0 overflow-x-auto">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={rows}
            margin={{ top: 8, right: 8, left: 8, bottom: 0 }}
          >
            <CartesianGrid stroke={chartStroke.grid} vertical={false} />
            <XAxis
              dataKey="label"
              minTickGap={48}
              tick={{ fill: chartStroke.muted, fontSize: 11 }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: chartStroke.muted, fontSize: 12 }}
              width={64}
              tickFormatter={(value: number) => formatMwValue(value)}
              tickLine={false}
              axisLine={false}
              label={{
                value: 'MW',
                angle: -90,
                position: 'insideLeft',
                fill: chartStroke.muted,
                fontSize: 12,
              }}
            />
            <Tooltip content={<SeriesTooltip />} />
            <Line
              type="linear"
              dataKey="actualMw"
              name={chart.actual}
              stroke={chartStroke.actual}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Line
              type="linear"
              dataKey="forecastMw"
              name={chart.forecast}
              stroke={chartStroke.forecast}
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Brush
              dataKey="label"
              height={28}
              stroke={chartStroke.forecast}
              travellerWidth={8}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <Typography variant="small">
        {`Missing forecast: ${gaps.forecast} half-hours. Missing actual: ${gaps.actual} half-hours.`}
      </Typography>
    </div>
  )
}

function SeriesTooltip({ active, payload }: SeriesTooltipProps) {
  const row = payload?.[0]?.payload
  if (!active || !isChartRow(row)) {
    return null
  }
  return (
    <div className={`rounded-md border ${color.line} ${color.paper} px-3 py-2`}>
      <div className={space.stack}>
        <Typography variant="small">{row.time}</Typography>
        <Typography variant="bodyMedium">{`Actual ${formatMw(row.actualMw)}`}</Typography>
        <Typography variant="bodyMedium">
          {`Forecast ${formatMw(row.forecastMw)}`}
        </Typography>
        <Typography variant="bodyMedium">
          {`Error ${formatMw(row.errorMw, true)}`}
        </Typography>
      </div>
    </div>
  )
}
