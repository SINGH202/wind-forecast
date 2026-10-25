"""Download small FUELHH and WINDFOR samples from the Elexon BMRS API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
TIMEOUT_SECONDS = 30.0
SAMPLES_DIR = Path(__file__).resolve().parents[1] / "docs" / "samples"

# About two days from 2026-01-05. FUELHH cannot combine settlement dates with
# publishDateTime* (BMRS docs). WINDFOR stream only accepts publish time filters.
REQUESTS: tuple[tuple[str, str, dict[str, str]], ...] = (
    (
        "fuelhh_wind_sample.json",
        "/datasets/FUELHH/stream",
        {
            "settlementDateFrom": "2026-01-05",
            "settlementDateTo": "2026-01-06",
            "fuelType": "WIND",
        },
    ),
    (
        "windfor_sample.json",
        "/datasets/WINDFOR/stream",
        {
            "publishDateTimeFrom": "2026-01-05T00:00:00Z",
            "publishDateTimeTo": "2026-01-07T00:00:00Z",
        },
    ),
)


def fetch_rows(client: httpx.Client, path: str, params: dict[str, str]) -> tuple[str, list[Any]]:
    """GET one stream endpoint and return the called URL plus the JSON array."""
    request = client.build_request("GET", path, params=params)
    url = str(request.url)
    try:
        response = client.send(request)
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"BMRS request timed out after {TIMEOUT_SECONDS:.0f}s: {url}") from exc

    print(f"url: {url}")
    print(f"status: {response.status_code}")
    if response.status_code != 200:
        detail = response.text.strip().replace("\n", " ")[:500]
        raise RuntimeError(f"BMRS request failed with status {response.status_code} for {url}: {detail}")

    payload: Any = response.json()
    if not isinstance(payload, list):
        raise TypeError(f"Expected a JSON array from {url}, got {type(payload).__name__}")

    print(f"rows: {len(payload)}")
    return url, payload


def write_json(path: Path, rows: list[Any]) -> None:
    """Pretty-print one sample response."""
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def write_readme(urls: list[str]) -> None:
    """Record the exact request URLs that produced the sample files."""
    lines = [
        "# BMRS samples",
        "",
        "Exact URLs called by `scripts/fetch_samples.py`:",
        "",
    ]
    lines.extend(f"- {url}" for url in urls)
    lines.append("")
    readme = SAMPLES_DIR / "README.md"
    readme.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """Fetch both samples and write them under docs/samples/."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    urls: list[str] = []
    timeout = httpx.Timeout(TIMEOUT_SECONDS)
    headers = {"Accept": "application/json"}
    with httpx.Client(base_url=BASE_URL, timeout=timeout, headers=headers) as client:
        for filename, path, params in REQUESTS:
            url, rows = fetch_rows(client, path, params)
            write_json(SAMPLES_DIR / filename, rows)
            urls.append(url)
    write_readme(urls)


if __name__ == "__main__":
    main()
