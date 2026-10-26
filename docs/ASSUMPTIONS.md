# Assumptions

Rules the app applies. Sample patterns cited here are from `docs/DATA_NOTES.md`.

## Scope

January 2026 delivery days only, at national level. The only inputs are Elexon BMRS FUELHH and WINDFOR. Demand and price data are out of scope.

## Decision rule

For delivery day D, the buyer decides on D-1. For each half-hour of D, the decision forecast is the WINDFOR row for that `startTime` with the latest `publishTime` that is still less than or equal to the cutoff. A row published after the cutoff is never used.

The default cutoff is 09:00 Europe/London on D-1. The cutoff is configurable. In the WINDFOR sample, every `startTime` has more than one `publishTime`, so more than one forecast exists to choose from.

## Why that cutoff

Buyers for delivery day D bid on D-1, so the forecast cutoff should fall before the morning auctions close. EPEX SPOT’s GB 60-minute day-ahead order book closes at 09:20 GMT/BST on D-1, and the outcome is published and validated as soon as possible from 09:30 GMT/BST. The GB 30-minute auction closes at 15:30 GMT/BST, with results from 15:45 GMT/BST (EPEX SPOT Operational Rules). The products page states the same clocks but labels them GMT. Nord Pool’s N2EX gate closure is 09:50 GMT, with results at latest 10:00 GMT. Those first results are preliminary until TSO validation, normally before 11:00 CET (Nord Pool support article, modified 26 July 2022). The GB day-ahead regulations do not print 09:50. The N2EX half-hour order-book close was not found: UNVERIFIED.

Default: 09:00 Europe/London on D-1, because it is before both verified morning closes under either a GMT or a GMT/BST reading of 09:20. Offer 08:00 to 10:00 Europe/London.

## Data definitions

- Actual: FUELHH `generation` where `fuelType` is `WIND`. The sample contains only that fuel type, on a 30-minute `startTime` grid.
- Forecast: WINDFOR `generation`. In the sample, `startTime` is hourly.
- Horizon: `startTime - publishTime`, in hours.

## Error definition

Error = forecast − actual, paired on `startTime`. A positive error means the forecast was higher than the actual (over-forecast). A negative error means under-forecast.

## Limitations

There is no demand series, so the app does not compute residual demand and does not say how much electricity must be bought from thermal plants.

Instead it shows firm wind: the decision forecast minus an error quantile. That is the amount of wind the buyer can reasonably count on.

### Known limitation: persistent positive forecast bias

For January 2026 the decision forecast is biased high by about 1,852 MW across 744 pairs. 631 of those 744 hours are over-forecasts, 27 of 31 days are positive, and the ratio of total forecast to total actual is 1.160. The bias is positive in all five actual-wind quintiles, from +993 MW to +2,824 MW, and in every horizon bucket, from +1,548 MW at 0–6 h to +2,005 MW at 36–48 h, including horizons below 0 h and above 48 h. The P10/P90 band and firm wind are computed from these empirical decision-forecast errors, so they already include this bias. The cause is unconfirmed.

## Questions

- Which error quantile, and over which errors (all horizons, or split by horizon)?
- WINDFOR `startTime` in the sample is hourly and FUELHH is half-hourly. How is a forecast paired with each half-hour actual?
- The sample timestamps end in `Z`. The notes do not confirm that means UTC. How is that string compared with 09:00 Europe/London?
- If no WINDFOR row for a `startTime` has `publishTime` at or before the cutoff, what is shown? The samples do not say to fill the gap.
- Are negative-horizon WINDFOR rows (240 of 1168 in the sample, where `startTime` is before `publishTime`) allowed as the decision forecast?
- Is the cutoff chooser limited to 08:00–10:00 Europe/London, or can it be any time?
- The samples do not state the unit of `generation`. What label should the app show?
