import { useState } from 'react'

import { ApiError } from '../../api/client.ts'
import { ChartCard } from '../../components/ChartCard.tsx'
import { DeskNotes } from '../../components/DeskNotes.tsx'
import { EmptyState } from '../../components/EmptyState.tsx'
import { ErrorState } from '../../components/ErrorState.tsx'
import { InfoPanel } from '../../components/InfoPanel.tsx'
import { KpiCard } from '../../components/KpiCard.tsx'
import { LoadingState } from '../../components/LoadingState.tsx'
import { SelectField } from '../../components/SelectField.tsx'
import { Typography } from '../../components/Typography.tsx'
import { formatHours, formatMwh } from '../../design/format.ts'
import { space } from '../../design/tokens.ts'
import { DecisionChart } from './DecisionChart.tsx'
import {
  ageSpread,
  cutoffSentence,
  deliveryComplete,
  hasForecast,
  initialCutoff,
  initialDeliveryDay,
  missingCounts,
  previousDay,
} from './decisionView.ts'
import { useDecision } from './useDecision.ts'

const firmExplanation =
  'Firm wind is the P10 of actual wind implied by the decision forecast and the error on earlier delivery days. It is the volume the buyer can count on.'

type DecisionTabProps = {
  deliveryDays: readonly string[]
  cutoffOptions: readonly string[]
  defaultCutoff: string
  timezone: string
}

export function DecisionTab({
  deliveryDays,
  cutoffOptions,
  defaultCutoff,
  timezone,
}: DecisionTabProps) {
  const [day, setDay] = useState(() => initialDeliveryDay(deliveryDays))
  const [cutoff, setCutoff] = useState(() =>
    initialCutoff(defaultCutoff, cutoffOptions),
  )
  const decision = useDecision(day, cutoff)
  const options = cutoffOptions.length > 0 ? cutoffOptions : [cutoff]
  const loaded =
    decision.data && decision.data.delivery_day === day && !decision.isFetching
      ? decision.data
      : undefined
  const sentence = loaded
    ? cutoffSentence(loaded.cutoff_local, timezone)
    : cutoffSentence(`${previousDay(day)}T${cutoff}:00`, timezone)

  return (
    <div className={space.stack}>
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
        <label
          className="flex w-full min-w-0 flex-col gap-1 sm:w-auto"
          htmlFor="decision-day"
        >
          <Typography variant="small">Delivery day</Typography>
          <SelectField
            id="decision-day"
            value={day}
            onChange={(event) => setDay(event.target.value)}
          >
            {deliveryDays.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </SelectField>
        </label>
        <label
          className="flex w-full min-w-0 flex-col gap-1 sm:w-auto"
          htmlFor="decision-cutoff"
        >
          <Typography variant="small">Cutoff</Typography>
          <SelectField
            id="decision-cutoff"
            value={cutoff}
            onChange={(event) => setCutoff(event.target.value)}
          >
            {options.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </SelectField>
        </label>
      </div>
      <Typography variant="bodyMedium">{sentence}</Typography>
      {!decision.data && decision.isLoading ? (
        <LoadingState />
      ) : decision.isError && !decision.data ? (
        <ErrorState
          message={errorMessage(decision.error)}
          onRetry={() => {
            void decision.refetch()
          }}
        />
      ) : !decision.data || !hasForecast(decision.data.points) ? (
        <EmptyState
          message="No wind data for this selection."
          hint="No forecast was published at or before this cutoff."
        />
      ) : (
        <DecisionBody data={decision.data} />
      )}
      <InfoPanel title="What this means for buying">
        <Typography variant="bodyMedium">
          Firm wind is what the buyer can count on. The rest of demand has to be
          procured from other sources.
        </Typography>
      </InfoPanel>
      <DeskNotes view="decision" />
    </div>
  )
}

function DecisionBody({
  data,
}: {
  data: NonNullable<ReturnType<typeof useDecision>['data']>
}) {
  const ages = ageSpread(data.points)
  const ageHint =
    ages.median === null
      ? 'No forecast was published before the cutoff.'
      : `Median ${formatHours(ages.median)} h, oldest ${formatHours(ages.oldest)} h.`
  const firmHint = data.band_available
    ? firmExplanation
    : `Uncertainty band unavailable: ${data.band_reason ?? 'insufficient history'}.`
  return (
    <div className={space.stack}>
      <div className={`flex flex-wrap ${space.md}`}>
        <KpiCard
          label="Expected energy"
          value={formatMwh(data.kpis.expected_mwh)}
          unit="MWh"
          hint={`${data.kpis.half_hours_with_forecast} of ${data.kpis.half_hours_expected} half-hours`}
        />
        <KpiCard
          label="Firm wind (P10)"
          value={formatMwh(data.kpis.firm_wind_mwh)}
          unit="MWh"
          hint={firmHint}
          title={firmExplanation}
        />
        <KpiCard
          label="Forecast age"
          value={formatHours(data.kpis.forecast_age_hours)}
          unit="h"
          hint={ageHint}
          title="Age of the newest forecast used at the cutoff, with the median and oldest of the selected half-hours."
        />
      </div>
      {!data.band_available ? (
        <Typography variant="bodyMedium">
          {`Uncertainty band unavailable: ${data.band_reason ?? 'insufficient history'}. The forecast is still shown.`}
        </Typography>
      ) : null}
      <ChartCard
        title="Decision forecast"
        subtitle="The latest forecast published at or before the cutoff."
        caption={`Missing forecast: ${missingCounts(data.points).forecast} half-hours. Missing actual: ${missingCounts(data.points).actual} half-hours.`}
      >
        {!deliveryComplete(data.points) ? (
          <Typography variant="bodyMedium">
            Delivery day not yet complete.
          </Typography>
        ) : null}
        <DecisionChart points={data.points} showBand={data.band_available} />
      </ChartCard>
    </div>
  )
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `Could not load wind data (${error.status}).`
  }
  return 'Could not load wind data.'
}
