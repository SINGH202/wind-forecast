"""Response models. Field names follow the API contract."""

from pydantic import BaseModel, Field


class ManifestInfo(BaseModel):
    """Provenance stored next to the parquet snapshot."""

    fetched_at: str | None = None
    actuals_rows: int | None = None
    forecasts_rows: int | None = None
    actuals_source: str | None = None
    forecasts_source: str | None = None


class MetaResponse(BaseModel):
    """What the snapshot covers and which assumptions the figures use."""

    delivery_days: list[str]
    delivery_day_count: int
    min_start_time: str | None
    max_start_time: str | None
    default_cutoff: str
    cutoff_options: list[str]
    timezone: str
    power_unit: str
    energy_unit: str
    resolution_minutes: int
    manifest: ManifestInfo | None
    assumptions: list[str]


class DecisionPoint(BaseModel):
    """One half-hour of the decision view."""

    start_time: str
    start_time_london: str
    forecast_mw: float | None
    actual_mw: float | None
    firm_mw: float | None
    band_low_mw: float | None
    band_high_mw: float | None
    publish_time: str | None
    horizon_hours: float | None
    forecast_age_hours: float | None
    missing_forecast: bool
    missing_actual: bool


class DecisionKpis(BaseModel):
    """Day totals. An hourly forecast slot is MW times 1.0 h. Age is the freshest forecast."""

    expected_mwh: float | None
    firm_wind_mwh: float | None
    forecast_age_hours: float | None
    half_hours_with_forecast: int
    half_hours_expected: int


class ErrorSample(BaseModel):
    """Error quantiles from delivery days before the selected day."""

    n: int
    p10_error_mw: float | None
    p90_error_mw: float | None
    prior_days_used: int


class DecisionResponse(BaseModel):
    """Decision forecast, firm-wind band, and day KPIs."""

    delivery_day: str
    cutoff_local: str | None
    cutoff_utc: str | None
    band_available: bool
    band_reason: str | None
    points: list[DecisionPoint]
    kpis: DecisionKpis
    error_sample: ErrorSample
    flags: list[str]


class SeriesPoint(BaseModel):
    """One half-hour of the horizon view."""

    start_time: str
    start_time_london: str
    forecast_mw: float | None
    actual_mw: float | None
    publish_time: str | None
    horizon_hours: float | None
    missing_forecast: bool
    missing_actual: bool


class SeriesResponse(BaseModel):
    """Actual generation and the forecast selected by horizon."""

    start_day: str
    end_day: str
    horizon_hours: int
    points: list[SeriesPoint]


class HourMetric(BaseModel):
    """MAE and bias for one Europe/London clock hour."""

    hour: int
    n: int
    mae_mw: float | None
    bias_mw: float | None


class BucketMetric(BaseModel):
    """MAE and bias for one horizon or wind-level bucket."""

    bucket: str
    n: int
    mae_mw: float | None
    bias_mw: float | None


class HistogramBin(BaseModel):
    """One 500 MW error bin."""

    edge_low_mw: float
    edge_high_mw: float
    count: int


class WorstDay(BaseModel):
    """A delivery day ranked by decision-forecast MAE."""

    delivery_day: str
    n: int
    mae_mw: float
    bias_mw: float


class HorizonMetrics(BaseModel):
    """Every forecast vintage, grouped by horizon. Not the decision forecast."""

    label: str = Field(description="All forecast vintages, grouped by horizon")
    buckets: list[BucketMetric]


class MetricsResponse(BaseModel):
    """Accuracy for a date range at one cutoff.

    WINDFOR is hourly. Headline metrics use the 24 matching hourly slots per day.
    """

    start_day: str
    end_day: str
    cutoff: str
    n: int = Field(
        description=(
            "Matching hourly slots. The forecast is hourly, "
            "so metrics use the 24 matching hourly slots per day."
        )
    )
    pairs_excluded_missing: int = Field(
        description=(
            "Half-hour rows with no forecast or no actual. The forecast is hourly, "
            "so metrics use the 24 matching hourly slots per day."
        )
    )
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    nmae: float | None
    mean_actual_mw: float | None
    p10_error_mw: float | None
    p90_error_mw: float | None
    by_hour_london: list[HourMetric]
    by_wind_level: list[BucketMetric]
    histogram: list[HistogramBin]
    worst_days: list[WorstDay]
    by_horizon: HorizonMetrics
