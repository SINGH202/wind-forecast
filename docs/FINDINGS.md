# Findings

Delivery days are 2 January through 1 February 2026. The figures below are the output of `scripts/diagnose_bias.py` for that window, pasted unchanged. The cause is not known.

```
shift_min  n    mae_mw    bias_mw
      -60  744   1969.73   1731.90
      -30  744   1989.60   1736.08
        0  744   2022.47   1745.94
       30  744   2061.45   1749.84
       60  743   2100.14   1762.17

2026-01-05  utc_start  forecast_mw  actual_mw
  2026-01-05T00:00:00Z        12848      10601
  2026-01-05T01:00:00Z        12514      10727
  2026-01-05T02:00:00Z        12141      10259
  2026-01-05T03:00:00Z        12018      10460
  2026-01-05T04:00:00Z        11854      10494
  2026-01-05T05:00:00Z        11433      10374

2026-01-15  utc_start  forecast_mw  actual_mw
  2026-01-15T00:00:00Z        15834      14602
  2026-01-15T01:00:00Z        15478      14200
  2026-01-15T02:00:00Z        15066      14534
  2026-01-15T03:00:00Z        14655      14028
  2026-01-15T04:00:00Z        14497      13901
  2026-01-15T05:00:00Z        14419      13704

2026-01-28  utc_start  forecast_mw  actual_mw
  2026-01-28T00:00:00Z        15208      10825
  2026-01-28T01:00:00Z        14248       8926
  2026-01-28T02:00:00Z        13397       7799
  2026-01-28T03:00:00Z        12620       6649
  2026-01-28T04:00:00Z        11780       5570
  2026-01-28T05:00:00Z        10987       5416

actual wind quintile  n  actual_min  actual_max  mean_actual_mw   mae_mw   bias_mw
Q1                    149      1728.0      7492.0          5128.5   2038.7    1817.8
Q2                    149      7527.0      9825.0          8553.5   1534.3    1057.6
Q3                    148      9837.0     13727.0         11595.4   1636.9    1065.9
Q4                    149     13778.0     15477.0         14688.3   2742.8    2708.4
Q5                    149     15488.0     17805.0         16463.8   2157.1    2075.4

delivery_day  n   bias_mw
2026-01-28     24    5329.0
2026-01-12     24    4875.4
2026-01-11     24    4853.0
2026-01-21     24    3677.1
2026-01-27     24    3418.6
2026-01-02     24    3070.4
2026-01-22     24    2646.8
2026-01-31     24    2315.1
2026-01-03     24    2098.5
2026-01-26     24    2070.8
2026-01-24     24    1947.0
2026-01-06     24    1938.1
2026-01-29     24    1799.9
2026-01-25     24    1794.5
2026-01-17     24    1659.4
2026-01-18     24    1594.5
2026-01-23     24    1541.5
2026-01-30     24    1393.4
2026-01-07     24    1371.9
2026-01-04     24    1102.5
2026-01-15     24    1025.2
2026-02-01     24     950.0
2026-01-08     24     876.0
2026-01-09     24     816.4
2026-01-20     24     414.8
2026-01-16     24     348.8
2026-01-13     24     110.2
2026-01-14     24     -10.5
2026-01-10     24    -105.3
2026-01-05     24    -115.3
2026-01-19     24    -683.6

5 highest bias days
  2026-01-28    5329.0
  2026-01-12    4875.4
  2026-01-11    4853.0
  2026-01-21    3677.1
  2026-01-27    3418.6
5 lowest bias days
  2026-01-19    -683.6
  2026-01-05    -115.3
  2026-01-10    -105.3
  2026-01-14     -10.5
  2026-01-13     110.2

horizon_h   n   bias_mw
[0,6)        1488    1428.5
[6,12)       1488    1504.3
[12,24)      2976    1698.0
[24,36)      2976    1719.1
[36,48]      2945    1900.1
<0           3697    1652.1
>48          2510    1415.0

group                n   error_sum_mw  share_of_net  share_of_positive_error_sum
forecast >= actual    630     1401848.0         1.079         1.000
forecast < actual     114     -102870.0        -0.079         0.000
all                   744     1298978.0
positive_error_sum_mw  1401848.0

sum_forecast_mw  sum_actual_mw  sum_forecast_over_sum_actual
      9695395.0      8396417.0  1.1547
```

## Ruled out

- **Alignment.** At a shift of 0 the bias is 1745.94 MW. At −60 minutes it is 1731.90 MW and at +60 minutes it is 1762.17 MW.
- **Units and slot length.** The bias is the mean MW difference on paired hours. Treating an hourly slot as 1.0 h or 0.5 h changes MWh totals only.
- **Horizon.** The printed horizon biases are 1428.5 MW for [0,6), 1504.3 MW for [6,12), 1698.0 MW for [12,24), 1719.1 MW for [24,36), 1900.1 MW for [36,48], 1652.1 MW below 0 h, and 1415.0 MW above 48 h.
- **Curtailment alone.** Every actual-wind quintile is positive: 1817.8, 1057.6, 1065.9, 2708.4, and 2075.4 MW.

## Unknown / to verify

These are open checks, not a stated cause. `docs/DATA_NOTES.md` records that the samples do not define `generation`.

- What `generation` means in FUELHH, and what it means in WINDFOR, including whether the two fields are the same quantity.
- Whether FUELHH wind and WINDFOR cover the same generators.
- Whether any hours or publications are missing from the snapshot.
