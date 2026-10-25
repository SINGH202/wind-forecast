# Data notes

Counts below are from the two files in `docs/samples/`.

- `fuelhh_wind_sample.json`: a JSON array of 96 objects.
- `windfor_sample.json`: a JSON array of 1168 objects.

`docs/samples/README.md` records the requests that produced them:

- FUELHH: `settlementDateFrom=2026-01-05`, `settlementDateTo=2026-01-06`, `fuelType=WIND`
- WINDFOR: `publishDateTimeFrom=2026-01-05T00:00:00Z`, `publishDateTimeTo=2026-01-07T00:00:00Z`

Horizon in section 3 is `startTime - publishTime`, in hours.

## 1. Schema

Every FUELHH object has the same seven fields. Every WINDFOR object has the same four fields. JSON numbers in both files are integer literals (no decimal point). No value is JSON `null`.

### FUELHH

| Field | JSON type | Example |
| --- | --- | --- |
| `dataset` | string | `"FUELHH"` |
| `publishTime` | string | `"2026-01-07T00:00:00Z"` |
| `startTime` | string | `"2026-01-06T23:30:00Z"` |
| `settlementDate` | string | `"2026-01-06"` |
| `settlementPeriod` | number | `48` |
| `fuelType` | string | `"WIND"` |
| `generation` | number | `15206` |

`dataset` is `"FUELHH"` on all 96 rows. `fuelType` is `"WIND"` on all 96 rows. `settlementDate` is `"2026-01-05"` on 48 rows and `"2026-01-06"` on 48 rows. `settlementPeriod` is an integer from 1 to 48, and each value occurs once per `settlementDate`. `generation` is an integer from 3376 to 16757. All 96 `generation` values are distinct. None are 0 or negative.

### WINDFOR

| Field | JSON type | Example |
| --- | --- | --- |
| `dataset` | string | `"WINDFOR"` |
| `publishTime` | string | `"2026-01-06T22:30:00Z"` |
| `startTime` | string | `"2026-01-05T21:00:00Z"` |
| `generation` | number | `6961` |

`dataset` is `"WINDFOR"` on all 1168 rows. `generation` is an integer from 3486 to 18593. There are 937 distinct values. None are 0 or negative.

## 2. Time semantics

The files do not define what `startTime` or `publishTime` represent. This section is only the pattern in the strings.

Every `startTime` and `publishTime` in both files is a 20-character string: `YYYY-MM-DDTHH:MM:SSZ`. Seconds are `00` on every row. No other suffix or numeric offset appears.

### FUELHH

`startTime` runs from `2026-01-05T00:00:00Z` to `2026-01-06T23:30:00Z`. There are 96 distinct values, one per row. Sorted, each step is 0.5 hours. Minutes are `00` or `30` (48 each).

`publishTime` runs from `2026-01-05T00:30:00Z` to `2026-01-07T00:00:00Z`. There are 96 distinct values. On every row, `publishTime` is 30 minutes after `startTime`. Two of those rows cross midnight:

- `startTime` `2026-01-05T23:30:00Z`, `publishTime` `2026-01-06T00:00:00Z`, `settlementPeriod` 48
- `startTime` `2026-01-06T23:30:00Z`, `publishTime` `2026-01-07T00:00:00Z`, `settlementPeriod` 48

`settlementDate` equals the date portion of `startTime` on all 96 rows. Within each date, `settlementPeriod` 1 is `00:00` and `settlementPeriod` 48 is `23:30`. Each clock time `HH:MM` maps to the same period on both dates. Each `startTime` has one `publishTime`.

In the file, both `startTime` and `publishTime` are in descending order.

### WINDFOR

`startTime` minutes are `00` on all 1168 rows. There are 97 distinct values, from `2026-01-04T21:00:00Z` to `2026-01-08T21:00:00Z`. Sorted, each step is 1 hour, with no larger gap.

`publishTime` minutes are `30` on all 1168 rows. There are 16 distinct values, from `2026-01-05T02:30:00Z` to `2026-01-06T22:30:00Z`. Sorted steps are 2, 3, or 4 hours. The clock times repeat on both dates: `02:30`, `04:30`, `07:30`, `09:30`, `11:30`, `15:30`, `18:30`, `22:30`.

WINDFOR does return several forecasts for the same `startTime`. All 97 `startTime` values have more than one `publishTime`:

- 49 `startTime` values have 16 distinct `publishTime` values. They are hourly from `2026-01-05T21:00:00Z` through `2026-01-07T21:00:00Z`.
- 48 `startTime` values have 8 distinct `publishTime` values, in two hourly blocks of 24: `2026-01-04T21:00:00Z` through `2026-01-05T20:00:00Z`, and `2026-01-07T22:00:00Z` through `2026-01-08T21:00:00Z`.

Each (`startTime`, `publishTime`) pair occurs once. For 91 of the 97 `startTime` values, `generation` is not the same on every `publishTime`. The other 6 `startTime` values keep one `generation` across their `publishTime` values.

Each `publishTime` has 73 rows and 73 distinct `startTime` values, spaced 1 hour apart. The eight `publishTime` values on 2026-01-05 cover `2026-01-04T21:00:00Z` through `2026-01-07T21:00:00Z`. The eight on 2026-01-06 cover `2026-01-05T21:00:00Z` through `2026-01-08T21:00:00Z`.

In the file, `publishTime` is descending. Inside one `publishTime`, `startTime` is ascending. The first block is `publishTime` `2026-01-06T22:30:00Z` with `startTime` from `2026-01-05T21:00:00Z` to `2026-01-08T21:00:00Z`.

## 3. Horizon

`horizon_hours = startTime - publishTime`. Both samples land on half-hour boundaries, so every horizon is a multiple of 0.5 hours.

### FUELHH

| | Hours |
| --- | --- |
| Min | -0.5 |
| Max | -0.5 |
| Median | -0.5 |

All 96 rows have horizon `-0.5`. Mean is also `-0.5`.

### WINDFOR

| | Hours |
| --- | --- |
| Min | -25.5 |
| Max | 66.5 |
| Median | 21.5 |

The two middle values of the 1168 sorted horizons are both 21.5, so the median is 21.5. The mean is also 21.5.

There is no single most common horizon. There are 93 distinct values. The highest frequency is 16 rows, shared by 53 of those values. The extreme values are rarer: `-25.5` and `66.5` each occur twice.

240 rows have a negative horizon (start before publish). 928 rows have a positive horizon. None are 0. The minimum row is `publishTime` `2026-01-06T22:30:00Z`, `startTime` `2026-01-05T21:00:00Z` (`-25.5` hours). The maximum row is `publishTime` `2026-01-06T02:30:00Z`, `startTime` `2026-01-08T21:00:00Z` (`66.5` hours).

Per `publishTime`, the 73 horizons are 1 hour apart. They are not the same set for every `publishTime`. For example, `2026-01-05T02:30:00Z` spans `-5.5` to `66.5`, while `2026-01-05T22:30:00Z` spans `-25.5` to `46.5`.

## 4. Data quality

Checked on these files only.

- No `null` values in either file.
- No missing keys. FUELHH has one key set of seven fields. WINDFOR has one key set of four fields. No object has an extra field relative to the others in its file.
- No exact duplicate objects.
- No duplicate (`startTime`, `publishTime`) pairs. FUELHH also has no duplicate `startTime`.
- No conflicting `generation` for the same (`startTime`, `publishTime`) pair.
- `fuelType` is only `"WIND"`. No other fuel type appears in this FUELHH file.
- `generation` has no nulls, zeros, negatives, or fractional literals.
- FUELHH `startTime` has no gap larger than 0.5 hours between its first and last value. Both settlement dates have periods 1 through 48 with none missing.
- WINDFOR distinct `startTime` values have no gap larger than 1 hour between the first and last value.
- WINDFOR coverage is uneven: `startTime` values have either 8 or 16 `publishTime` values, as listed in section 2. Distinct `publishTime` values are not evenly spaced.
- 240 WINDFOR rows have `startTime` earlier than `publishTime`.

## 5. Open questions

The samples do not say:

- What `startTime`, `publishTime`, `settlementDate`, `settlementPeriod`, `dataset`, or `generation` mean, or the unit of `generation`.
- Whether the trailing `Z` means UTC, or how these strings should be shown in `Europe/London`.
- Whether the FUELHH `publishTime` (always 30 minutes after `startTime`) is a publication timestamp or something else.
- Whether other `fuelType` values exist. This file was requested with `fuelType=WIND`, so it cannot show them.
- Whether other responses include more fields, nulls, or non-integer `generation`.
- Whether the file order is guaranteed.
- Whether the 2/3/4-hour gaps between WINDFOR `publishTime` values are missing rows or the full set returned for this request.
- Whether 73 `startTime` values per `publishTime` is the full forecast for that publication. The request filtered publish time only.
- Why 6 `startTime` values keep the same `generation` across every `publishTime`, while 91 change.
- Whether a negative horizon should be kept, dropped, or flagged. Both signs are present in WINDFOR.
- How much of January 2026 is outside these files. FUELHH here covers two `settlementDate` values. WINDFOR `publishTime` values fall on 2026-01-05 and 2026-01-06 only, while its `startTime` values run from 2026-01-04 through 2026-01-08.
