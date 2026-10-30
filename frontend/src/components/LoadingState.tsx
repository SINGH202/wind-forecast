import { useEffect, useState } from 'react'

import { color, space } from '../design/tokens.ts'
import { Typography } from './Typography.tsx'

const WAKE_AFTER_MS = 3000
export const WAKE_MESSAGE =
  'Waking up the data service, this can take up to a minute'

type LoadingStateProps = {
  message?: string
  /** When true, show the wake-up spinner and message immediately. */
  waking?: boolean
}

export function LoadingState({
  message = 'Loading wind data.',
  waking = false,
}: LoadingStateProps) {
  const [slow, setSlow] = useState(false)

  useEffect(() => {
    if (waking) {
      return
    }
    const timer = window.setTimeout(() => setSlow(true), WAKE_AFTER_MS)
    return () => window.clearTimeout(timer)
  }, [waking])

  const showWake = waking || slow

  return (
    <div className={space.stack} aria-busy="true" aria-live="polite">
      {showWake ? (
        <div className="flex items-center gap-3">
          <div
            className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-line border-t-forecast"
            aria-hidden="true"
          />
          <Typography variant="bodyMedium">{WAKE_MESSAGE}</Typography>
        </div>
      ) : (
        <Typography variant="bodyMedium">{message}</Typography>
      )}
      <div className={`flex flex-wrap ${space.md}`} aria-hidden="true">
        <div className={`h-20 w-40 animate-pulse rounded-md ${color.band}`} />
        <div className={`h-20 w-40 animate-pulse rounded-md ${color.band}`} />
        <div className={`h-20 w-40 animate-pulse rounded-md ${color.band}`} />
      </div>
    </div>
  )
}
