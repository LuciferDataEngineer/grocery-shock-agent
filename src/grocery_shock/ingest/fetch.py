"""Refresh snapshots from the ABS and RBA. Falls back to the committed files.

Nothing in this module invents a number. A failed request leaves the previous
snapshot in place after retries.
"""

from __future__ import annotations

import csv
import io
import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from grocery_shock.ingest.sdmx import parse_observations
from grocery_shock.paths import raw_dir

USER_AGENT = "grocery-shock-agent/1.0 (public-data snapshot; CC BY / RBA attribution)"
ABS_ACCEPT = "application/vnd.sdmx.data+json; version=2.0.0"
CPI_URL = "https://data.api.abs.gov.au/rest/data/ABS,CPI,2.0.0/"
WEIGHT_URL = "https://data.api.abs.gov.au/rest/data/ABS,CPI_WEIGHTS,1.0.0/"
RBA_URL = "https://www.rba.gov.au/statistics/tables/csv/f1-data.csv"

# Index codes kept in the committed snapshot. 999902 (trimmed mean) is not on
# the monthly key, so it is not requested.
CPI_CODES = [
    "10001",
    "20001",
    "20003",
    "20005",
    "40055",
    "40081",
    "115522",
    "30014",
    "30002",
    "40005",
    "40006",
    "40007",
    "40008",
    "30003",
    "40009",
    "131178",
    "40010",
    "40012",
    "40014",
    "40015",
    "30001",
    "40001",
    "40002",
    "40004",
    "114120",
    "114121",
    "114122",
    "131179",
    "40027",
    "40029",
    "97549",
    "97550",
    "115501",
    "40034",
    "131180",
    "40030",
    "115520",
    "30007",
    "40025",
    "40026",
]
WEIGHT_CODES = [code for code in CPI_CODES if code != "30014"]


def _get(url: str, accept: str | None = None) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    request = urllib.request.Request(url, headers=headers)
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"request failed after retries: {url}") from last_error


def _chunks(codes: list[str], size: int) -> list[list[str]]:
    return [codes[index : index + size] for index in range(0, len(codes), size)]


def fetch_cpi_rows() -> list[dict]:
    rows: list[dict] = []
    windows = (("1", "2023-09"), ("3", "2024-09"), ("7", "2025-09"))
    for measure, start in windows:
        for batch in _chunks(CPI_CODES, 8):
            key = f"{measure}.{'+'.join(batch)}.10.50.M"
            url = f"{CPI_URL}{key}?startPeriod={start}&endPeriod=2026-09"
            payload = json.loads(_get(url, ABS_ACCEPT))
            for row in parse_observations(payload):
                row["measure"] = measure
                rows.append(row)
    return rows


def fetch_weight_rows() -> list[dict]:
    """One series per request. A combined key drops history on this endpoint."""
    rows: list[dict] = []
    for code in WEIGHT_CODES:
        url = (
            f"{WEIGHT_URL}1.{code}.50.Q?startPeriod=2018-Q1&endPeriod=2025-Q4"
        )
        payload = json.loads(_get(url, ABS_ACCEPT))
        for row in parse_observations(payload, value_field="weight_pct"):
            if row["index_id"] == code:
                rows.append(row)
        time.sleep(0.1)
    return rows


def fetch_cash_rows() -> list[dict]:
    text = _get(RBA_URL).decode("utf-8-sig")
    rows: list[dict] = []
    for line in text.splitlines():
        if not line[:1].isdigit():
            continue
        parts = line.strip().split(",")
        if len(parts) < 4 or not parts[1]:
            continue
        moment = datetime.strptime(parts[0], "%d-%b-%Y")
        if moment < datetime(2024, 1, 1) or moment > datetime(2026, 11, 5):
            continue
        rows.append(
            {
                "date": moment.strftime("%Y-%m-%d"),
                "cash_rate_target": parts[1],
                "cash_rate_change_published": parts[2],
                "overnight_cash_rate": parts[3],
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    path.write_text(buffer.getvalue())


def refresh_snapshots(directory: Path | None = None) -> dict[str, int]:
    target = directory or raw_dir()
    try:
        cpi = fetch_cpi_rows()
        weights = fetch_weight_rows()
        cash = fetch_cash_rows()
    except Exception as exc:
        existing = (target / "cpi_observations.csv").exists()
        print(f"Refresh failed ({exc}). {'Keeping the committed snapshot.' if existing else ''}")
        if existing:
            return {"refreshed": 0}
        raise
    cpi.sort(key=lambda row: (row["measure"], row["index_id"], row["period"]))
    weights.sort(key=lambda row: (row["index_id"], row["period"]))
    _write_csv(
        target / "cpi_observations.csv",
        cpi,
        ["measure", "index_id", "index_name", "period", "value"],
    )
    _write_csv(
        target / "cpi_weights.csv",
        weights,
        ["index_id", "index_name", "period", "weight_pct"],
    )
    _write_csv(
        target / "rba_cash_rate_daily.csv",
        cash,
        ["date", "cash_rate_target", "cash_rate_change_published", "overnight_cash_rate"],
    )
    return {"cpi": len(cpi), "weights": len(weights), "cash": len(cash), "refreshed": 1}


def main() -> None:
    print(refresh_snapshots())


if __name__ == "__main__":
    main()
