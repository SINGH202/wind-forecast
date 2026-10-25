import { useEffect, useState } from 'react'

import { tabFromHash, type DeskTab } from './tabs.ts'

export function useDeskTab(): readonly [DeskTab, (tab: DeskTab) => void] {
  const [tab, setTab] = useState<DeskTab>(() =>
    tabFromHash(window.location.hash),
  )

  useEffect(() => {
    if (window.location.hash === '') {
      window.history.replaceState(null, '', '#decision')
    }
    const onHashChange = () => {
      setTab(tabFromHash(window.location.hash))
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  function select(next: DeskTab) {
    const hash = `#${next}`
    if (window.location.hash !== hash) {
      window.location.hash = next
    }
    setTab(next)
  }

  return [tab, select]
}
