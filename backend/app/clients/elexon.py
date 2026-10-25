"""Elexon BMRS stream client. Returns plain dicts; no forecast logic."""

import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from app.config import Settings

# TODO: DATA_NOTES.md does not document a maximum request span (open question).
# The saved samples cover two settlement dates and a 48-hour publish window.
# Confirm the real limit before relying on this value.
MAX_DAYS_PER_REQUEST = 7

FUELHH_PATH = "/datasets/FUELHH/stream"
WINDFOR_PATH = "/datasets/WINDFOR/stream"
TIMEOUT_SECONDS = 30.0
MAX_RETRIES = 3
_BACKOFF_SECONDS = 0.5


class ElexonAPIError(Exception):
    """Elexon failed, or the body was not the JSON array the samples use."""


class ElexonClient:
    """GET FUELHH and WINDFOR stream endpoints."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        resolved = base_url if base_url is not None else Settings().elexon_base_url
        self._sleep = sleep if sleep is not None else _default_sleep
        self._client = httpx.Client(
            base_url=resolved,
            timeout=httpx.Timeout(TIMEOUT_SECONDS),
            transport=transport,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "ElexonClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def fetch_fuelhh_wind(self, start: date, end: date) -> list[dict[str, Any]]:
        """Actual wind rows for settlement dates from start through end, inclusive."""
        rows: list[dict[str, Any]] = []
        for chunk_start, chunk_end in _date_chunks(start, end):
            payload = self._get_json_array(
                FUELHH_PATH,
                {
                    "settlementDateFrom": chunk_start.isoformat(),
                    "settlementDateTo": chunk_end.isoformat(),
                    "fuelType": "WIND",
                },
            )
            rows.extend(row for row in payload if row.get("fuelType") == "WIND")
        return rows

    def fetch_windfor(self, publish_from: datetime, publish_to: datetime) -> list[dict[str, Any]]:
        """Forecast rows with publishTime in [publish_from, publish_to)."""
        start = _as_utc(publish_from)
        end = _as_utc(publish_to)
        rows: list[dict[str, Any]] = []
        for chunk_start, chunk_end in _time_chunks(start, end):
            rows.extend(
                self._get_json_array(
                    WINDFOR_PATH,
                    {
                        "publishDateTimeFrom": _format_z(chunk_start),
                        "publishDateTimeTo": _format_z(chunk_end),
                    },
                )
            )
        return rows

    def _get_json_array(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        """GET one window. Retry network errors and 5xx up to MAX_RETRIES times."""
        attempt = 0
        while True:
            try:
                response = self._client.get(path, params=params)
            except httpx.TransportError as exc:
                if attempt >= MAX_RETRIES:
                    message = f"Elexon request failed after {MAX_RETRIES} retries: {path}"
                    raise ElexonAPIError(message) from exc
                self._sleep(_BACKOFF_SECONDS * (2**attempt))
                attempt += 1
                continue
            if response.status_code >= 500:
                if attempt >= MAX_RETRIES:
                    message = (
                        f"Elexon request failed with status {response.status_code} "
                        f"after {MAX_RETRIES} retries: {response.url}"
                    )
                    raise ElexonAPIError(message)
                self._sleep(_BACKOFF_SECONDS * (2**attempt))
                attempt += 1
                continue
            if response.status_code != 200:
                detail = response.text.strip().replace("\n", " ")[:500]
                message = (
                    f"Elexon request failed with status {response.status_code} "
                    f"for {response.url}: {detail}"
                )
                raise ElexonAPIError(message)
            payload: Any = response.json()
            if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
                message = f"Expected a JSON array of objects from {response.url}"
                raise ElexonAPIError(message)
            return payload


def _default_sleep(seconds: float) -> None:
    time.sleep(seconds)


def _date_chunks(start: date, end: date) -> list[tuple[date, date]]:
    """Inclusive settlement-date windows. The sample To date is included."""
    if end < start:
        message = "end must be on or after start"
        raise ValueError(message)
    chunks: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        chunk_end = min(end, cursor + timedelta(days=MAX_DAYS_PER_REQUEST - 1))
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + timedelta(days=1)
    return chunks


def _time_chunks(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """Half-open publish windows. Sample publish times fall strictly before publishDateTimeTo."""
    if end <= start:
        message = "publish_to must be after publish_from"
        raise ValueError(message)
    chunks: list[tuple[datetime, datetime]] = []
    cursor = start
    step = timedelta(days=MAX_DAYS_PER_REQUEST)
    while cursor < end:
        chunk_end = min(end, cursor + step)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end
    return chunks


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _format_z(value: datetime) -> str:
    utc = _as_utc(value).replace(microsecond=0, tzinfo=None)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")
