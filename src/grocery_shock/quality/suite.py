"""Great Expectations suites over the bronze parquet files."""

from __future__ import annotations

import os

os.environ.setdefault("GX_ANALYTICS_ENABLED", "false")
os.environ.setdefault("TQDM_DISABLE", "1")

import great_expectations as gx
import great_expectations.expectations as gxe
import polars as pl

from grocery_shock.paths import bronze_dir


class DataQualityError(RuntimeError):
    pass


def _validate(frame: pl.DataFrame, expectations: list) -> list[str]:
    context = gx.get_context(mode="ephemeral")
    context.variables.analytics_enabled = False
    source = context.data_sources.add_pandas("bronze")
    asset = source.add_dataframe_asset(name="frame")
    batch_definition = asset.add_batch_definition_whole_dataframe("whole")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": frame.to_pandas()})
    suite = gx.ExpectationSuite(name="bronze", expectations=expectations)
    result = batch.validate(suite)
    failures = []
    for item in result.results:
        if not item.success:
            config = item.expectation_config
            failures.append(f"{config.type} {config.kwargs}")
    return failures


def run_quality(directory=None) -> dict[str, int]:
    folder = directory or bronze_dir()
    observations = pl.read_parquet(folder / "cpi_observations.parquet")
    weights = pl.read_parquet(folder / "cpi_weights.parquet")
    cash = pl.read_parquet(folder / "cash_rate_daily.parquet")
    index_only = observations.filter(pl.col("measure") == "1")
    changes = observations.filter(pl.col("measure").is_in(["3", "7"]))

    checks = [
        (
            "observations",
            observations,
            [
                gxe.ExpectColumnValuesToNotBeNull(column="value"),
                gxe.ExpectColumnValuesToNotBeNull(column="index_id"),
                gxe.ExpectColumnValuesToNotBeNull(column="period"),
                gxe.ExpectColumnValuesToBeInSet(column="measure", value_set=["1", "3", "7"]),
                gxe.ExpectColumnValuesToMatchRegex(column="period", regex=r"^\d{4}-\d{2}$"),
                gxe.ExpectCompoundColumnsToBeUnique(column_list=["measure", "index_id", "period"]),
            ],
        ),
        (
            "index_levels",
            index_only,
            [gxe.ExpectColumnValuesToBeBetween(column="value", min_value=40, max_value=300)],
        ),
        (
            "changes",
            changes,
            [gxe.ExpectColumnValuesToBeBetween(column="value", min_value=-80, max_value=80)],
        ),
        (
            "weights",
            weights,
            [
                gxe.ExpectColumnValuesToNotBeNull(column="weight_pct"),
                gxe.ExpectColumnValuesToBeBetween(column="weight_pct", min_value=0, max_value=100),
                gxe.ExpectColumnValuesToMatchRegex(column="period", regex=r"^\d{4}-Q[1-4]$"),
                gxe.ExpectCompoundColumnsToBeUnique(column_list=["index_id", "period"]),
            ],
        ),
        (
            "cash_rate",
            cash,
            [
                gxe.ExpectColumnValuesToNotBeNull(column="cash_rate_target"),
                gxe.ExpectColumnValuesToBeBetween(
                    column="cash_rate_target", min_value=0, max_value=20
                ),
                gxe.ExpectColumnValuesToBeUnique(column="date"),
            ],
        ),
    ]
    failed: list[str] = []
    for name, frame, expectations in checks:
        for failure in _validate(frame, expectations):
            failed.append(f"{name}: {failure}")
    if failed:
        raise DataQualityError("; ".join(failed))
    return {
        "observations": observations.height,
        "weights": weights.height,
        "cash_rate": cash.height,
    }
