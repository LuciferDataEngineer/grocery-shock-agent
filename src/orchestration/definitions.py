"""Asset graph. The same functions back the Makefile."""

from dagster import AssetExecutionContext, Definitions, asset, define_asset_job


@asset(group_name="grocery")
def bronze_snapshot(context: AssetExecutionContext) -> dict:
    from grocery_shock.ingest.bronze import build_bronze

    stats = build_bronze()
    context.log.info("bronze rows %s", stats)
    return stats


@asset(deps=[bronze_snapshot], group_name="grocery")
def expectation_results() -> dict:
    from grocery_shock.quality.suite import run_quality

    return run_quality()


@asset(deps=[expectation_results], group_name="grocery")
def gold_marts() -> str:
    from grocery_shock.transform import run_dbt

    run_dbt()
    return "gold"


@asset(deps=[gold_marts], group_name="grocery")
def insight_index() -> int:
    from grocery_shock.insights import write_insights
    from grocery_shock.vectors import build_vector_index

    write_insights()
    return build_vector_index()


@asset(deps=[insight_index], group_name="grocery")
def stakeholder_site() -> dict:
    from grocery_shock.export_site import build_site

    return build_site()


grocery_briefing = define_asset_job(name="grocery_briefing", selection="*")

defs = Definitions(
    assets=[bronze_snapshot, expectation_results, gold_marts, insight_index, stakeholder_site],
    jobs=[grocery_briefing],
)
