"""Independent check of the decision forecast and January error scores.

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
JANUARY_START = date(2026, 1, 1)
JANUARY_END = date(2026, 1, 31)
CUTOFF_HHMM = (9, 0)


def main() -> int:
    """Recompute the figures and compare them with the running API."""
    actuals, forecasts = _load_snapshot(DATA_DIR)
    failures = 0
    for delivery_day in CHECK_DAYS:
        failures += _check_decision_day(actuals, forecasts, delivery_day)
    failures += _check_january_scores(actuals, forecasts)
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
    return int(not forecast_ok) + int(not publish_ok)


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
        print("FAIL january mae api_request")
        print("FAIL january rmse api_request")
        print("FAIL january bias api_request")
        return 3
    failures = 0
    for name, api_key in (("mae", "mae_mw"), ("rmse", "rmse_mw"), ("bias", "bias_mw")):
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


def _january_scores(forecasts: pd.DataFrame, actuals: pd.DataFrame) -> dict[str, float | None]:
    """MAE, RMSE, and bias of every January decision forecast that has an actual."""
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
        return {"mae": None, "rmse": None, "bias": None}
    # Rule: error = forecast - actual. A positive value is an over-forecast.
    error = usable["forecast_mw"] - usable["actual_mw"]
    return {
        "mae": float(error.abs().mean()),
        "rmse": float((error.pow(2).mean()) ** 0.5),
        "bias": float(error.mean()),
    }


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
