import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("GROCERY_ROOT", str(ROOT))
os.environ.setdefault("GX_ANALYTICS_ENABLED", "false")
os.environ.setdefault("TQDM_DISABLE", "1")


@pytest.fixture(scope="session")
def built():
    from grocery_shock.pipeline import run_all

    return run_all()
