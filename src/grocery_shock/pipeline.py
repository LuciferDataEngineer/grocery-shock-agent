"""Run the briefing from the committed snapshot through to the static site."""

from __future__ import annotations

from grocery_shock.export_site import build_site
from grocery_shock.ingest.bronze import build_bronze
from grocery_shock.insights import write_insights
from grocery_shock.quality.suite import run_quality
from grocery_shock.transform import run_dbt
from grocery_shock.vectors import build_vector_index


def run_all() -> dict:
    bronze = build_bronze()
    quality = run_quality()
    run_dbt()
    notes = write_insights()
    indexed = build_vector_index()
    site = build_site()
    return {
        "bronze": bronze,
        "quality": quality,
        "notes": notes,
        "indexed": indexed,
        "site": site,
    }


def main(argv: list[str] | None = None) -> None:
    command = (argv or ["all"])[0]
    if command in {"all", "dashboard", "transform"}:
        if command == "transform":
            build_bronze()
            run_quality()
            run_dbt()
            return
        print(run_all())
        return
    if command == "quality":
        build_bronze()
        print(run_quality())
        return
    raise SystemExit(f"Unknown command {command}")


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
