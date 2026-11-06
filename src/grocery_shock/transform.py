"""Run the dbt-duckdb project that builds silver views and gold marts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from grocery_shock.paths import bronze_dir, dbt_dir, warehouse_path


def run_dbt() -> None:
    warehouse = warehouse_path()
    warehouse.parent.mkdir(parents=True, exist_ok=True)
    dbt_bin = Path(sys.executable).parent / "dbt"
    if not dbt_bin.exists():
        dbt_bin = Path("dbt")
    env = os.environ.copy()
    env["GROCERY_DUCKDB"] = str(warehouse)
    env["GROCERY_BRONZE"] = str(bronze_dir())
    project = str(dbt_dir())
    for command in (["seed"], ["build"]):
        completed = subprocess.run(
            [str(dbt_bin), *command, "--project-dir", project, "--profiles-dir", project],
            check=False,
            env=env,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"dbt {' '.join(command)} failed\n{completed.stdout}\n{completed.stderr}"
            )
