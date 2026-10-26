# 2 January through 1 February 2026: the half-hour grid assumes no DST change.
"""Independent check of the decision forecast and the numbers the buyer acts on.

Uses pandas and the parquet snapshot only. It does not import the application,
so a passing result is not a check of the service functions against themselves.

Run from the repo with the API already serving the same snapshot:

    backend/.venv/bin/python scripts/verify.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

API_BASE = "http://localhost:8000"
TOLERANCE = 1e-6
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CHECK_DAYS = (date(2026, 1, 5), date(2026, 1, 15), date(2026, 1, 28))
JANUARY_START = date(2026, 1, 2)
JANUARY_END = date(2026, 2, 1)
CUTOFF_HHMM = (9, 0)
MIN_HISTORY_DAYS = 3
EXPECTED_JANUARY_PAIRS = 744
LEAK_DAY = date(2026, 1, 15)
LEAK_LATER_DAY = date(2026, 1, 16)
LEAK_MW = 1000.0


def main() -> int:
    """Recompute the figures and compare them with the running API."""
    actuals, forecasts = _load_snapshot(DATA_DIR)
    failures = 0
    for delivery_day in CHECK_DAYS:
        failures += _check_decision_day(actuals, forecasts, delivery_day)
    failures += _check_january_scores(actuals, forecasts)
    failures += _check_no_future_leak(actuals, forecasts)
    if failures:
        print(f"{failures} check(s) FAILED")
        return 1
    print("all checks PASS")
    return 0


def _load_snapshot(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    actual_path = data_dir / "actuals.parquet"
    forecast_path = data_dir / "forecasts.parquet"
    if not actual_path.is_file() or not forecast_path.is_file():
        message = f"missing parquet snapshot in {data_dir}"
        raise SystemExit(message)
    actuals = pd.read_parquet(actual_path)
    forecasts = pd.read_parquet(forecast_path)
    # Rule: timestamps in the snapshot are UTC. A naive value is labelled UTC, not London.
    for frame, columns in (
        (actuals, ("start_time_utc",)),
        (forecasts, ("start_time_utc", "publish_time_utc")),
    ):
        for column in columns:
            frame[column] = pd.to_datetime(frame[column], utc=True)
    return actuals, forecasts


def _check_decision_day(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    delivery_day: date,
) -> int:
    """Compare one day's decision forecast, slot by slot, with GET /api/decision."""
    independent = _decision_forecast(forecasts, delivery_day)
    payload = _get_json("/api/decision", {"delivery_day": delivery_day.isoformat(), "cutoff": "09:00"})
    if payload is None:
        print(f"FAIL decision {delivery_day.isoformat()} api_request")
        return 1
    api_points = {point["start_time"]: point for point in payload["points"]}
    own_points = {
        _iso_z(row.start_time_utc): row
        for row in independent.itertuples(index=False)
    }
    forecast_diffs: list[tuple[str, float]] = []
    publish_mismatches: list[str] = []
    missing_mismatches: list[str] = []
    for start in sorted(set(api_points) | set(own_points)):
        api_point = api_points.get(start)
        own = own_points.get(start)
        api_mw = None if api_point is None else api_point["forecast_mw"]
        own_mw = None if own is None or pd.isna(own.forecast_mw) else float(own.forecast_mw)
        difference = _abs_diff(own_mw, api_mw)
        if difference is None:
            missing_mismatches.append(f"  {start} independent={own_mw} api={api_mw}")
        elif difference > TOLERANCE:
            forecast_diffs.append((start, difference))
        api_publish = None if api_point is None else api_point["publish_time"]
        own_publish = None if own is None else _iso_z(own.publish_time_utc)
        if api_publish != own_publish:
            publish_mismatches.append(f"  {start} independent={own_publish} api={api_publish}")
    max_diff = max((diff for _, diff in forecast_diffs), default=0.0)
    forecast_ok = not forecast_diffs and not missing_mismatches
    _print_check(
        forecast_ok,
        f"decision {delivery_day.isoformat()} forecast_mw",
        f"max_abs_diff={max_diff:.6e}",
    )
    if not forecast_ok:
        for start, difference in forecast_diffs:
            api_mw = api_points[start]["forecast_mw"]
            own_mw = float(own_points[start].forecast_mw)
            print(f"  {start} independent={own_mw} api={api_mw} abs_diff={difference:.6e}")
        for line in missing_mismatches:
            print(line)
    publish_ok = not publish_mismatches
    _print_check(
        publish_ok,
        f"decision {delivery_day.isoformat()} publish_time",
        f"mismatches={len(publish_mismatches)}",
    )
    for line in publish_mismatches:
        print(line)
    return int(not forecast_ok) + int(not publish_ok) + _check_buyer_numbers(
        independent, actuals, forecasts, delivery_day, payload
    )


def _check_january_scores(actuals: pd.DataFrame, forecasts: pd.DataFrame) -> int:
    """Compare January MAE, RMSE, and bias with GET /api/metrics."""
    scores = _january_scores(forecasts, actuals)
    payload = _get_json(
        "/api/metrics",
        {
            "start_day": JANUARY_START.isoformat(),
            "end_day": JANUARY_END.isoformat(),
            "cutoff": "09:00",
        },
    )
    if payload is None:
        for name in ("mae", "rmse", "bias", "n", "p10_error_mw", "p90_error_mw"):
            print(f"FAIL january {name} api_request")
        return 6
    failures = 0
    n_ok = scores["n"] == EXPECTED_JANUARY_PAIRS and payload["n"] == EXPECTED_JANUARY_PAIRS
    _print_check(
        n_ok,
        "january n",
        f"independent={scores['n']} api={payload['n']} expected={EXPECTED_JANUARY_PAIRS}",
    )
    failures += int(not n_ok)
    for name, api_key in (
        ("mae", "mae_mw"),
        ("rmse", "rmse_mw"),
        ("bias", "bias_mw"),
        ("p10_error_mw", "p10_error_mw"),
        ("p90_error_mw", "p90_error_mw"),
    ):
        difference = _abs_diff(scores[name], payload[api_key])
        ok = difference is not None and difference <= TOLERANCE
        shown = "missing" if difference is None else f"{difference:.6e}"
        _print_check(
            ok,
            f"january {name}",
            f"abs_diff={shown} independent={scores[name]} api={payload[api_key]}",
        )
        failures += int(not ok)
    return failures


def _decision_forecast(forecasts: pd.DataFrame, delivery_day: date) -> pd.DataFrame:
    """One row per London half-hour, using idxmax rather than a sort-and-tail."""
    cutoff = _cutoff_utc(delivery_day)
    # Rule: keep all 48 half-hours of delivery day D, including slots with no forecast.
    grid = pd.DataFrame({"start_time_utc": _london_half_hours(delivery_day)})
    # Rule: never use a forecast published after the D-1 cutoff.
    eligible = forecasts.loc[forecasts["publish_time_utc"] <= cutoff]
    if eligible.empty:
        chosen = forecasts.iloc[0:0]
    else:
        # Rule: the decision forecast is the maximum publish time still at or before the cutoff.
        latest_index = eligible.groupby("start_time_utc")["publish_time_utc"].idxmax()
        chosen = eligible.loc[latest_index]
    return grid.merge(chosen, on="start_time_utc", how="left")


def _january_scores(forecasts: pd.DataFrame, actuals: pd.DataFrame) -> dict[str, float | int | None]:
    """MAE, RMSE, bias, and error quantiles of every January decision pair."""
    day = JANUARY_START
    pieces: list[pd.DataFrame] = []
    while day <= JANUARY_END:
        # Rule: each delivery day uses its own D-1 09:00 London cutoff.
        pieces.append(_decision_forecast(forecasts, day))
        day += timedelta(days=1)
    selected = pd.concat(pieces, ignore_index=True)
    # Rule: pair a forecast with the actual on the same start time. Do not fill gaps.
    paired = selected.merge(actuals[["start_time_utc", "actual_mw"]], on="start_time_utc", how="left")
    # Rule: a missing forecast or a missing actual is excluded, not scored as zero.
    usable = paired.dropna(subset=["forecast_mw", "actual_mw"])
    if usable.empty:
        return {
            "n": 0,
            "mae": None,
            "rmse": None,
            "bias": None,
            "p10_error_mw": None,
            "p90_error_mw": None,
        }
    # Rule: error = forecast - actual. A positive value is an over-forecast.
    error = usable["forecast_mw"] - usable["actual_mw"]
    quantiles = error.quantile([0.10, 0.90], interpolation="linear")
    return {
        "n": len(usable),
        "mae": float(error.abs().mean()),
        "rmse": float((error.pow(2).mean()) ** 0.5),
        "bias": float(error.mean()),
        "p10_error_mw": float(quantiles.iloc[0]),
        "p90_error_mw": float(quantiles.iloc[1]),
    }


def _check_buyer_numbers(
    independent: pd.DataFrame,
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    delivery_day: date,
    payload: dict,
) -> int:
    """Compare history quantiles, day energy, and the firm-wind band with one decision response."""
    label = delivery_day.isoformat()
    p10, p90 = _history_quantiles(forecasts, actuals, delivery_day)
    sample = payload["error_sample"]
    kpis = payload["kpis"]
    hours = _slot_hours(independent)
    firm = _firm_mw(independent["forecast_mw"], p10, p90)
    failures = _compare_value(f"decision {label} p10_error_mw", p10, sample["p10_error_mw"])
    failures += _compare_value(f"decision {label} p90_error_mw", p90, sample["p90_error_mw"])
    failures += _compare_value(
        f"decision {label} expected_mwh",
        _energy(independent["forecast_mw"], hours),
        kpis["expected_mwh"],
    )
    failures += _compare_value(
        f"decision {label} firm_wind_mwh",
        _energy(firm, hours),
        kpis["firm_wind_mwh"],
    )
    failures += _compare_band(label, independent, p10, p90, payload["points"])
    return failures


def _check_no_future_leak(actuals: pd.DataFrame, forecasts: pd.DataFrame) -> int:
    """P10 and P90 for 15 Jan must ignore a 1,000 MW bump on every 16 Jan forecast."""
    base = _history_quantiles(forecasts, actuals, LEAK_DAY)
    bumped = forecasts.copy()
    local_day = bumped["start_time_utc"].dt.tz_convert("Europe/London").dt.date
    on_later_day = local_day == LEAK_LATER_DAY
    bumped.loc[on_later_day, "forecast_mw"] = bumped.loc[on_later_day, "forecast_mw"] + LEAK_MW
    leaked = _history_quantiles(bumped, actuals, LEAK_DAY)
    failures = 0
    for name, before, after in (
        ("p10_error_mw", base[0], leaked[0]),
        ("p90_error_mw", base[1], leaked[1]),
    ):
        difference = _abs_diff(before, after)
        ok = difference == 0.0
        shown = "missing" if difference is None else f"{difference:.6e}"
        _print_check(
            ok,
            f"leakage {LEAK_DAY.isoformat()} {name}",
            f"abs_diff={shown} unmodified={before} bumped_16_jan={after}",
        )
        failures += int(not ok)
    return failures


def _history_quantiles(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    before_day: date,
) -> tuple[float | None, float | None]:
    """P10 and P90 of decision-forecast errors on days strictly before ``before_day``.

    Late December counts when it is before the selected day. A day counts only
    when it has at least one paired error. Fewer than three such days means no band.
    """
    errors, days_used = _prior_errors(forecasts, actuals, before_day)
    if days_used < MIN_HISTORY_DAYS or not errors:
        return None, None
    values = pd.Series(errors, dtype="float64").quantile([0.10, 0.90], interpolation="linear")
    return float(values.iloc[0]), float(values.iloc[1])


def _prior_errors(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    before_day: date,
) -> tuple[list[float], int]:
    local_days = forecasts["start_time_utc"].dt.tz_convert("Europe/London").dt.date
    candidate_days = sorted({day for day in local_days if day < before_day})
    errors: list[float] = []
    days_used = 0
    for day in candidate_days:
        paired = _paired_errors(forecasts, actuals, day)
        if paired.empty:
            continue
        days_used += 1
        errors.extend(float(value) for value in paired.tolist())
    return errors, days_used


def _paired_errors(forecasts: pd.DataFrame, actuals: pd.DataFrame, delivery_day: date) -> pd.Series:
    selected = _decision_forecast(forecasts, delivery_day)
    paired = selected.merge(
        actuals[["start_time_utc", "actual_mw"]],
        on="start_time_utc",
        how="left",
    )
    usable = paired.dropna(subset=["forecast_mw", "actual_mw"])
    return usable["forecast_mw"] - usable["actual_mw"]


def _slot_hours(frame: pd.DataFrame) -> float:
    """Shortest gap between forecast start times. Hourly WINDFOR is 1.0 h."""
    present = frame.loc[frame["forecast_mw"].notna(), "start_time_utc"].dropna().sort_values()
    if len(present) >= 2:
        gaps = present.diff().dt.total_seconds().dropna() / 3600
        positive = gaps[gaps > 0]
        if not positive.empty:
            return float(positive.min())
    if len(present) == 1 and pd.Timestamp(present.iloc[0]).minute == 30:
        return 0.5
    return 1.0


def _firm_mw(forecast_mw: pd.Series, p10: float | None, p90: float | None) -> pd.Series:
    """Firm wind per slot is max(0, forecast - P90 error). Missing forecasts stay missing."""
    if p10 is None or p90 is None:
        return pd.Series(pd.NA, index=forecast_mw.index, dtype="Float64")
    return (forecast_mw - p90).clip(lower=0)


def _energy(values: pd.Series, slot_hours: float) -> float | None:
    present = values.dropna()
    if present.empty:
        return None
    return float((present * slot_hours).sum())


def _band_edges(
    forecast_mw: float | None,
    p10: float | None,
    p90: float | None,
) -> tuple[float | None, float | None]:
    if forecast_mw is None or p10 is None or p90 is None:
        return None, None
    return max(0.0, forecast_mw - p90), forecast_mw - p10


def _compare_band(
    label: str,
    frame: pd.DataFrame,
    p10: float | None,
    p90: float | None,
    points: list[dict],
) -> int:
    api_points = {point["start_time"]: point for point in points}
    mismatches = {"band_low_mw": [], "band_high_mw": []}
    missing_slots: list[str | None] = []
    for row in frame.itertuples(index=False):
        start = _iso_z(row.start_time_utc)
        forecast = None if pd.isna(row.forecast_mw) else float(row.forecast_mw)
        own_low, own_high = _band_edges(forecast, p10, p90)
        api_point = api_points.get(start)
        if api_point is None:
            missing_slots.append(start)
            continue
        for name, own, api_value in (
            ("band_low_mw", own_low, api_point["band_low_mw"]),
            ("band_high_mw", own_high, api_point["band_high_mw"]),
        ):
            difference = _abs_diff(own, api_value)
            if difference is None or difference > TOLERANCE:
                mismatches[name].append((start, own, api_value, difference))
    failures = 0
    for name, rows in mismatches.items():
        ok = not rows and not missing_slots
        finite = [difference for _, _, _, difference in rows if difference is not None]
        max_diff = max(finite, default=0.0)
        _print_check(
            ok,
            f"decision {label} {name}",
            f"max_abs_diff={max_diff:.6e} mismatches={len(rows) + len(missing_slots)}",
        )
        failures += int(not ok)
        for start, own, api_value, difference in rows:
            shown = "missing" if difference is None else f"{difference:.6e}"
            print(f"  {start} independent={own} api={api_value} abs_diff={shown}")
    for start in missing_slots:
        print(f"  {start} missing from the API response")
    return failures


def _compare_value(name: str, independent: float | None, api_value: float | None) -> int:
    difference = _abs_diff(independent, api_value)
    ok = difference is not None and difference <= TOLERANCE
    shown = "missing" if difference is None else f"{difference:.6e}"
    _print_check(ok, name, f"abs_diff={shown} independent={independent} api={api_value}")
    return int(not ok)


def _cutoff_utc(delivery_day: date) -> pd.Timestamp:
    """09:00 Europe/London on the day before delivery, as UTC."""
    previous = delivery_day - timedelta(days=1)
    hour, minute = CUTOFF_HHMM
    # Rule: the cutoff clock is Europe/London on D-1, then converted to UTC.
    local = pd.Timestamp(
        year=previous.year,
        month=previous.month,
        day=previous.day,
        hour=hour,
        minute=minute,
        tz="Europe/London",
    )
    return local.tz_convert("UTC")


def _london_half_hours(delivery_day: date) -> pd.DatetimeIndex:
    """Midnight through 23:30 Europe/London, expressed in UTC."""
    # Rule: a delivery day is the 48 London half-hours, not a rolling 24 hours from UTC midnight.
    midnight = pd.Timestamp(
        year=delivery_day.year,
        month=delivery_day.month,
        day=delivery_day.day,
        tz="Europe/London",
    )
    return pd.date_range(midnight, periods=48, freq="30min").tz_convert("UTC")


def _get_json(path: str, params: dict[str, str]) -> dict | None:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{API_BASE}{path}?{query}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"  API {exc.code} {path}: {detail}")
        return None
    except urllib.error.URLError as exc:
        print(f"  API unreachable {path}: {exc.reason}")
        return None
    if not isinstance(payload, dict):
        print(f"  API {path} did not return an object")
        return None
    return payload


def _abs_diff(independent: float | None, api_value: float | None) -> float | None:
    """Absolute difference. None means one side is missing and the other is not."""
    if independent is None and api_value is None:
        return 0.0
    if independent is None or api_value is None:
        return None
    return abs(float(independent) - float(api_value))


def _iso_z(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    return stamp.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def _print_check(ok: bool, name: str, detail: str) -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name}  {detail}")


if __name__ == "__main__":
    sys.exit(main())
