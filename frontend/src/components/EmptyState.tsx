import { space } from '../design/tokens.ts'
import { Typography } from './Typography.tsx'

type EmptyStateProps = {
  message: string
  hint: string
}

export function EmptyState({ message, hint }: EmptyStateProps) {
  return (
    <div className={space.stack}>
      <Typography variant="bodyMedium">{message}</Typography>
      <Typography variant="small">{hint}</Typography>
    </div>
  )
}
