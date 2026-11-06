"""Clean the committed snapshots with Polars and write bronze parquet."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from grocery_shock.paths import bronze_dir, raw_dir

PERIOD_MONTH = r"^\d{4}-\d{2}$"
PERIOD_QUARTER = r"^\d{4}-Q[1-4]$"


def _write(frame: pl.DataFrame, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(path)
    return frame.height


def build_bronze(source: Path | None = None, target: Path | None = None) -> dict[str, int]:
    raw = source or raw_dir()
    out = target or bronze_dir()

    observations = (
        pl.read_csv(
            raw / "cpi_observations.csv",
            schema_overrides={
                "measure": pl.Utf8,
                "index_id": pl.Utf8,
                "index_name": pl.Utf8,
                "period": pl.Utf8,
                "value": pl.Float64,
            },
        )
        .with_columns(
            pl.col("index_id").str.strip_chars(),
            pl.col("measure").str.strip_chars(),
            pl.col("period").str.strip_chars(),
        )
        .filter(pl.col("value").is_not_null())
        .filter(pl.col("period").str.contains(PERIOD_MONTH))
        .unique(subset=["measure", "index_id", "period"], keep="first")
        .sort(["measure", "index_id", "period"])
    )

    weights = (
        pl.read_csv(
            raw / "cpi_weights.csv",
            schema_overrides={
                "index_id": pl.Utf8,
                "index_name": pl.Utf8,
                "period": pl.Utf8,
                "weight_pct": pl.Float64,
            },
        )
        .with_columns(
            pl.col("index_id").str.strip_chars(),
            pl.col("period").str.strip_chars(),
        )
        .filter(pl.col("weight_pct").is_not_null())
        .filter(pl.col("period").str.contains(PERIOD_QUARTER))
        .unique(subset=["index_id", "period"], keep="first")
        .sort(["index_id", "period"])
    )

    cash = (
        pl.read_csv(
            raw / "rba_cash_rate_daily.csv",
            schema_overrides={
                "date": pl.Utf8,
                "cash_rate_target": pl.Float64,
                "cash_rate_change_published": pl.Float64,
                "overnight_cash_rate": pl.Float64,
            },
        )
        .with_columns(pl.col("date").str.strptime(pl.Date, "%Y-%m-%d"))
        .filter(pl.col("cash_rate_target").is_not_null())
        .unique(subset=["date"], keep="first")
        .sort("date")
    )

    return {
        "observations": _write(observations, out / "cpi_observations.parquet"),
        "weights": _write(weights, out / "cpi_weights.parquet"),
        "cash_rate": _write(cash, out / "cash_rate_daily.parquet"),
    }
