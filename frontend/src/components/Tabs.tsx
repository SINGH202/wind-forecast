import type { KeyboardEvent } from 'react'
import { useRef } from 'react'

import { color, space } from '../design/tokens.ts'
import type { DeskTab } from '../shell/tabs.ts'
import { DESK_TABS } from '../shell/tabs.ts'
import { Typography } from './Typography.tsx'

type TabsProps = {
  active: DeskTab
  onSelect: (tab: DeskTab) => void
}

export function Tabs({ active, onSelect }: TabsProps) {
  const buttons = useRef<Partial<Record<DeskTab, HTMLButtonElement | null>>>({})

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const index = DESK_TABS.findIndex((tab) => tab.id === active)
    let nextIndex: number
    if (event.key === 'ArrowRight') {
      nextIndex = (index + 1) % DESK_TABS.length
    } else if (event.key === 'ArrowLeft') {
      nextIndex = (index - 1 + DESK_TABS.length) % DESK_TABS.length
    } else if (event.key === 'Home') {
      nextIndex = 0
    } else if (event.key === 'End') {
      nextIndex = DESK_TABS.length - 1
    } else {
      return
    }
    event.preventDefault()
    const next = DESK_TABS[nextIndex]
    if (!next || next.id === active) {
      return
    }
    // Focus during the key event so the browser keeps the visible focus ring.
    buttons.current[next.id]?.focus()
    onSelect(next.id)
  }

  return (
    <div
      role="tablist"
      aria-label="Views"
      className={`flex flex-wrap ${space.sm}`}
      onKeyDown={onKeyDown}
    >
      {DESK_TABS.map((tab) => {
        const selected = tab.id === active
        return (
          <button
            key={tab.id}
            ref={(node) => {
              buttons.current[tab.id] = node
            }}
            id={`tab-${tab.id}`}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={`panel-${tab.id}`}
            tabIndex={selected ? 0 : -1}
            className={`rounded-md px-3 py-1.5 ${color.focus} ${
              selected ? 'bg-ink' : 'bg-paper'
            }`}
            onClick={() => onSelect(tab.id)}
          >
            <Typography
              variant="button"
              className={selected ? 'text-paper' : 'text-ink'}
            >
              {tab.label}
            </Typography>
          </button>
        )
      })}
    </div>
  )
}
