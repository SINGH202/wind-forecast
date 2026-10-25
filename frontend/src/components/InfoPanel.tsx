import type { ReactNode } from 'react'
import { useId, useState } from 'react'

import { color, space } from '../design/tokens.ts'
import { Typography } from './Typography.tsx'

type InfoPanelProps = {
  title: string
  children: ReactNode
}

export function InfoPanel({ title, children }: InfoPanelProps) {
  const [open, setOpen] = useState(true)
  const panelId = useId()

  return (
    <section
      className={`rounded-md border ${color.line} ${color.paper} px-4 py-3`}
    >
      <button
        type="button"
        className={`rounded-md ${color.focus}`}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((current) => !current)}
      >
        <Typography variant="button" className="text-ink">
          {title}
        </Typography>
      </button>
      <div id={panelId} hidden={!open} className={`pt-3 ${space.stack}`}>
        {children}
      </div>
    </section>
  )
}
