import { color, space } from '../design/tokens.ts'
import { Typography } from './Typography.tsx'

type LoadingStateProps = {
  message?: string
}

export function LoadingState({
  message = 'Loading wind data.',
}: LoadingStateProps) {
  return (
    <div className={space.stack} aria-busy="true" aria-live="polite">
      <Typography variant="bodyMedium">{message}</Typography>
      <div className={`flex flex-wrap ${space.md}`} aria-hidden="true">
        <div className={`h-20 w-40 animate-pulse rounded-md ${color.band}`} />
        <div className={`h-20 w-40 animate-pulse rounded-md ${color.band}`} />
        <div className={`h-20 w-40 animate-pulse rounded-md ${color.band}`} />
      </div>
    </div>
  )
}
