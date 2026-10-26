# Findings

January 2026 decision forecasts are high on most hours and most days. The bias is about +1,852 MW over 744 pairs. 631 of those 744 hours are over-forecasts, 27 of 31 days are positive, and sum(forecast) / sum(actual) is 1.160. The bias is positive in every actual-wind quintile and in every horizon bucket. Five days, 28, 12, 11, 1, and 21 January, account for about 40% of the net error. The cause is not known.

## Actual-wind quintiles

Five equal-count buckets of actual wind. Bias is forecast minus actual.

| Quintile | n | Actual range MW | Mean actual MW | MAE MW | Bias MW |
| --- | --- | --- | --- | --- | --- |
| Q1 | 149 | 1,728–7,767 | 5,389.8 | 2,055.2 | +1,827.4 |
| Q2 | 149 | 7,777–10,314 | 8,916.8 | 1,595.3 | +993.3 |
| Q3 | 148 | 10,351–14,106 | 12,223.4 | 1,886.5 | +1,447.1 |
| Q4 | 149 | 14,123–15,585 | 14,895.1 | 2,854.1 | +2,824.2 |
| Q5 | 149 | 15,590–17,805 | 16,484.8 | 2,244.7 | +2,163.0 |

## Daily bias

Decision-forecast bias by delivery day, highest first. Every listed day is in January 2026.

| Day | Bias MW |
| --- | --- |
| 28 Jan | +5,329.0 |
| 12 Jan | +4,875.4 |
| 11 Jan | +4,853.0 |
| 01 Jan | +4,223.2 |
| 21 Jan | +3,677.1 |
| 27 Jan | +3,418.6 |
| 02 Jan | +3,070.4 |
| 22 Jan | +2,646.8 |
| 31 Jan | +2,315.1 |
| 03 Jan | +2,098.5 |
| 26 Jan | +2,070.8 |
| 24 Jan | +1,947.0 |
| 06 Jan | +1,938.1 |
| 29 Jan | +1,799.9 |
| 25 Jan | +1,794.5 |
| 17 Jan | +1,659.4 |
| 18 Jan | +1,594.5 |
| 23 Jan | +1,541.5 |
| 30 Jan | +1,393.4 |
| 07 Jan | +1,371.9 |
| 04 Jan | +1,102.5 |
| 15 Jan | +1,025.2 |
| 08 Jan | +876.0 |
| 09 Jan | +816.4 |
| 20 Jan | +414.8 |
| 16 Jan | +348.8 |
| 13 Jan | +110.2 |
| 14 Jan | −10.5 |
| 10 Jan | −105.3 |
| 05 Jan | −115.3 |
| 19 Jan | −683.6 |

## Horizon

All forecast vintages.

| Horizon | n | Bias MW |
| --- | --- | --- |
| [0, 6) h | 1,488 | +1,548.2 |
| [6, 12) h | 1,488 | +1,616.1 |
| [12, 24) h | 2,976 | +1,811.2 |
| [24, 36) h | 2,976 | +1,838.5 |
| [36, 48] h | 2,945 | +2,004.5 |
| < 0 h | 3,721 | +1,749.8 |
| > 48 h | 2,510 | +1,479.6 |

## Sign split

| Group | Pairs | Sum of error MW |
| --- | --- | --- |
| Forecast ≥ actual | 631 | +1,480,192 |
| Forecast < actual | 113 | −102,655 |
| Net | 744 | +1,377,537 |

sum(forecast) / sum(actual) = 9,993,885 / 8,616,348 = 1.160.

## Ruled out

- **Alignment.** Shifting the forecast by 60 minutes either way does not change the positive bias.
- **Units and slot length.** The bias is the mean MW difference on paired hours. Treating an hourly slot as 1.0 h or 0.5 h changes MWh totals only.
- **Horizon.** The bias is positive in every horizon bucket, from +1,548.2 MW at 0–6 h to +2,004.5 MW at 36–48 h, and it is also positive below 0 h and above 48 h.
- **Curtailment alone.** The bias is positive in all five actual-wind quintiles, from +993.3 MW to +2,824.2 MW, so it is not limited to the highest-wind hours.

## Unknown / to verify

These are open checks, not a stated cause. `docs/DATA_NOTES.md` records that the samples do not define `generation`.

- What `generation` means in FUELHH, and what it means in WINDFOR, including whether the two fields are the same quantity.
- Whether FUELHH wind and WINDFOR cover the same generators.
- Whether any January hours or publications are missing from the snapshot.
