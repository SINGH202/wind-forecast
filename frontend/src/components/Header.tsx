import { color, space } from '../design/tokens.ts'
import type { DeskTab } from '../shell/tabs.ts'
import { Tabs } from './Tabs.tsx'
import { Typography } from './Typography.tsx'

type HeaderProps = {
  active: DeskTab
  onSelect: (tab: DeskTab) => void
}

export function Header({ active, onSelect }: HeaderProps) {
  return (
    <header
      className={`border-b ${color.line} ${color.paper} ${space.pageX} py-4`}
    >
      <div className={`mx-auto flex w-full max-w-6xl flex-col ${space.md}`}>
        <Typography variant="h1">Wind Day-Ahead Desk</Typography>
        <Tabs active={active} onSelect={onSelect} />
      </div>
    </header>
  )
}
