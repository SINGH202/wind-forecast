"""API contract against a tiny parquet snapshot."""

import ast
import json
from pathlib import Path

import pandas as pd
import pytest
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def _utc(value: str) -> pd.Timestamp:
    return pd.Timestamp(value, tz="UTC")


def _write_snapshot(directory: Path) -> None:
    """Three prior days of +10, +20, +30 MW error, then a decision day.

    2026-01-04 00:00Z forecasts, cutoff 09:00Z on 3 January:
    publish 00:00Z is 40 MW (horizon 24), 08:00Z is 100 MW, 09:01Z is 999 MW.
    The decision row is 100 MW. Actual is 90 MW, so the decision error is +10.
    """
    actuals = pd.DataFrame(
        {
            "start_time_utc": [
                _utc("2026-01-01T00:00:00Z"),
                _utc("2026-01-02T00:00:00Z"),
                _utc("2026-01-03T00:00:00Z"),
                _utc("2026-01-04T00:00:00Z"),
            ],
            "actual_mw": [100.0, 100.0, 100.0, 90.0],
        }
    )
    forecasts = pd.DataFrame(
        {
            "start_time_utc": [
                _utc("2026-01-01T00:00:00Z"),
                _utc("2026-01-02T00:00:00Z"),
                _utc("2026-01-03T00:00:00Z"),
                _utc("2026-01-04T00:00:00Z"),
                _utc("2026-01-04T00:00:00Z"),
                _utc("2026-01-04T00:00:00Z"),
            ],
            "publish_time_utc": [
                _utc("2025-12-31T08:00:00Z"),
                _utc("2026-01-01T08:00:00Z"),
                _utc("2026-01-02T08:00:00Z"),
                _utc("2026-01-03T00:00:00Z"),
                _utc("2026-01-03T08:00:00Z"),
                _utc("2026-01-03T09:01:00Z"),
            ],
            "forecast_mw": [110.0, 120.0, 130.0, 40.0, 100.0, 999.0],
            "horizon_hours": [16.0, 16.0, 16.0, 24.0, 16.0, 14.983333],
        }
    )
    actuals.to_parquet(directory / "actuals.parquet", index=False)
    forecasts.to_parquet(directory / "forecasts.parquet", index=False)
    manifest = {
        "fetched_at": "2026-02-02T00:00:00Z",
        "actuals": {"rows": 4, "source_endpoint": "https://example.test/fuelhh"},
        "forecasts": {"rows": 6, "source_endpoint": "https://example.test/windfor"},
    }
    (directory / "_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _client(directory: Path) -> TestClient:
    _write_snapshot(directory)
    settings = Settings(
        data_dir=directory,
        decision_cutoff_time="09:00",
        timezone="Europe/London",
    )
    application = create_app(settings)
    # The process keeps the frames loaded at startup.
    (directory / "actuals.parquet").unlink()
    (directory / "forecasts.parquet").unlink()
    return TestClient(application)


def test_meta_reports_coverage_and_assumptions(tmp_path: Path) -> None:
    """Coverage comes from the snapshot loaded before the files were removed."""
    client = _client(tmp_path)

    response = client.get("/api/meta")

    assert response.status_code == 200
    body = response.json()
    assert body["delivery_days"] == [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
        "2026-01-04",
    ]
    assert body["delivery_day_count"] == 4
    assert body["min_start_time"] == "2026-01-01T00:00:00Z"
    assert body["max_start_time"] == "2026-01-04T00:00:00Z"
    assert body["default_cutoff"] == "09:00"
    assert body["cutoff_options"] == ["08:00", "08:30", "09:00"]
    assert body["timezone"] == "Europe/London"
    assert body["manifest"]["fetched_at"] == "2026-02-02T00:00:00Z"
    assert body["manifest"]["actuals_rows"] == 4
    assert any("residual demand" in item for item in body["assumptions"])


def test_decision_uses_the_cutoff_and_prior_days_only(tmp_path: Path) -> None:
    """100 MW at 08:00Z is the decision forecast. Firm wind is 100 - 28 = 72."""
    # Prior errors +10, +20, +30. P10 = 12, P90 = 28.
    # lower = max(0, 100 - 28) = 72. upper = 100 - 12 = 88.
    # The only forecast is on the hour, so the slot is 1.0 h.
    # expected = 100 * 1 = 100 MWh. firm = 72 * 1 = 72 MWh. Age = 1 h.
    client = _client(tmp_path)

    response = client.get("/api/decision", params={"delivery_day": "2026-01-04"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["points"]) == 48
    assert body["cutoff_utc"] == "2026-01-03T09:00:00Z"
    assert body["cutoff_local"] == "2026-01-03T09:00:00"
    assert body["band_available"] is True
    assert body["band_reason"] is None
    midnight = body["points"][0]
    assert midnight["start_time"] == "2026-01-04T00:00:00Z"
    assert midnight["forecast_mw"] == 100
    assert midnight["publish_time"] == "2026-01-03T08:00:00Z"
    assert midnight["actual_mw"] == 90
    assert midnight["firm_mw"] == 72
    assert midnight["band_low_mw"] == 72
    assert midnight["band_high_mw"] == 88
    assert midnight["forecast_age_hours"] == 1
    assert body["points"][1]["forecast_mw"] is None
    assert body["kpis"]["expected_mwh"] == 100
    assert body["kpis"]["firm_wind_mwh"] == 72
    assert body["kpis"]["forecast_age_hours"] == 1
    assert body["kpis"]["half_hours_with_forecast"] == 1
    assert body["kpis"]["half_hours_expected"] == 48
    assert body["error_sample"] == {
        "n": 3,
        "p10_error_mw": 12,
        "p90_error_mw": 28,
        "prior_days_used": 3,
    }


def test_decision_flags_insufficient_history(tmp_path: Path) -> None:
    """Two earlier days are below the three-day minimum, so the band stays empty."""
    client = _client(tmp_path)

    response = client.get("/api/decision", params={"delivery_day": "2026-01-03", "cutoff": "09:00"})

    assert response.status_code == 200
    body = response.json()
    assert body["band_available"] is False
    assert body["band_reason"] == "insufficient history"
    assert body["points"][0]["forecast_mw"] == 130
    assert body["points"][0]["firm_mw"] is None
    assert "no_prior_days_for_band" in body["flags"]
    assert body["error_sample"]["prior_days_used"] == 2
    assert body["error_sample"]["p90_error_mw"] is None


def test_decision_rejects_a_day_outside_the_snapshot(tmp_path: Path) -> None:
    """February, and a January day past the loaded span, are both invalid."""
    client = _client(tmp_path)

    february = client.get("/api/decision", params={"delivery_day": "2026-02-01", "cutoff": "09:00"})
    later = client.get("/api/decision", params={"delivery_day": "2026-01-20", "cutoff": "09:00"})
    cutoff = client.get("/api/decision", params={"delivery_day": "2026-01-04", "cutoff": "07:00"})
    after_close = client.get(
        "/api/decision", params={"delivery_day": "2026-01-04", "cutoff": "09:30"}
    )
    garbage = client.get("/api/decision", params={"delivery_day": "nope", "cutoff": "09:00"})

    assert february.status_code == 400
    assert february.json() == {"detail": "delivery_day is invalid"}
    assert later.status_code == 400
    assert later.json() == {"detail": "delivery_day is invalid"}
    assert cutoff.status_code == 400
    assert cutoff.json() == {"detail": "cutoff is invalid"}
    assert after_close.status_code == 400
    assert after_close.json() == {"detail": "cutoff is invalid"}
    assert garbage.status_code == 422


def test_series_horizon_default_is_latest_and_24_keeps_the_early_publish(tmp_path: Path) -> None:
    """Horizon 0 selects 999 MW. Horizon 24 selects the 40 MW publish."""
    client = _client(tmp_path)
    params = {"start_day": "2026-01-04", "end_day": "2026-01-04"}

    latest = client.get("/api/series", params=params)
    early = client.get("/api/series", params={**params, "horizon_hours": 24})

    assert latest.status_code == 200
    assert latest.json()["horizon_hours"] == 0
    assert len(latest.json()["points"]) == 48
    assert latest.json()["points"][0]["forecast_mw"] == 999
    assert latest.json()["points"][0]["publish_time"] == "2026-01-03T09:01:00Z"
    assert early.status_code == 200
    assert early.json()["points"][0]["forecast_mw"] == 40
    assert early.json()["points"][0]["publish_time"] == "2026-01-03T00:00:00Z"


def test_series_rejects_a_reversed_range_and_a_horizon_past_48(tmp_path: Path) -> None:
    client = _client(tmp_path)

    reversed_range = client.get(
        "/api/series",
        params={"start_day": "2026-01-04", "end_day": "2026-01-01", "horizon_hours": 0},
    )
    too_far = client.get(
        "/api/series",
        params={"start_day": "2026-01-04", "end_day": "2026-01-04", "horizon_hours": 49},
    )
    negative = client.get(
        "/api/series",
        params={"start_day": "2026-01-04", "end_day": "2026-01-04", "horizon_hours": -1},
    )

    assert reversed_range.status_code == 400
    assert reversed_range.json() == {"detail": "start_day is invalid"}
    assert too_far.status_code == 400
    assert too_far.json() == {"detail": "horizon_hours is invalid"}
    assert negative.status_code == 400
    assert negative.json() == {"detail": "horizon_hours is invalid"}


def test_metrics_keeps_decision_scores_apart_from_every_vintage(tmp_path: Path) -> None:
    """Decision MAE uses the +10 MW error. The 999 MW vintage stays in the horizon group."""
    # Decision error = 100 - 90 = +10. MAE = 10. nMAE = 10 / 90.
    # Vintages at horizon 16 and 14.98 are both in [12, 24): errors +10 and +909.
    client = _client(tmp_path)

    response = client.get(
        "/api/metrics",
        params={"start_day": "2026-01-04", "end_day": "2026-01-04", "cutoff": "09:00"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["n"] == 1
    assert body["pairs_excluded_missing"] == 47
    assert body["mae_mw"] == 10
    assert body["bias_mw"] == 10
    assert body["rmse_mw"] == 10
    assert body["nmae"] == pytest.approx(10 / 90)
    assert body["mean_actual_mw"] == 90
    assert body["p10_error_mw"] == 10
    assert body["p90_error_mw"] == 10
    assert body["by_hour_london"][0] == {"hour": 0, "n": 1, "mae_mw": 10, "bias_mw": 10}
    assert body["by_hour_london"][1]["n"] == 0
    assert body["by_hour_london"][1]["mae_mw"] is None
    wind = {row["bucket"]: row for row in body["by_wind_level"]}
    assert wind["[0,5000)"]["n"] == 1
    assert wind["[0,5000)"]["mae_mw"] == 10
    assert body["histogram"] == [{"edge_low_mw": 0, "edge_high_mw": 500, "count": 1}]
    assert body["worst_days"] == [
        {"delivery_day": "2026-01-04", "n": 1, "mae_mw": 10, "bias_mw": 10}
    ]
    assert body["by_horizon"]["label"] == "All forecast vintages, grouped by horizon"
    buckets = {row["bucket"]: row for row in body["by_horizon"]["buckets"]}
    assert buckets["[12,24)"]["n"] == 2
    assert buckets["[12,24)"]["mae_mw"] == pytest.approx((10 + 909) / 2)
    assert buckets["[24,48)"]["n"] == 1
    assert buckets["[24,48)"]["bias_mw"] == -50


def test_metrics_rejects_an_unknown_cutoff(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get(
        "/api/metrics",
        params={"start_day": "2026-01-04", "end_day": "2026-01-04", "cutoff": "10:00"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "cutoff is invalid"}


def test_docs_expose_the_openapi_schema(tmp_path: Path) -> None:
    client = _client(tmp_path)

    docs = client.get("/docs")
    schema = client.get("/openapi.json")

    assert docs.status_code == 200
    assert "openapi.json" in docs.text
    paths = schema.json()["paths"]
    assert "/api/meta" in paths
    assert "/api/decision" in paths
    assert "/api/series" in paths
    assert "/api/metrics" in paths
    assert "DecisionResponse" in schema.json()["components"]["schemas"]


def test_api_package_does_not_import_pandas_or_the_elexon_client() -> None:
    """Routes stay free of dataframes and of the ingest-only client."""
    api_dir = ROOT / "app" / "api"
    for path in api_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules: list[str | None] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.append(node.module)
            for module in modules:
                assert module is None or not module.startswith("pandas")
                assert module is None or module != "app.clients"
                assert module is None or not module.startswith("app.clients.")
