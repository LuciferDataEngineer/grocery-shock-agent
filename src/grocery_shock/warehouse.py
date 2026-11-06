"""DuckDB connections to the gold warehouse."""

from __future__ import annotations

import duckdb

from grocery_shock.paths import warehouse_path


def connect(*, read_only: bool = False, load_vss: bool = False) -> duckdb.DuckDBPyConnection:
    path = warehouse_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(path), read_only=read_only)
    if load_vss:
        if not read_only:
            connection.execute("INSTALL vss;")
        connection.execute("LOAD vss;")
        if not read_only:
            connection.execute("SET hnsw_enable_experimental_persistence = true;")
    return connection
