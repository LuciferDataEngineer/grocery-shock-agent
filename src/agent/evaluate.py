"""Recall and answer checks that do not call a paid model."""

from __future__ import annotations

from agent.questions import DEMO_QUESTIONS
from agent.react import run_agent
from agent.tools import retrieve_insights

CASES = [
    {
        "question": DEMO_QUESTIONS[0],
        "tools": ["rank_categories"],
        "contains": ["Fruit", "10.2", "Breakfast cereals"],
    },
    {
        "question": DEMO_QUESTIONS[1],
        "tools": ["substitution_hints"],
        "contains": ["Beef", "Pork", "1.3"],
    },
    {
        "question": DEMO_QUESTIONS[2],
        "tools": ["get_kpi_snapshot", "retrieve_insights"],
        "contains": ["4.85", "23.6", "petrol"],
    },
    {
        "question": DEMO_QUESTIONS[3],
        "tools": ["what_if_basket"],
        "contains": ["eggs", "pork", "percentage points"],
    },
    {
        "question": DEMO_QUESTIONS[4],
        "tools": ["get_kpi_snapshot"],
        "contains": ["3.2", "8.7", "5.2"],
    },
]

RECALL = [
    ("fruit price spike september", "fruit-spike"),
    ("cash rate mortgage hikes", "cash-rate"),
    ("pork poultry substitute beef", "protein-swaps"),
    ("petrol electricity policymakers watch", "watch-next"),
]


def run_eval() -> dict:
    failures: list[str] = []
    traces = []
    for case in CASES:
        trace = run_agent(case["question"])
        traces.append(trace)
        missing_tools = [name for name in case["tools"] if name not in trace["tools_used"]]
        if missing_tools:
            failures.append(f"{case['question']} missing tools {missing_tools}")
        answer = trace["answer"]
        for needle in case["contains"]:
            if needle not in answer:
                failures.append(f"{case['question']} answer missing {needle!r}")
        if "estimate" in answer.lower() or "I guess" in answer:
            failures.append(f"{case['question']} answer is not grounded")
        observations = [step for step in trace["steps"] if step["kind"] == "observation"]
        if any(not step.get("ok") for step in observations):
            failures.append(f"{case['question']} had a failed tool call")
    hits = 0
    for query, expected in RECALL:
        matches = retrieve_insights(query, k=3)["matches"]
        found = [row["doc_id"] for row in matches]
        if expected in found:
            hits += 1
        else:
            failures.append(f"recall miss for {query!r}: got {found}")
    recall = hits / len(RECALL)
    return {
        "cases": len(CASES),
        "recall_at_3": recall,
        "failures": failures,
        "passed": not failures and recall == 1,
    }


def main() -> None:
    report = run_eval()
    print(report)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
