import polars as pl

from grocery_shock.embed import embed
from grocery_shock.ingest.bronze import build_bronze
from grocery_shock.ingest.sdmx import parse_observations
from grocery_shock.paths import raw_dir


def test_parse_observations_skips_blank_values():
    payload = {
        "data": {
            "structures": [
                {
                    "dimensions": {
                        "series": [
                            {"id": "MEASURE", "values": [{"id": "1", "name": "Index"}]},
                            {"id": "INDEX", "values": [{"id": "114121", "name": "Fruit"}]},
                        ],
                        "observation": [
                            {
                                "id": "TIME_PERIOD",
                                "values": [{"id": "2026-09"}, {"id": "2026-08"}],
                            }
                        ],
                    }
                }
            ],
            "dataSets": [
                {
                    "series": {
                        "0:0": {
                            "observations": {
                                "0": [10.2],
                                "1": [None],
                            }
                        }
                    }
                }
            ],
        }
    }
    rows = parse_observations(payload)
    assert rows == [
        {
            "index_id": "114121",
            "index_name": "Fruit",
            "period": "2026-09",
            "value": 10.2,
        }
    ]


def test_bronze_keeps_september_fruit(tmp_path):
    stats = build_bronze(raw_dir(), tmp_path)
    frame = pl.read_parquet(tmp_path / "cpi_observations.parquet")
    fruit = frame.filter(
        (pl.col("measure") == "3")
        & (pl.col("index_id") == "114121")
        & (pl.col("period") == "2026-09")
    )
    assert stats["observations"] > 1000
    assert fruit["value"][0] == 10.2
    cash = pl.read_parquet(tmp_path / "cash_rate_daily.parquet")
    latest = cash.sort("date").tail(1)
    assert latest["cash_rate_target"][0] == 4.85


def test_embed_is_deterministic_and_unit_length():
    first = embed("fruit prices spiked in september")
    second = embed("fruit prices spiked in september")
    assert first == second
    norm = sum(value * value for value in first) ** 0.5
    assert abs(norm - 1) < 1e-9
