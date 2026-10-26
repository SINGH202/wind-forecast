import { useQuery } from '@tanstack/react-query'

import { ApiError, getMeta, type MetaResponse } from './api/client.ts'
import { EmptyState } from './components/EmptyState.tsx'
import { ErrorState } from './components/ErrorState.tsx'
import { Footer } from './components/Footer.tsx'
import { Header } from './components/Header.tsx'
import { LoadingState } from './components/LoadingState.tsx'
import { color } from './design/tokens.ts'
import { AccuracyTab } from './features/accuracy/AccuracyTab.tsx'
import { DecisionTab } from './features/decision/DecisionTab.tsx'
import { ExplorerTab } from './features/explorer/ExplorerTab.tsx'
import { formatCoverage, formatCutoff } from './shell/formatMeta.ts'
import type { DeskTab } from './shell/tabs.ts'
import { useDeskTab } from './shell/useDeskTab.ts'

export default function App() {
  const [tab, selectTab] = useDeskTab()
  const meta = useQuery({
    queryKey: ['meta'],
    queryFn: ({ signal }) => getMeta(signal),
  })

  const coverage = meta.data
    ? formatCoverage(meta.data)
    : meta.isError
      ? 'Coverage unavailable'
      : 'Loading coverage'
  const cutoff = meta.data ? formatCutoff(meta.data) : 'Default cutoff —'

  return (
    <div className={`flex min-h-svh flex-col ${color.page}`}>
      <Header active={tab} onSelect={selectTab} />
      <main className="mx-auto w-full min-w-0 max-w-6xl flex-1 px-4 py-6 sm:px-6">
        <div
          role="tabpanel"
          id={`panel-${tab}`}
          aria-labelledby={`tab-${tab}`}
          tabIndex={0}
          className="focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-forecast"
        >
          {meta.isPending ? (
            <LoadingState />
          ) : meta.isError ? (
            <ErrorState
              message={errorMessage(meta.error)}
              onRetry={() => {
                void meta.refetch()
              }}
            />
          ) : meta.data.delivery_days.length === 0 ? (
            <EmptyState
              message="No wind data for this selection."
              hint="The snapshot has no delivery days from 2 January to 1 February 2026."
            />
          ) : (
            <TabBody
              tab={tab}
              deliveryDays={meta.data.delivery_days}
              cutoffOptions={meta.data.cutoff_options}
              defaultCutoff={meta.data.default_cutoff}
              timezone={meta.data.timezone}
            />
          )}
        </div>
      </main>
      <Footer coverage={coverage} cutoff={cutoff} />
    </div>
  )
}

function TabBody({
  tab,
  deliveryDays,
  cutoffOptions,
  defaultCutoff,
  timezone,
}: {
  tab: DeskTab
  deliveryDays: MetaResponse['delivery_days']
  cutoffOptions: MetaResponse['cutoff_options']
  defaultCutoff: string
  timezone: string
}) {
  switch (tab) {
    case 'decision':
      return (
        <DecisionTab
          deliveryDays={deliveryDays}
          cutoffOptions={cutoffOptions}
          defaultCutoff={defaultCutoff}
          timezone={timezone}
        />
      )
    case 'explorer':
      return <ExplorerTab deliveryDays={deliveryDays} />
    case 'accuracy':
      return (
        <AccuracyTab
          deliveryDays={deliveryDays}
          cutoffOptions={cutoffOptions}
          defaultCutoff={defaultCutoff}
          timezone={timezone}
        />
      )
    default: {
      const unreachable: never = tab
      return unreachable
    }
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `Could not load wind data (${error.status}).`
  }
  return 'Could not load wind data.'
}
