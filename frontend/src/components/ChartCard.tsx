import type { ReactNode } from 'react'

import { color, space } from '../design/tokens.ts'
import { Typography } from './Typography.tsx'

type ChartCardProps = {
  title: string
  subtitle: string
  caption: string
  children: ReactNode
}

export function ChartCard({
  title,
  subtitle,
  caption,
  children,
}: ChartCardProps) {
  return (
    <section
      className={`rounded-md border ${color.line} ${color.paper} px-4 py-4`}
    >
      <div className={space.stack}>
        <div className={`flex flex-col ${space.xs}`}>
          <Typography variant="h2">{title}</Typography>
          <Typography variant="small">{subtitle}</Typography>
        </div>
        {children}
        <Typography variant="small">{caption}</Typography>
      </div>
    </section>
  )
}
