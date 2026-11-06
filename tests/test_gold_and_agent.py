import pytest

from agent.react import run_agent
from agent.tools import SCENARIO, query_gold_sql, what_if_basket
from grocery_shock.format import prose_change
from grocery_shock.warehouse import connect


def test_published_september_figures(built):
    connection = connect()
    try:
        row = connection.execute(
            """
            select period, headline_yoy, food_yoy, fruit_yoy, beef_yoy, transport_yoy
            from mart_headline
            """
        ).fetchone()
    finally:
        connection.close()
    assert row[0] == "2026-09"
    assert row[1:] == pytest.approx((4.3, 3.2, 10.2, 5.8, 8.7))
    assert built["indexed"] >= 8


def test_five_2026_hikes_and_blank_september_change(built):
    connection = connect()
    try:
        rows = connection.execute(
            """
            select decision_date, cash_rate_target, cash_rate_change_published
            from mart_rate_decisions
            where move = 'hike' and cast(decision_date as varchar) >= '2026-01-01'
            order by decision_date
            """
        ).fetchall()
    finally:
        connection.close()
    assert len(rows) == 5
    assert rows[-1][1] == pytest.approx(4.85)
    september = next(row for row in rows if str(row[0]).startswith("2026-09-30"))
    assert september[2] is None


def test_sql_tool_is_read_only(built):
    with pytest.raises(ValueError):
        query_gold_sql("drop table mart_latest")
    with pytest.raises(ValueError):
        query_gold_sql("select 1; select 2")
    result = query_gold_sql(
        "select plain_name, yoy_pct from mart_latest where index_id = '114121'"
    )
    assert result["rows"][0]["plain_name"] == "Fruit"
    assert result["rows"][0]["yoy_pct"] == pytest.approx(10.2)


def test_agent_happy_path_uses_tools_and_real_numbers(built):
    trace = run_agent("Which food categories hurt most?")
    assert trace["tools_used"] == ["rank_categories"]
    assert "Fruit" in trace["answer"]
    assert "10.2" in trace["answer"]
    assert "Breakfast cereals" in trace["answer"]
    observations = [step for step in trace["steps"] if step["kind"] == "observation"]
    assert observations[0]["ok"] is True
    assert observations[0]["payload"]["rows"][0]["yoy_pct"] == pytest.approx(10.2)


def test_what_if_answer_quotes_the_tool(built):
    scenario = what_if_basket(scenario=SCENARIO)
    trace = run_agent(
        "What if a household shifts spend from beef and fruit toward eggs and pork?"
    )
    assert "what_if_basket" in trace["tools_used"]
    assert prose_change(scenario["scenario_yoy"]) in trace["answer"]
    assert prose_change(scenario["baseline_yoy"]) in trace["answer"]


def test_dashboard_is_stakeholder_language(built):
    from grocery_shock.paths import site_dir

    page = (site_dir() / "index.html").read_text()
    assert "Fruit" in page
    assert "10.2" in page
    assert "4.85" in page
    for banned in ("DuckDB", "dbt", "LangGraph", "Great Expectations", "schema", "YoY"):
        assert banned not in page
    assert (site_dir() / "index.html").exists()
    insights = (site_dir().parents[0] / "INSIGHTS.md").read_text()
    assert "4.85" in insights
    assert "10.2" in insights
