"""Elexon client against the saved sample payloads. No live network."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
from app.clients.elexon import MAX_DAYS_PER_REQUEST, ElexonAPIError, ElexonClient

SAMPLES = Path(__file__).resolve().parents[2] / "docs" / "samples"
BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"


def _load(name: str) -> list[dict[str, object]]:
    payload: object = json.loads((SAMPLES / name).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        message = f"{name} is not a JSON array"
        raise TypeError(message)
    return [row for row in payload if isinstance(row, dict)]


FUELHH = _load("fuelhh_wind_sample.json")
WINDFOR = _load("windfor_sample.json")


def _client(handler: httpx.MockTransport, delays: list[float]) -> ElexonClient:
    return ElexonClient(
        base_url=BASE_URL,
        transport=handler,
        sleep=delays.append,
    )


def test_fuelhh_keeps_wind_only() -> None:
    """A non-WIND row in the body is dropped, and the request asks for WIND."""
    extra = dict(FUELHH[0])
    extra["fuelType"] = "BIOMASS"
    seen: list[httpx.QueryParams] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params)
        return httpx.Response(200, json=[*FUELHH, extra])

    with _client(httpx.MockTransport(handler), []) as client:
        rows = client.fetch_fuelhh_wind(date(2026, 1, 5), date(2026, 1, 6))

    assert len(rows) == len(FUELHH)
    assert {row["fuelType"] for row in rows} == {"WIND"}
    assert seen[0]["settlementDateFrom"] == "2026-01-05"
    assert seen[0]["settlementDateTo"] == "2026-01-06"
    assert seen[0]["fuelType"] == "WIND"


def test_twenty_day_fuelhh_request_is_chunked() -> None:
    """20 inclusive settlement dates split on MAX_DAYS_PER_REQUEST without overlap."""
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        seen.append((params["settlementDateFrom"], params["settlementDateTo"]))
        return httpx.Response(200, json=FUELHH)

    with _client(httpx.MockTransport(handler), []) as client:
        client.fetch_fuelhh_wind(date(2026, 1, 1), date(2026, 1, 20))

    assert len(seen) == _chunk_count(20)
    assert seen == [
        ("2026-01-01", "2026-01-07"),
        ("2026-01-08", "2026-01-14"),
        ("2026-01-15", "2026-01-20"),
    ]


def test_twenty_day_windfor_request_is_chunked() -> None:
    """A 20-day publish window uses publishDateTimeFrom/To and the same day limit."""
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        seen.append((params["publishDateTimeFrom"], params["publishDateTimeTo"]))
        return httpx.Response(200, json=WINDFOR)

    start = datetime(2025, 12, 25, tzinfo=UTC)
    with _client(httpx.MockTransport(handler), []) as client:
        rows = client.fetch_windfor(start, start + timedelta(days=20))

    assert len(seen) == _chunk_count(20)
    assert seen == [
        ("2025-12-25T00:00:00Z", "2026-01-01T00:00:00Z"),
        ("2026-01-01T00:00:00Z", "2026-01-08T00:00:00Z"),
        ("2026-01-08T00:00:00Z", "2026-01-14T00:00:00Z"),
    ]
    assert len(rows) == len(WINDFOR) * len(seen)


def test_retries_500_then_returns_rows() -> None:
    """One 500 is retried with backoff; the next 200 is returned."""
    calls = {"n": 0}
    delays: list[float] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, text="unavailable")
        return httpx.Response(200, json=FUELHH)

    with _client(httpx.MockTransport(handler), delays) as client:
        rows = client.fetch_fuelhh_wind(date(2026, 1, 5), date(2026, 1, 5))

    assert calls["n"] == 2
    assert delays == [0.5]
    assert len(rows) == len(FUELHH)


def test_400_raises_without_retry() -> None:
    """A 400 is an ElexonAPIError and is not retried."""
    calls = {"n": 0}
    delays: list[float] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, text="bad settlement date")

    with _client(httpx.MockTransport(handler), delays) as client:
        try:
            client.fetch_fuelhh_wind(date(2026, 1, 5), date(2026, 1, 5))
        except ElexonAPIError as exc:
            message = str(exc)
        else:
            message = ""

    assert calls["n"] == 1
    assert delays == []
    assert "400" in message
    assert "bad settlement date" in message


def _chunk_count(day_count: int) -> int:
    full, remainder = divmod(day_count, MAX_DAYS_PER_REQUEST)
    return full if remainder == 0 else full + 1
