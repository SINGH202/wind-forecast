import { chart, color, space } from '../../design/tokens.ts'
import { ChartCard } from '../../components/ChartCard.tsx'
import { InfoPanel } from '../../components/InfoPanel.tsx'
import { KpiCard } from '../../components/KpiCard.tsx'
import { Typography } from '../../components/Typography.tsx'

export function DecisionTab() {
  return (
    <div className={space.stack}>
      <div className={`flex flex-wrap ${space.md}`}>
        <KpiCard label="Expected" value="—" unit="MWh" hint="Placeholder" />
        <KpiCard
          label="Firm wind (P10)"
          value="—"
          unit="MWh"
          hint="Placeholder"
        />
        <KpiCard label="Forecast age" value="—" unit="h" hint="Placeholder" />
      </div>
      <ChartCard
        title="Decision forecast"
        subtitle="The forecast available at the D-1 cutoff"
        caption="MW"
      >
        <Legend />
        <Typography variant="bodyMedium">
          The half-hour chart for the selected delivery day will appear here.
        </Typography>
      </ChartCard>
      <InfoPanel title="How firm wind is counted">
        <Typography variant="bodyMedium">
          Firm wind is the decision forecast minus an error quantile from
          earlier delivery days. This desk does not compute residual demand.
        </Typography>
      </InfoPanel>
    </div>
  )
}

function Legend() {
  return (
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
      <Typography variant="li" className="flex items-center gap-2">
        <span aria-hidden="true" className={`h-3 w-6 ${color.band}`} />
        {chart.band}
      </Typography>
    </ul>
  )
}
