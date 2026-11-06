"""Repository paths. Override the root with GROCERY_ROOT in tests."""

from __future__ import annotations

import os
from pathlib import Path

MELBOURNE = "Australia/Melbourne"
ACCESS_DATE = "2026-11-06"


def project_root() -> Path:
    override = os.environ.get("GROCERY_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[2]


def raw_dir() -> Path:
    return project_root() / "data" / "raw"


def bronze_dir() -> Path:
    return project_root() / "data" / "bronze"


def warehouse_path() -> Path:
    override = os.environ.get("GROCERY_DUCKDB")
    if override:
        return Path(override)
    return project_root() / "data" / "warehouse" / "grocery.duckdb"


def dbt_dir() -> Path:
    return project_root() / "dbt"


def catalog_path() -> Path:
    return dbt_dir() / "seeds" / "series_catalog.csv"


def insights_dir() -> Path:
    return project_root() / "data" / "insights"


def site_dir() -> Path:
    return project_root() / "site"


def traces_dir() -> Path:
    return project_root() / "src" / "agent" / "traces"


def manifest_path() -> Path:
    return project_root() / "data" / "manifest.json"
