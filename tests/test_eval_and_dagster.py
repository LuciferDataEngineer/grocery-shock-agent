from agent.evaluate import run_eval
from orchestration.definitions import defs


def test_eval_recall_and_answers(built):
    report = run_eval()
    assert report["failures"] == []
    assert report["recall_at_3"] == 1


def test_dagster_graph_loads(built):
    keys = {key.to_user_string() for key in defs.resolve_asset_graph().get_all_asset_keys()}
    assert "bronze_snapshot" in keys
    assert "stakeholder_site" in keys
    assert defs.get_job_def("grocery_briefing") is not None
