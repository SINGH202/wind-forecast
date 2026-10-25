import { color, space } from '../design/tokens.ts'
import { Typography } from './Typography.tsx'

type KpiCardProps = {
  label: string
  value: string
  unit: string
  hint?: string
  title?: string
}

export function KpiCard({ label, value, unit, hint, title }: KpiCardProps) {
  return (
    <article
      title={title}
      className={`min-w-0 flex-1 basis-full rounded-md border ${color.line} ${color.paper} px-4 py-3 sm:basis-64`}
    >
      <div className={`flex flex-col ${space.xs}`}>
        <Typography variant="small">{label}</Typography>
        <div className="flex items-baseline gap-2">
          <Typography variant="h3">{value}</Typography>
          <Typography variant="small">{unit}</Typography>
        </div>
        {hint ? <Typography variant="small">{hint}</Typography> : null}
      </div>
    </article>
  )
}
