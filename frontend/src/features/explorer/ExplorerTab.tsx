import { space } from '../../design/tokens.ts'
import { ChartCard } from '../../components/ChartCard.tsx'
import { Typography } from '../../components/Typography.tsx'

export function ExplorerTab() {
  return (
    <div className={space.stack}>
      <ChartCard
        title="Horizon view"
        subtitle="Latest forecast published at least H hours before each half-hour. This is not the decision cutoff."
        caption="MW"
      >
        <Typography variant="bodyMedium">
          The horizon chart will appear here.
        </Typography>
      </ChartCard>
    </div>
  )
}
