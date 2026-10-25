import { space } from '../../design/tokens.ts'
import { ChartCard } from '../../components/ChartCard.tsx'
import { KpiCard } from '../../components/KpiCard.tsx'
import { Typography } from '../../components/Typography.tsx'

export function AccuracyTab() {
  return (
    <div className={space.stack}>
      <div className={`flex flex-wrap ${space.md}`}>
        <KpiCard label="MAE" value="—" unit="MW" hint="Placeholder" />
        <KpiCard label="RMSE" value="—" unit="MW" hint="Placeholder" />
        <KpiCard label="Bias" value="—" unit="MW" hint="Placeholder" />
      </div>
      <ChartCard
        title="Accuracy"
        subtitle="Headline numbers use the decision forecast at the selected cutoff"
        caption="MW"
      >
        <Typography variant="bodyMedium">
          Hour, wind level, and error charts will appear here.
        </Typography>
      </ChartCard>
    </div>
  )
}
