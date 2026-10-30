import { useQuery } from '@tanstack/react-query'

import { ApiError, getMeta, wakeApi, type MetaResponse } from './api/client.ts'
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
  // Render free tier sleeps. Wake /api/health first, then load desk meta.
  const wake = useQuery({
    queryKey: ['wake'],
    queryFn: ({ signal }) => wakeApi(signal),
    staleTime: 5 * 60_000,
  })
  const meta = useQuery({
    queryKey: ['meta'],
    queryFn: ({ signal }) => getMeta(signal),
    enabled: wake.isSuccess,
  })

  const coverage = meta.data
    ? formatCoverage(meta.data)
    : wake.isError || meta.isError
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
          <DeskBody tab={tab} wake={wake} meta={meta} />
        </div>
      </main>
      <Footer coverage={coverage} cutoff={cutoff} />
    </div>
  )
}

function DeskBody({
  tab,
  wake,
  meta,
}: {
  tab: DeskTab
  wake: {
    isSuccess: boolean
    isError: boolean
    isFetching: boolean
    error: unknown
    refetch: () => unknown
  }
  meta: {
    isPending: boolean
    isError: boolean
    error: unknown
    data: MetaResponse | undefined
    refetch: () => unknown
  }
}) {
  if (!wake.isSuccess) {
    if (wake.isError && !wake.isFetching) {
      return (
        <ErrorState
          message={errorMessage(wake.error)}
          onRetry={() => {
            void wake.refetch()
          }}
        />
      )
    }
    return <LoadingState waking />
  }
  if (meta.isPending) {
    return <LoadingState />
  }
  if (meta.isError) {
    return (
      <ErrorState
        message={errorMessage(meta.error)}
        onRetry={() => {
          void meta.refetch()
        }}
      />
    )
  }
  if (!meta.data || meta.data.delivery_days.length === 0) {
    return (
      <EmptyState
        message="No wind data for this selection."
        hint="The snapshot has no delivery days from 2 January to 1 February 2026."
      />
    )
  }
  return (
    <TabBody
      tab={tab}
      deliveryDays={meta.data.delivery_days}
      cutoffOptions={meta.data.cutoff_options}
      defaultCutoff={meta.data.default_cutoff}
      timezone={meta.data.timezone}
    />
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
