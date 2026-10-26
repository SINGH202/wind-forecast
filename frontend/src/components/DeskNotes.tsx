import { space } from '../design/tokens.ts'
import { InfoPanel } from './InfoPanel.tsx'
import { Typography } from './Typography.tsx'

type DeskView = 'decision' | 'explorer' | 'accuracy'

type DeskNotesProps = {
  view: DeskView
}

export function DeskNotes({ view }: DeskNotesProps) {
  return (
    <div className={space.stack}>
      <InfoPanel title="How to read this">
        <HowTo view={view} />
      </InfoPanel>
      <InfoPanel title="Assumptions" defaultOpen={false}>
        <Assumptions />
      </InfoPanel>
    </div>
  )
}

function HowTo({ view }: { view: DeskView }) {
  switch (view) {
    case 'decision':
      return (
        <ul className={`list-disc pl-5 ${space.xs}`}>
          <Typography variant="li">
            The dashed line is the latest wind forecast published at or before
            the cutoff on the day before delivery. A later forecast is not used.
          </Typography>
          <Typography variant="li">
            The shaded band is the P10 to P90 range from earlier delivery days.
            Firm wind is the lower edge, the volume the buyer can count on.
          </Typography>
          <Typography variant="li">
            The solid line is metered wind. A gap is a missing value, not zero
            megawatts.
          </Typography>
        </ul>
      )
    case 'explorer':
      return (
        <ul className={`list-disc pl-5 ${space.xs}`}>
          <Typography variant="li">
            This is a horizon view. It does not use the decision cutoff.
          </Typography>
          <Typography variant="li">
            Each half-hour shows the latest forecast published at least H hours
            before that half-hour.
          </Typography>
          <Typography variant="li">
            The solid line is metered wind and the dashed line is that forecast.
            Both are in MW.
          </Typography>
        </ul>
      )
    case 'accuracy':
      return (
        <ul className={`list-disc pl-5 ${space.xs}`}>
          <Typography variant="li">
            MAE, RMSE, bias, and normalized MAE use the decision forecast at the
            cutoff you selected.
          </Typography>
          <Typography variant="li">
            Positive bias means the forecast was higher than metered wind.
          </Typography>
          <Typography variant="li">
            The horizon chart uses every forecast vintage. The hour, wind-level,
            and histogram charts use the decision forecast.
          </Typography>
          <Typography variant="li">
            Known limitation: the January decision forecast has a persistent
            positive bias of about 1,852 MW, and the P10/P90 band and firm wind
            already include it because they are built from those errors; the
            cause is unconfirmed.
          </Typography>
        </ul>
      )
    default: {
      const unreachable: never = view
      return unreachable
    }
  }
}

function Assumptions() {
  return (
    <ul className={`list-disc pl-5 ${space.xs}`}>
      <Typography variant="li">
        The desk covers January 2026 only, for Great Britain as a whole.
      </Typography>
      <Typography variant="li">
        Actual wind is Elexon FUELHH generation for fuel type WIND, every
        half-hour. Forecasts are WINDFOR generation. Those forecasts are hourly,
        so some half-hours stay blank.
      </Typography>
      <Typography variant="li">
        For delivery day D the buyer decides on D-1. The forecast is the latest
        one published at or before the cutoff. The default cutoff is 09:00
        Europe/London, before the morning day-ahead auctions close. The choices
        run from 08:00 to 09:00. 09:30 and later are after the 09:20 auction
        close.
      </Typography>
      <Typography variant="li">
        Error is forecast minus actual. A positive error is an over-forecast.
      </Typography>
      <Typography variant="li">
        There is no demand series, so the desk does not compute residual demand.
        Firm wind is the decision forecast minus an error quantile from earlier
        days.
      </Typography>
    </ul>
  )
}
