export const DESK_TABS = [
  { id: 'decision', label: 'Decision' },
  { id: 'explorer', label: 'Explorer' },
  { id: 'accuracy', label: 'Accuracy' },
] as const

export type DeskTab = (typeof DESK_TABS)[number]['id']

export function tabFromHash(hash: string): DeskTab {
  const bare = hash.startsWith('#') ? hash.slice(1) : hash
  if (bare === 'decision' || bare === 'explorer' || bare === 'accuracy') {
    return bare
  }
  return 'decision'
}
