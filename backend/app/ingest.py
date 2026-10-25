"""Download a FUELHH and WINDFOR snapshot into data/*.parquet."""

import argparse
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd

from app.clients.elexon import FUELHH_PATH, WINDFOR_PATH, ElexonClient
from app.config import Settings
from app.services.normalize import normalize_actuals, normalize_forecasts


def main(argv: list[str] | None = None) -> None:
    """Fetch, normalize, and write the parquet snapshot."""
    args = _parser().parse_args(argv)
    if args.end < args.start:
        message = "--to must be on or after --from"
        raise SystemExit(message)

    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    publish_from = datetime(args.start.year, args.start.month, args.start.day, tzinfo=UTC)
    # WINDFOR publish windows are half-open, so the end date is included through its last instant.
    publish_to = datetime(args.end.year, args.end.month, args.end.day, tzinfo=UTC) + timedelta(
        days=1
    )
    fetched_at = datetime.now(UTC)
    base_url = Settings().elexon_base_url.rstrip("/")

    with ElexonClient() as client:
        actual_rows = client.fetch_fuelhh_wind(args.start, args.end)
        forecast_rows = client.fetch_windfor(publish_from, publish_to)

    actuals = normalize_actuals(actual_rows)
    forecasts = normalize_forecasts(forecast_rows)
    actuals.to_parquet(data_dir / "actuals.parquet", index=False)
    forecasts.to_parquet(data_dir / "forecasts.parquet", index=False)

    manifest = {
        "fetched_at": _iso_z(fetched_at),
        "actuals": _series_summary(actuals, "start_time_utc", f"{base_url}{FUELHH_PATH}"),
        "forecasts": {
            **_series_summary(forecasts, "start_time_utc", f"{base_url}{WINDFOR_PATH}"),
            "min_publish_time_utc": _iso_z(_min(forecasts, "publish_time_utc")),
            "max_publish_time_utc": _iso_z(_max(forecasts, "publish_time_utc")),
        },
    }
    manifest_path = data_dir / "_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _print_summary(manifest)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write the FUELHH and WINDFOR parquet snapshot.")
    parser.add_argument("--from", dest="start", required=True, type=_parse_date, help="YYYY-MM-DD")
    parser.add_argument("--to", dest="end", required=True, type=_parse_date, help="YYYY-MM-DD")
    return parser


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _data_dir() -> Path:
    """Resolve DATA_DIR. A relative path is from the backend directory."""
    configured = Settings().data_dir
    if configured.is_absolute():
        return configured
    backend_dir = Path(__file__).resolve().parents[1]
    return (backend_dir / configured).resolve()


def _series_summary(frame: pd.DataFrame, time_column: str, endpoint: str) -> dict[str, object]:
    return {
        "rows": int(len(frame)),
        "min_start_time_utc": _iso_z(_min(frame, time_column)),
        "max_start_time_utc": _iso_z(_max(frame, time_column)),
        "source_endpoint": endpoint,
    }


def _min(frame: pd.DataFrame, column: str) -> pd.Timestamp | None:
    if frame.empty or column not in frame.columns:
        return None
    value = frame[column].min()
    if pd.isna(value):
        return None
    return pd.Timestamp(value)


def _max(frame: pd.DataFrame, column: str) -> pd.Timestamp | None:
    if frame.empty or column not in frame.columns:
        return None
    value = frame[column].max()
    if pd.isna(value):
        return None
    return pd.Timestamp(value)


def _iso_z(value: datetime | pd.Timestamp | None) -> str | None:
    if value is None or pd.isna(value):
        return None
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize(UTC)
    return stamp.tz_convert(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _print_summary(manifest: dict[str, object]) -> None:
    actuals = manifest["actuals"]
    forecasts = manifest["forecasts"]
    header = (
        "dataset",
        "rows",
        "min_start_utc",
        "max_start_utc",
        "min_publish_utc",
        "max_publish_utc",
    )
    rows = [
        _table_row("actuals", actuals, publish=False),
        _table_row("forecasts", forecasts, publish=True),
    ]
    widths = [len(cell) for cell in header]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row, strict=True)]
    _emit(header, widths)
    for row in rows:
        _emit(row, widths)


def _table_row(name: str, summary: object, *, publish: bool) -> tuple[str, str, str, str, str, str]:
    if not isinstance(summary, dict):
        message = "manifest summary is not an object"
        raise TypeError(message)
    return (
        name,
        str(summary["rows"]),
        _cell(summary.get("min_start_time_utc")),
        _cell(summary.get("max_start_time_utc")),
        _cell(summary.get("min_publish_time_utc")) if publish else "-",
        _cell(summary.get("max_publish_time_utc")) if publish else "-",
    )


def _cell(value: object) -> str:
    if value is None:
        return "-"
    return str(value)


def _emit(cells: tuple[str, ...], widths: list[int]) -> None:
    print("  ".join(cell.ljust(width) for cell, width in zip(cells, widths, strict=True)))


if __name__ == "__main__":
    main()
