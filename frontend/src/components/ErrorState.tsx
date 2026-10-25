import { color } from '../design/tokens.ts'
import { Typography } from './Typography.tsx'

type ErrorStateProps = {
  message: string
  onRetry: () => void
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-start gap-3" role="alert">
      <Typography variant="bodyMedium" className={color.danger}>
        {message}
      </Typography>
      <button
        type="button"
        className={`rounded-md border border-line bg-paper px-3 py-1.5 ${color.focus}`}
        onClick={onRetry}
      >
        <Typography variant="button" className="text-ink">
          Retry
        </Typography>
      </button>
    </div>
  )
}
