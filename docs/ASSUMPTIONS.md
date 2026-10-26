# Assumptions

Rules the app applies. Sample patterns cited here are from `docs/DATA_NOTES.md`.

## Scope

Delivery days are 2 January through 1 February 2026, at national level. A decision for delivery day D is made on D-1, so these are the days decided in January. The only inputs are Elexon BMRS FUELHH and WINDFOR. Demand and price data are out of scope. The P10/P90 band may still use earlier delivery days, including late December.

## Decision rule

For delivery day D, the buyer decides on D-1. For each half-hour of D, the decision forecast is the WINDFOR row for that `startTime` with the latest `publishTime` that is still less than or equal to the cutoff. A row published after the cutoff is never used.

The default cutoff is 09:00 Europe/London on D-1. The cutoff is configurable. In the WINDFOR sample, every `startTime` has more than one `publishTime`, so more than one forecast exists to choose from.

## Why that cutoff

Buyers for delivery day D bid on D-1, so the forecast cutoff should fall before the morning auctions close. EPEX SPOT’s GB 60-minute day-ahead order book closes at 09:20 GMT/BST on D-1, and the outcome is published and validated as soon as possible from 09:30 GMT/BST. The GB 30-minute auction closes at 15:30 GMT/BST, with results from 15:45 GMT/BST (EPEX SPOT Operational Rules). The products page states the same clocks but labels them GMT. Nord Pool’s N2EX gate closure is 09:50 GMT, with results at latest 10:00 GMT. Those first results are preliminary until TSO validation, normally before 11:00 CET (Nord Pool support article, modified 26 July 2022). The GB day-ahead regulations do not print 09:50. The N2EX half-hour order-book close was not found: UNVERIFIED.

Default: 09:00 Europe/London on D-1, because it is before both verified morning closes under either a GMT or a GMT/BST reading of 09:20. Offer 08:00 to 09:00 Europe/London. 09:30 and later fall after the 09:20 EPEX close, so a buyer could not have acted on a forecast published after that close.

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

For delivery days 2 January through 1 February 2026, `scripts/diagnose_bias.py` prints a decision-forecast bias of 1745.94 MW on 744 pairs. 630 pairs have forecast >= actual, and sum(forecast) / sum(actual) is 1.1547. Quintile biases are 1817.8, 1057.6, 1065.9, 2708.4, and 2075.4 MW. Horizon biases are 1428.5 MW at [0,6), 1900.1 MW at [36,48], 1652.1 MW below 0 h, and 1415.0 MW above 48 h. The P10/P90 band and firm wind are computed from these empirical decision-forecast errors, so they already include this bias. The cause is unconfirmed.

## Resolved decisions

- Quantiles are the P10 and P90 of decision-forecast errors from delivery days before the selected day. All horizons are pooled.
- Pairing is on `startTime`. The forecast is hourly, so metrics use the 24 matching hourly slots per day. The :30 actuals are not paired.
- A slot with no valid forecast is flagged and never filled.
- A negative-horizon row can never be a decision forecast, because a D-1 cutoff precedes every target on D. Explorer uses horizon >= 0.

## To verify

- Whether the `Z` suffix means UTC.
- The unit of `generation`. The app currently labels it MW.
