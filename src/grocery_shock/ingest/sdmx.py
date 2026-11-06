"""Parse ABS SDMX-JSON data messages into flat rows.

The combined weight key on this API returns a single quarter per series. Callers
that need the full weight history should request one index code at a time and
pass each payload through `parse_observations`.
"""

from __future__ import annotations


def parse_observations(payload: dict, *, value_field: str = "value") -> list[dict]:
    structure = payload["data"]["structures"][0]
    series_dims = structure["dimensions"]["series"]
    dim_ids = [dim["id"] for dim in series_dims]
    index_dim = series_dims[dim_ids.index("INDEX")]
    time_values = structure["dimensions"]["observation"][0]["values"]
    index_pos = dim_ids.index("INDEX")
    rows: list[dict] = []
    for key, series in payload["data"]["dataSets"][0]["series"].items():
        parts = [int(piece) for piece in key.split(":")]
        meta = index_dim["values"][parts[index_pos]]
        for obs_index, raw in series.get("observations", {}).items():
            if not raw or raw[0] is None or raw[0] == "":
                continue
            rows.append(
                {
                    "index_id": str(meta["id"]),
                    "index_name": meta["name"],
                    "period": time_values[int(obs_index)]["id"],
                    value_field: float(raw[0]),
                }
            )
    return rows
