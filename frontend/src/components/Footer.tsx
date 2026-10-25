import { color, space } from '../design/tokens.ts'
import { Typography } from './Typography.tsx'

type FooterProps = {
  coverage: string
  cutoff: string
}

export function Footer({ coverage, cutoff }: FooterProps) {
  return (
    <footer
      className={`border-t ${color.line} ${color.paper} ${space.pageX} py-3`}
    >
      <div
        className={`mx-auto flex w-full max-w-6xl flex-col ${space.xs} sm:flex-row sm:items-center sm:justify-between`}
      >
        <Typography variant="small">{coverage}</Typography>
        <Typography variant="small">{cutoff}</Typography>
      </div>
    </footer>
  )
}
