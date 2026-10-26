# PRD: day-ahead wind forecast portal

Pilot for a day-ahead power trader or analyst. January 2026 only. National wind only. Inputs are Elexon BMRS FUELHH (`fuelType` `WIND`) and WINDFOR. No demand, prices, other weather, or login.

A delivery day D is the 48 half-hours whose `startTime` falls on that UTC date, from `D 00:00Z` to `D 23:30Z`. That matches the sample, where `settlementDate` equals the UTC date of `startTime` and period 1 is `00:00`. Charts and hour-of-day labels use Europe/London. Stored timestamps are the sample strings treated as UTC (they all end in `Z`). January 2026 is GMT, so the London clock matches UTC. The cutoff is still built in Europe/London and then converted to UTC before any comparison.

Power is shown in MW. An hourly WINDFOR slot contributes `MW × 1.0` MWh. A forecast that lands on both :00 and :30 contributes `MW × 0.5` MWh. Missing slots are left empty. They are never copied, interpolated, or dropped from the 48-row grid.

## Jobs

1. What will wind produce tomorrow, per half-hour, from forecasts published by my cutoff?
2. How wrong have these forecasts been, and how wrong should I assume they will be?

## Locked decisions

These close the questions in `docs/ASSUMPTIONS.md`.

- Cutoff choices are `08:00`, `08:30`, `09:00` Europe/London on D-1. The default is the `DECISION_CUTOFF_TIME` setting, which is `09:00`. The API rejects any other cutoff. 09:30 and later fall after the 09:20 EPEX close.
- A forecast matches a half-hour only when `startTime` is equal. The WINDFOR sample is hourly, so `:30` slots have no forecast unless a row with that exact `startTime` exists. Show the gap.
- `publishTime <= cutoff` is allowed even if the horizon is negative. For this cutoff range and a delivery day D, selected horizons are still positive, because every `startTime` on D is after 09:00 on D-1.
- If no row is early enough, that half-hour's forecast fields are null and `missing_forecast` is true.
- Generation is labelled MW. The samples do not name the unit; the product still shows MW and MWh on every figure.

## Decision rule

For each of the 48 half-hours on D, the decision forecast is the WINDFOR row with that `startTime` and the greatest `publishTime` that is still `<=` the cutoff instant. Rows published later are ignored.

The uncertainty band uses only earlier delivery days, with the same cutoff clock. For each prior day E `<` D, take that day's decision forecast, pair it with the FUELHH actual on the same `startTime`, and keep the error. Do not use day D or any later day.

```
error = forecast_mw - actual_mw
```

Positive error means the forecast was too high.

Percentiles use linear interpolation on the sorted errors: index `(n - 1) * p`.

```
band_low_mw  = forecast_mw - p90(error)    # P10 of implied generation
band_high_mw = forecast_mw - p10(error)    # P90 of implied generation
firm_mw      = band_low_mw
```

`p90(error) >= p10(error)`, so the low band is never above the high band. Do not clamp negative firm MW. If `n = 0`, the band and firm values are null and the response includes `no_prior_days_for_band`.

```
slot_hours     = 1.0 when forecast start times are an hour apart, else 0.5
expected_mwh  = sum of forecast_mw × slot_hours where forecast_mw is present
firm_wind_mwh = sum of firm_mw × slot_hours where firm_mw is present
forecast_age_hours = cutoff_utc - publish_time
```

The age card shows the smallest age among the selected rows (the freshest forecast that made the cutoff), in hours to one decimal. If no forecast was selected, the card is empty, not zero.

Actuals are the FUELHH wind MW for that `startTime` when a row exists. A missing actual is a gap, including when the half-hour has not been published yet. It is not a request error.

## Explorer rule

Explorer is a horizon view. It does not use the decision cutoff. The screen must say that, in the heading or next to the slider: "Horizon view: latest forecast published at least H hours before each half-hour."

For each half-hour in the chosen UTC date range, and a horizon H from 0 to 48 hours (step 1, default 0):

Pick the WINDFOR row with that exact `startTime` and the greatest `publishTime` such that

```
horizon_hours = startTime - publishTime >= H
```

"At least H hours earlier" includes an equal horizon. The slider starts at 0, so a negative horizon never qualifies. No row means a gap.

## Accuracy rule

Two populations. Do not mix them in one number.

Headline population: the decision forecast at the selected cutoff. For each half-hour in the date range, use the same rule as the Decision view (greatest `publishTime` at or before that day's cutoff). Pair it with the FUELHH actual on the same `startTime`. This population is used for MAE, RMSE, bias, normalized MAE, P10 and P90 of error, the hour-of-day breakdown, the wind-level breakdown, the histogram, and the worst-days table.

`n` is the number of those pairs. Half-hours missing a decision forecast or an actual are excluded and counted. They are not filled.

Horizon population: every WINDFOR row in the range whose `startTime` equals a FUELHH wind row, whatever its `publishTime`. This is used only for the horizon breakdown. The chart and the API label are "All forecast vintages, grouped by horizon".

These four numbers, and P10 and P90 of the same errors, use the headline population only. They are not the Decision-tab band. That band still uses decision-forecast errors from delivery days before the day on screen.

```
MAE  = mean(|error|)                         MW
RMSE = sqrt(mean(error²))                    MW
bias = mean(error)                           MW
nMAE = MAE / mean(actual_mw)                 unitless
```

If `n = 0` or `mean(actual_mw) = 0`, the four metrics are null. P10 and P90 are null when `n = 0`. Do not substitute zero.

Horizon buckets, half-open except the last: `< 0`, `[0, 6)`, `[6, 12)`, `[12, 24)`, `[24, 48]`, `> 48` hours. Each returns `n`, `mae_mw`, `bias_mw`.

Hour of day is the Europe/London hour of `startTime`, 0–23. Return all 24 hours. `n = 0` is allowed.

Wind-level buckets use actual MW: `[0, 5000)`, `[5000, 10000)`, `[10000, 15000)`, `>= 15000`. Same `n`, `mae_mw`, `bias_mw`.

Histogram bins are 500 MW wide, half-open, covering the errors in the response. The last bin is closed. Omit empty bins.

Worst days: for each UTC delivery day, MAE and bias of its pairs. Sort by `mae_mw` descending. Return at most 5. Fewer days means a shorter table, not an error.

## Screens

Three tabs. Every tab has three states:

- **Loading.** The request is in flight. Show "Loading wind data." Do not show an empty message yet, and do not keep old numbers in the KPI cards.
- **Empty.** The response is 200 and there is nothing to draw (`n = 0` or all forecasts null). Show "No wind data for this selection."
- **Error.** The request failed. Show "Could not load wind data" and the HTTP status. Offer Retry. A 400 names the bad parameter.

Chart colours: actual = solid dark, forecast = dashed blue, uncertainty band = light blue. Axes say MW. Do not draw across a gap.

### Decision

```
[ Decision ] [ Explorer ] [ Accuracy ]

Delivery day [ 2026-01-15 v ]   Cutoff [ 09:00 London v ]

[ Expected  12 400 MWh ] [ Firm wind (P10)  9 800 MWh ] [ Forecast age  1.5 h ]
  48 of 48 half-hours        from days before 15 Jan         newest used

MW
  |        ....==== forecast (dashed)  ==== actual (solid)
  |   ##### band #####
  +------------------------------------------------ London time
  00:00              12:00                    23:30

  Gaps stay blank. A note lists missing_forecast and missing_actual counts.
```

### Explorer

```
[ Decision ] [ Explorer ] [ Accuracy ]

Horizon view — not the decision cutoff

From [ 2026-01-01 ]  To [ 2026-01-31 ]    Horizon  [====|====]  12 h
         latest forecast published at least 12 h before each half-hour

MW |  ---- forecast    —— actual
   +---------------------------------------------- London time
```

### Accuracy

```
[ Decision ] [ Explorer ] [ Accuracy ]

From [ 2026-01-01 ]  To [ 2026-01-31 ]   Cutoff [ 09:00 London v ]
Headline numbers use the decision forecast at this cutoff.

[ MAE  800 MW ] [ RMSE  1 100 MW ] [ Bias  +200 MW ] [ nMAE  0.08 ]
[ P10 error  -400 MW ] [ P90 error  +900 MW ]
  n = 400 decision pairs     over-forecast if bias > 0

All forecast vintages, grouped by horizon
[ <0 ] [ 0–6 h ] [ 6–12 h ] [ 12–24 h ] [ 24–48 h ] [ >48 h ]

[ MAE by hour, London ]  [ MAE by wind level ]     both from the decision forecast

[ Error histogram, 500 MW bins ]                   decision-forecast errors

Worst days (decision forecast)
Day          MAE MW    Bias MW    Pairs
2026-01-09    1 400      +600       24
...
```

## API

JSON. Times in responses are UTC `YYYY-MM-DDTHH:MM:SSZ` plus a London display string where listed. An unknown query value, a day outside January 2026, `start_day > end_day`, a cutoff not in the three choices, or `horizon_hours` outside 0–48 returns 400 `{ "detail": "<parameter> is invalid" }`. A selection with no rows returns 200 and null metrics, not 404.

### `GET /api/meta`

No query.

```
delivery_days: string[]          # UTC dates in Jan 2026 that have FUELHH wind or WINDFOR
default_cutoff: "09:00"             # value of DECISION_CUTOFF_TIME
cutoff_options: ["08:00","08:30","09:00"]
timezone: "Europe/London"
power_unit: "MW"
energy_unit: "MWh"
resolution_minutes: 30
```

`delivery_days: []` is the empty state for the whole app.

### `GET /api/decision?delivery_day=2026-01-15&cutoff=09:00`

`cutoff` defaults to `DECISION_CUTOFF_TIME` (`09:00`). Any other value than the three allowed times returns 400.

```
delivery_day, cutoff_local, cutoff_utc
points[48]:
  start_time, start_time_london
  forecast_mw, actual_mw, firm_mw, band_low_mw, band_high_mw   # number or null
  publish_time                                                  # or null
  horizon_hours, forecast_age_hours                             # or null
  missing_forecast, missing_actual                              # bool
kpis:
  expected_mwh, firm_wind_mwh, forecast_age_hours               # or null
  half_hours_with_forecast, half_hours_expected                 # expected is 48
error_sample:
  n, p10_error_mw, p90_error_mw, prior_days_used                # quantiles null if n = 0
flags: string[]    # "no_prior_days_for_band", "missing_forecast_slots",
                   # "missing_actual_slots", "negative_firm_wind"
```

### `GET /api/series?start_day=2026-01-01&end_day=2026-01-31&horizon_hours=0`

`horizon_hours` defaults to 0.

```
start_day, end_day, horizon_hours
points[]:    # one per half-hour in the range, in start_time order
  start_time, start_time_london
  forecast_mw, actual_mw, publish_time, horizon_hours    # nulls when missing
  missing_forecast, missing_actual
```

### `GET /api/metrics?start_day=2026-01-01&end_day=2026-01-31&cutoff=09:00`

`cutoff` defaults to `DECISION_CUTOFF_TIME` (`09:00`) and must be one of the three allowed times.

Headline fields use the decision forecast at that cutoff. `by_horizon` does not.

```
start_day, end_day, cutoff
n, pairs_excluded_missing
mae_mw, rmse_mw, bias_mw, nmae, mean_actual_mw          # null when n = 0 or mean actual is 0
p10_error_mw, p90_error_mw                             # decision-forecast errors; null when n = 0
by_hour_london[]: hour, n, mae_mw, bias_mw             # 24 rows, decision forecast
by_wind_level[]:  bucket, n, mae_mw, bias_mw           # decision forecast
histogram[]:      edge_low_mw, edge_high_mw, count     # decision-forecast errors
worst_days[]:     delivery_day, n, mae_mw, bias_mw     # at most 5, decision forecast
by_horizon:
  label: "All forecast vintages, grouped by horizon"
  buckets[]: bucket, n, mae_mw, bias_mw                # every matched publication
```

Bucket `mae_mw` and `bias_mw` are null when that bucket's `n` is 0.

## Non-goals

No demand and no residual demand. No prices. No weather beyond what is already inside FUELHH and WINDFOR. No other fuel types. No dates outside January 2026. No authentication.
