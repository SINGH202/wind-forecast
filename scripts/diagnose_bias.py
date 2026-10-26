"""Describe where the January decision-forecast bias sits.

Uses pandas and the parquet snapshot only. It does not import the application
and it does not change any service.

    backend/.venv/bin/python scripts/diagnose_bias.py
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
JANUARY_START = date(2026, 1, 1)
JANUARY_END = date(2026, 1, 31)
SAMPLE_DAYS = (date(2026, 1, 5), date(2026, 1, 15), date(2026, 1, 28))
SHIFTS_MINUTES = (-60, -30, 0, 30, 60)
PAIRS_PER_DAY = 6
QUINTILES = 5
HORIZON_EDGES = (0, 6, 12, 24, 36, 48)
EXTREME_DAYS = 5


def main() -> None:
    """Print the shift table, sample pairs, and the five January breakdowns."""
    actuals, forecasts = _load_snapshot(DATA_DIR)
    decision = _with_error(_january_decision(forecasts, actuals))
    _print_shifts(decision, actuals)
    _print_sample_pairs(decision)
    _print_quintiles(decision)
    _print_days(decision)
    _print_horizons(_all_vintages(forecasts, actuals))
    _print_sign_split(decision)
    _print_ratio(decision)


def _load_snapshot(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    actual_path = data_dir / "actuals.parquet"
    forecast_path = data_dir / "forecasts.parquet"
    if not actual_path.is_file() or not forecast_path.is_file():
        message = f"missing parquet snapshot in {data_dir}"
        raise SystemExit(message)
    actuals = pd.read_parquet(actual_path)
    forecasts = pd.read_parquet(forecast_path)
    for frame, columns in (
        (actuals, ("start_time_utc",)),
        (forecasts, ("start_time_utc", "publish_time_utc")),
    ):
        for column in columns:
            frame[column] = pd.to_datetime(frame[column], utc=True)
    return actuals, forecasts


def _january_decision(forecasts: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Decision forecast for every January delivery day, paired at shift 0."""
    day = JANUARY_START
    pieces: list[pd.DataFrame] = []
    while day <= JANUARY_END:
        pieces.append(_decision_forecast(forecasts, day))
        day += timedelta(days=1)
    selected = pd.concat(pieces, ignore_index=True)
    paired = selected.merge(
        actuals[["start_time_utc", "actual_mw"]],
        on="start_time_utc",
        how="left",
    )
    return paired.dropna(subset=["forecast_mw", "actual_mw"]).reset_index(drop=True)


def _score(decision: pd.DataFrame, actuals: pd.DataFrame, minutes: int) -> dict[str, float]:
    """MAE and bias after moving each forecast start by ``minutes``.

    Error stays forecast minus actual. A pair is kept only when an actual
    exists at the shifted time.
    """
    shifted = decision[["start_time_utc", "forecast_mw"]].copy()
    shifted["start_time_utc"] = shifted["start_time_utc"] + pd.Timedelta(minutes=minutes)
    paired = shifted.merge(
        actuals[["start_time_utc", "actual_mw"]],
        on="start_time_utc",
        how="inner",
    )
    error = paired["forecast_mw"] - paired["actual_mw"]
    return {
        "n": float(len(paired)),
        "mae": float(error.abs().mean()),
        "bias": float(error.mean()),
    }


def _hourly_pairs(decision: pd.DataFrame, delivery_day: date) -> pd.DataFrame:
    """Shift-0 pairs on one delivery day, in UTC start order."""
    local = decision["start_time_utc"].dt.tz_convert("Europe/London")
    day_rows = decision.loc[local.dt.date == delivery_day]
    return day_rows.sort_values("start_time_utc")


def _print_shifts(decision: pd.DataFrame, actuals: pd.DataFrame) -> None:
    print("shift_min  n    mae_mw    bias_mw")
    for minutes in SHIFTS_MINUTES:
        scored = _score(decision, actuals, minutes)
        print(
            f"{minutes:9d}  {int(scored['n']):3d}  {scored['mae']:8.2f}  {scored['bias']:8.2f}"
        )
    print()


def _print_sample_pairs(decision: pd.DataFrame) -> None:
    for delivery_day in SAMPLE_DAYS:
        print(f"{delivery_day.isoformat()}  utc_start  forecast_mw  actual_mw")
        pairs = _hourly_pairs(decision, delivery_day).head(PAIRS_PER_DAY)
        for row in pairs.itertuples(index=False):
            print(
                f"  {_iso_z(row.start_time_utc)}  {row.forecast_mw:11.0f}  {row.actual_mw:9.0f}"
            )
        print()


def _print_quintiles(decision: pd.DataFrame) -> None:
    """Five equal-count buckets of actual MW, lowest actual first."""
    ranked = decision["actual_mw"].rank(method="first")
    labels = [f"Q{index}" for index in range(1, QUINTILES + 1)]
    quintile = pd.qcut(ranked, QUINTILES, labels=labels)
    print("actual wind quintile  n  actual_min  actual_max  mean_actual_mw   mae_mw   bias_mw")
    for label in labels:
        rows = decision.loc[quintile == label]
        error = rows["error_mw"]
        print(
            f"{label:<20}  {len(rows):3d}  {rows['actual_mw'].min():10.1f}  "
            f"{rows['actual_mw'].max():10.1f}  {rows['actual_mw'].mean():14.1f}  "
            f"{error.abs().mean():7.1f}  {error.mean():8.1f}"
        )
    print()


def _print_days(decision: pd.DataFrame) -> None:
    """One bias per London delivery day, highest bias first."""
    frame = decision.copy()
    frame["delivery_day"] = frame["start_time_utc"].dt.tz_convert("Europe/London").dt.date
    grouped = frame.groupby("delivery_day", sort=False)["error_mw"]
    days = pd.DataFrame({"n": grouped.size(), "bias_mw": grouped.mean()}).reset_index()
    days = days.sort_values("bias_mw", ascending=False).reset_index(drop=True)
    print("delivery_day  n   bias_mw")
    for row in days.itertuples(index=False):
        print(f"{row.delivery_day.isoformat()}     {int(row.n):2d}  {row.bias_mw:8.1f}")
    print()
    print(f"{EXTREME_DAYS} highest bias days")
    _print_day_slice(days.head(EXTREME_DAYS))
    print(f"{EXTREME_DAYS} lowest bias days")
    _print_day_slice(days.tail(EXTREME_DAYS).sort_values("bias_mw"))
    print()


def _print_day_slice(days: pd.DataFrame) -> None:
    for row in days.itertuples(index=False):
        print(f"  {row.delivery_day.isoformat()}  {row.bias_mw:8.1f}")


def _print_horizons(paired: pd.DataFrame) -> None:
    """Bias of every January vintage in the requested horizon buckets."""
    edges = list(HORIZON_EDGES)
    labels = [f"[{edges[index]},{edges[index + 1]})" for index in range(len(edges) - 1)]
    labels[-1] = f"[{edges[-2]},{edges[-1]}]"
    bucket = pd.cut(
        paired["horizon_hours"],
        bins=[*edges[:-1], edges[-1] + 1e-9],
        right=False,
        labels=labels,
    )
    print("horizon_h   n   bias_mw")
    for label in labels:
        rows = paired.loc[bucket == label, "error_mw"]
        bias = float("nan") if rows.empty else float(rows.mean())
        print(f"{label:<10}  {len(rows):5d}  {bias:8.1f}")
    below = paired.loc[paired["horizon_hours"] < 0, "error_mw"]
    above = paired.loc[paired["horizon_hours"] > HORIZON_EDGES[-1], "error_mw"]
    for label, rows in (("<0", below), (">48", above)):
        bias = float("nan") if rows.empty else float(rows.mean())
        print(f"{label:<10}  {len(rows):5d}  {bias:8.1f}")
    print()


def _print_sign_split(decision: pd.DataFrame) -> None:
    """Counts and error sums for forecast >= actual and forecast < actual."""
    error = decision["error_mw"]
    net = float(error.sum())
    positive = float(error.loc[error > 0].sum())
    groups = (
        ("forecast >= actual", decision.loc[decision["forecast_mw"] >= decision["actual_mw"]]),
        ("forecast < actual", decision.loc[decision["forecast_mw"] < decision["actual_mw"]]),
    )
    print("group                n   error_sum_mw  share_of_net  share_of_positive_error_sum")
    for name, rows in groups:
        total = float(rows["error_mw"].sum())
        net_share = total / net if net != 0 else float("nan")
        positive_share = total / positive if positive != 0 and total > 0 else 0.0
        if name.startswith("forecast <"):
            positive_share = 0.0
        print(
            f"{name:<20}  {len(rows):3d}  {total:12.1f}  {net_share:12.3f}  {positive_share:12.3f}"
        )
    print(f"{'all':<20}  {len(decision):3d}  {net:12.1f}")
    print(f"positive_error_sum_mw  {positive:.1f}")
    print()


def _print_ratio(decision: pd.DataFrame) -> None:
    forecast_sum = float(decision["forecast_mw"].sum())
    actual_sum = float(decision["actual_mw"].sum())
    ratio = forecast_sum / actual_sum if actual_sum != 0 else float("nan")
    print("sum_forecast_mw  sum_actual_mw  sum_forecast_over_sum_actual")
    print(f"{forecast_sum:15.1f}  {actual_sum:13.1f}  {ratio:.4f}")
    print()


def _with_error(paired: pd.DataFrame) -> pd.DataFrame:
    out = paired.copy()
    out["error_mw"] = out["forecast_mw"] - out["actual_mw"]
    return out


def _all_vintages(forecasts: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Every WINDFOR row for a January start time that has an actual."""
    vintage = forecasts.copy()
    vintage["horizon_hours"] = (
        vintage["start_time_utc"] - vintage["publish_time_utc"]
    ).dt.total_seconds() / 3600
    paired = vintage.merge(
        actuals[["start_time_utc", "actual_mw"]],
        on="start_time_utc",
        how="inner",
    )
    local_day = paired["start_time_utc"].dt.tz_convert("Europe/London").dt.date
    january = (local_day >= JANUARY_START) & (local_day <= JANUARY_END)
    return _with_error(paired.loc[january].reset_index(drop=True))


def _decision_forecast(forecasts: pd.DataFrame, delivery_day: date) -> pd.DataFrame:
    """One row per London half-hour. The chosen publish is the latest at or before 09:00."""
    cutoff = _cutoff_utc(delivery_day)
    grid = pd.DataFrame({"start_time_utc": _london_half_hours(delivery_day)})
    eligible = forecasts.loc[forecasts["publish_time_utc"] <= cutoff]
    if eligible.empty:
        chosen = forecasts.iloc[0:0]
    else:
        latest_index = eligible.groupby("start_time_utc")["publish_time_utc"].idxmax()
        chosen = eligible.loc[latest_index]
    return grid.merge(chosen, on="start_time_utc", how="left")


def _cutoff_utc(delivery_day: date) -> pd.Timestamp:
    """09:00 Europe/London on the day before delivery, as UTC."""
    previous = delivery_day - timedelta(days=1)
    local = pd.Timestamp(
        year=previous.year,
        month=previous.month,
        day=previous.day,
        hour=9,
        minute=0,
        tz="Europe/London",
    )
    return local.tz_convert("UTC")


def _london_half_hours(delivery_day: date) -> pd.DatetimeIndex:
    """Midnight through 23:30 Europe/London, expressed in UTC."""
    midnight = pd.Timestamp(
        year=delivery_day.year,
        month=delivery_day.month,
        day=delivery_day.day,
        tz="Europe/London",
    )
    return pd.date_range(midnight, periods=48, freq="30min").tz_convert("UTC")


def _iso_z(value: pd.Timestamp) -> str:
    return value.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    main()
