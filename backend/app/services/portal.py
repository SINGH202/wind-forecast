"""Build API payloads from the loaded snapshot. Routes do not touch these frames."""

from datetime import date, timedelta
from typing import Any

import pandas as pd

from app.config import Settings
from app.constants import ASSUMPTIONS, CUTOFF_OPTIONS, HORIZON_EDGES, HORIZON_LABEL
from app.dataset import Dataset
from app.services.metrics import (
    error_histogram,
    error_quantiles,
    metrics_by_horizon_bucket,
    metrics_by_hour_of_day,
    metrics_by_wind_level_bucket,
    overall_metrics,
    worst_days,
)
from app.services.selection import (
    build_cutoff_utc,
    decision_forecast,
    horizon_forecast,
    join_with_actuals,
)
from app.services.uncertainty import (
    apply_band,
    day_kpis,
    historical_error_quantiles,
    prior_decision_errors,
)

MIN_HISTORY_DAYS = 3


def build_meta(dataset: Dataset, settings: Settings) -> dict[str, object]:
    """Coverage, the default cutoff, and the assumptions the numbers rely on."""
    return {
        "delivery_days": [day.isoformat() for day in dataset.delivery_days],
        "delivery_day_count": len(dataset.delivery_days),
        "min_start_time": _iso_z(dataset.min_start_time),
        "max_start_time": _iso_z(dataset.max_start_time),
        "default_cutoff": settings.decision_cutoff_time,
        "cutoff_options": list(CUTOFF_OPTIONS),
        "timezone": settings.timezone,
        "power_unit": "MW",
        "energy_unit": "MWh",
        "resolution_minutes": 30,
        "manifest": _manifest(dataset.manifest),
        "assumptions": list(ASSUMPTIONS),
    }


def build_decision(
    dataset: Dataset,
    delivery_day: date,
    cutoff: str,
    tz: str,
) -> dict[str, object]:
    """One delivery day at the decision cutoff, with the firm-wind band."""
    cutoff_utc = build_cutoff_utc(delivery_day, cutoff, tz)
    selected = decision_forecast(dataset.forecasts, delivery_day, cutoff, tz)
    selected["cutoff_utc"] = cutoff_utc
    joined = join_with_actuals(selected, dataset.actuals)
    history = prior_decision_errors(dataset.forecasts, dataset.actuals, delivery_day, cutoff, tz)
    quantiles = historical_error_quantiles(
        dataset.forecasts,
        dataset.actuals,
        delivery_day,
        cutoff,
        tz,
        qs=(0.10, 0.90),
        min_days=MIN_HISTORY_DAYS,
    )
    band_available = quantiles is not None
    banded = apply_band(
        joined,
        None if quantiles is None else quantiles[0.10],
        None if quantiles is None else quantiles[0.90],
    )
    kpis = day_kpis(banded)
    ages = kpis["forecast_age_hours"]
    age_min = ages["min"] if isinstance(ages, dict) else None
    return {
        "delivery_day": delivery_day.isoformat(),
        "cutoff_local": _london(cutoff_utc, tz),
        "cutoff_utc": _iso_z(cutoff_utc),
        "band_available": band_available,
        "band_reason": None if band_available else "insufficient history",
        "points": [
            _decision_point(row, cutoff_utc, tz) for row in banded.to_dict(orient="records")
        ],
        "kpis": {
            "expected_mwh": kpis["expected_mwh"],
            "firm_wind_mwh": kpis["firm_mwh"],
            "forecast_age_hours": None if age_min is None else round(float(age_min), 1),
            "half_hours_with_forecast": int(banded["has_forecast"].sum()),
            "half_hours_expected": 48,
        },
        "error_sample": {
            "n": len(history.values),
            "p10_error_mw": None if quantiles is None else quantiles[0.10],
            "p90_error_mw": None if quantiles is None else quantiles[0.90],
            "prior_days_used": history.prior_days_used,
        },
        "flags": _flags(banded, band_available),
    }


def build_series(
    dataset: Dataset,
    start: date,
    end: date,
    horizon_hours: int,
    tz: str,
) -> dict[str, object]:
    """Actuals against the horizon forecast. This view does not use the cutoff."""
    frames = [
        join_with_actuals(
            horizon_forecast(dataset.forecasts, day, horizon_hours, tz),
            dataset.actuals,
        )
        for day in _days(start, end)
    ]
    combined = pd.concat(frames, ignore_index=True)
    return {
        "start_day": start.isoformat(),
        "end_day": end.isoformat(),
        "horizon_hours": horizon_hours,
        "points": [_series_point(row, tz) for row in combined.to_dict(orient="records")],
    }


def build_metrics(
    dataset: Dataset,
    start: date,
    end: date,
    cutoff: str,
    tz: str,
) -> dict[str, object]:
    """Headline scores from the decision forecast, and horizon scores from every vintage."""
    decision_rows = []
    for day in _days(start, end):
        selected = decision_forecast(dataset.forecasts, day, cutoff, tz)
        decision_rows.append(join_with_actuals(selected, dataset.actuals))
    decision = pd.concat(decision_rows, ignore_index=True)
    headline = overall_metrics(decision)
    mean_actual = _mean_actual(decision)
    n = int(headline["n"])
    blank = n == 0 or mean_actual == 0
    quantiles = error_quantiles(decision, qs=(0.10, 0.90))
    return {
        "start_day": start.isoformat(),
        "end_day": end.isoformat(),
        "cutoff": cutoff,
        "n": n,
        "pairs_excluded_missing": int(headline["n_excluded"]),
        "mae_mw": None if blank else headline["mae"],
        "rmse_mw": None if blank else headline["rmse"],
        "bias_mw": None if blank else headline["bias"],
        "nmae": None if blank else headline["normalized_mae"],
        "mean_actual_mw": None if blank else mean_actual,
        "p10_error_mw": None if n == 0 else quantiles[0.10],
        "p90_error_mw": None if n == 0 else quantiles[0.90],
        "by_hour_london": [_hour_row(row) for row in metrics_by_hour_of_day(decision)],
        "by_wind_level": [_bucket_row(row) for row in metrics_by_wind_level_bucket(decision)],
        "histogram": error_histogram(decision),
        "worst_days": [_worst_row(row) for row in worst_days(decision)],
        "by_horizon": {
            "label": HORIZON_LABEL,
            "buckets": [
                _bucket_row(row)
                for row in metrics_by_horizon_bucket(_vintages(dataset, start, end), HORIZON_EDGES)
            ],
        },
    }


def _decision_point(row: dict[str, Any], cutoff_utc: pd.Timestamp, tz: str) -> dict[str, Any]:
    has_forecast = bool(row["has_forecast"])
    publish = row.get("publish_time_utc")
    age = None
    if has_forecast and publish is not None and not pd.isna(publish):
        age = (cutoff_utc - pd.Timestamp(publish)).total_seconds() / 3600
    return {
        "start_time": _iso_z(row["start_time_utc"]),
        "start_time_london": _london(row["start_time_utc"], tz),
        "forecast_mw": _num(row.get("forecast_mw")),
        "actual_mw": _num(row.get("actual_mw")),
        "firm_mw": _num(row.get("firm_mw")),
        "band_low_mw": _num(row.get("lower_mw")),
        "band_high_mw": _num(row.get("upper_mw")),
        "publish_time": None if not has_forecast else _iso_z(publish),
        "horizon_hours": None if not has_forecast else _num(row.get("horizon_hours")),
        "forecast_age_hours": age,
        "missing_forecast": not has_forecast,
        "missing_actual": bool(row["missing_actual"]),
    }


def _series_point(row: dict[str, Any], tz: str) -> dict[str, Any]:
    has_forecast = bool(row["has_forecast"])
    return {
        "start_time": _iso_z(row["start_time_utc"]),
        "start_time_london": _london(row["start_time_utc"], tz),
        "forecast_mw": None if not has_forecast else _num(row.get("forecast_mw")),
        "actual_mw": _num(row.get("actual_mw")),
        "publish_time": None if not has_forecast else _iso_z(row.get("publish_time_utc")),
        "horizon_hours": None if not has_forecast else _num(row.get("horizon_hours")),
        "missing_forecast": not has_forecast,
        "missing_actual": bool(row["missing_actual"]),
    }


def _hour_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "hour": int(row["hour"]),
        "n": int(row["n"]),
        "mae_mw": row["mae"],
        "bias_mw": row["bias"],
    }


def _bucket_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "bucket": str(row["label"]),
        "n": int(row["n"]),
        "mae_mw": row["mae"],
        "bias_mw": row["bias"],
    }


def _worst_row(row: dict[str, Any]) -> dict[str, Any]:
    day = row["date"]
    return {
        "delivery_day": day.isoformat() if isinstance(day, date) else str(day),
        "n": int(row["n"]),
        "mae_mw": row["mae"],
        "bias_mw": row["bias"],
    }


def _vintages(dataset: Dataset, start: date, end: date) -> pd.DataFrame:
    forecasts = dataset.forecasts
    if forecasts.empty:
        empty = forecasts.copy()
        empty["actual_mw"] = pd.Series(dtype="float64")
        empty["missing_actual"] = pd.Series(dtype="bool")
        empty["has_forecast"] = pd.Series(dtype="bool")
        return empty
    starts = forecasts["start_time_utc"].dt.tz_convert("UTC").dt.date
    chosen = forecasts.loc[(starts >= start) & (starts <= end)].copy()
    merged = chosen.merge(dataset.actuals, on="start_time_utc", how="left")
    merged["missing_actual"] = merged["actual_mw"].isna()
    merged["has_forecast"] = merged["forecast_mw"].notna()
    return merged


def _mean_actual(frame: pd.DataFrame) -> float | None:
    usable = frame.loc[
        frame["has_forecast"].fillna(False).astype(bool)
        & ~frame["missing_actual"].fillna(True).astype(bool)
        & frame["forecast_mw"].notna()
        & frame["actual_mw"].notna()
    ]
    if usable.empty:
        return None
    return float(usable["actual_mw"].mean())


def _flags(frame: pd.DataFrame, band_available: bool) -> list[str]:
    flags: list[str] = []
    if not band_available:
        flags.append("no_prior_days_for_band")
    if bool((~frame["has_forecast"]).any()):
        flags.append("missing_forecast_slots")
    if bool(frame["missing_actual"].any()):
        flags.append("missing_actual_slots")
    firm = frame["firm_mw"]
    if bool(firm.notna().any()) and bool((firm < 0).any()):
        flags.append("negative_firm_wind")
    return flags


def _days(start: date, end: date) -> list[date]:
    days: list[date] = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def _manifest(payload: dict[str, object] | None) -> dict[str, object] | None:
    if payload is None:
        return None
    actuals = payload.get("actuals")
    forecasts = payload.get("forecasts")
    actuals_map = actuals if isinstance(actuals, dict) else {}
    forecasts_map = forecasts if isinstance(forecasts, dict) else {}
    return {
        "fetched_at": _text(payload.get("fetched_at")),
        "actuals_rows": _whole(actuals_map.get("rows")),
        "forecasts_rows": _whole(forecasts_map.get("rows")),
        "actuals_source": _text(actuals_map.get("source_endpoint")),
        "forecasts_source": _text(forecasts_map.get("source_endpoint")),
    }


def _iso_z(value: Any) -> str | None:
    if value is None or _missing(value):
        return None
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    return stamp.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def _london(value: Any, tz: str) -> str | None:
    if value is None or _missing(value):
        return None
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    return stamp.tz_convert(tz).strftime("%Y-%m-%dT%H:%M:%S")


def _num(value: Any) -> float | None:
    if value is None or _missing(value):
        return None
    return float(value)


def _missing(value: Any) -> bool:
    try:
        missing = pd.isna(value)
    except TypeError:
        return False
    return bool(missing)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _whole(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return int(value)
