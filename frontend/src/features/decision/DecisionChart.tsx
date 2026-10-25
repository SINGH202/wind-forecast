import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { Typography } from '../../components/Typography.tsx'
import { formatMw } from '../../design/format.ts'
import { chart, chartStroke, color, space } from '../../design/tokens.ts'
import {
  isDecisionRow,
  toDecisionRows,
  type DecisionPoint,
} from './decisionView.ts'

type DecisionChartProps = {
  points: readonly DecisionPoint[]
  showBand: boolean
}

const axisTick = { fill: chartStroke.muted, fontSize: 11 }

export function DecisionChart({ points, showBand }: DecisionChartProps) {
  const rows = toDecisionRows(points)

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
        {showBand ? (
          <Typography variant="li" className="flex items-center gap-2">
            <span aria-hidden="true" className={`h-3 w-6 ${color.band}`} />
            {chart.band}
          </Typography>
        ) : null}
      </ul>
      <div
        className="h-80 w-full min-w-0 overflow-x-auto"
        role="img"
        aria-label="Decision forecast in MW. The dashed line is the forecast, the shaded area is the uncertainty band, and the solid line is metered wind."
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={rows}
            margin={{ top: 8, right: 8, left: 8, bottom: 0 }}
          >
            <CartesianGrid stroke={chartStroke.grid} vertical={false} />
            <XAxis
              dataKey="label"
              minTickGap={28}
              tick={axisTick}
              tickLine={false}
            />
            <YAxis
              tick={axisTick}
              width={64}
              tickFormatter={(value: number) => formatMw(value)}
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
            <Tooltip content={<DecisionTooltip showBand={showBand} />} />
            {showBand ? (
              <Area
                type="linear"
                dataKey="band"
                name={chart.band}
                stroke="none"
                fill={chartStroke.band}
                connectNulls={false}
                isAnimationActive={false}
                activeDot={false}
              />
            ) : null}
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
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function DecisionTooltip({
  active,
  payload,
  showBand,
}: {
  active?: boolean
  payload?: ReadonlyArray<{ payload?: unknown }>
  showBand: boolean
}) {
  const row = payload?.[0]?.payload
  if (!active || !isDecisionRow(row)) {
    return null
  }
  const band =
    showBand && row.band
      ? `${formatMw(row.band[0])}–${formatMw(row.band[1])} MW`
      : '—'
  return (
    <div className={`rounded-md border ${color.line} ${color.paper} px-3 py-2`}>
      <div className={space.stack}>
        <Typography variant="small">{row.time}</Typography>
        <Typography variant="bodyMedium">
          {`Forecast ${formatMw(row.forecastMw)} MW`}
        </Typography>
        <Typography variant="bodyMedium">{`Band ${band}`}</Typography>
        <Typography variant="bodyMedium">
          {`Actual ${formatMw(row.actualMw)} MW`}
        </Typography>
        <Typography variant="small">
          {row.publishTime
            ? `Published ${row.publishTime}`
            : 'No forecast was published before the cutoff.'}
        </Typography>
      </div>
    </div>
  )
}
