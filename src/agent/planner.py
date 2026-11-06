"""Choose the next tool from the question and the observations so far.

The planner never supplies a figure. It only chooses a tool and its arguments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from agent.tools import SCENARIO

RANK = re.compile(r"hurt|worst|sharpest|hottest|which food|food categor", re.I)
SUBSTITUTE = re.compile(r"substitut|swap|instead of|alternative", re.I)
WHATIF = re.compile(r"what if|shift(?:s|ing)? spend|scenario", re.I)
POLICY = re.compile(r"policymaker|watch next|should watch|what to watch", re.I)
COMPARE = re.compile(r"compar|versus|transport and housing|housing and transport", re.I)
KPI = re.compile(r"cash rate|headline|how bad|overview|mortgage", re.I)
PATH = re.compile(r"over the past|each month|month by month|how has", re.I)

ALIASES = [
    ("breakfast cereals", "40007"),
    ("soft drinks", "115520"),
    ("coffee", "40030"),
    ("beef", "40009"),
    ("pork", "131178"),
    ("poultry", "40012"),
    ("chicken", "40012"),
    ("lamb", "40010"),
    ("fish", "40015"),
    ("fruit", "114121"),
    ("vegetables", "114122"),
    ("milk", "40001"),
    ("cheese", "40002"),
    ("eggs", "40027"),
    ("bread", "40005"),
    ("petrol", "40081"),
    ("fuel", "40081"),
    ("takeaway", "40026"),
    ("restaurant", "40025"),
]


@dataclass
class Decision:
    kind: str
    thought: str = ""
    tool: str = ""
    arguments: dict[str, Any] | None = None


def _category_id(question: str) -> str | None:
    lowered = question.lower()
    for alias, index_id in ALIASES:
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            return index_id
    return None


def _intents(question: str) -> set[str]:
    found = set()
    if RANK.search(question):
        found.add("rank")
    if SUBSTITUTE.search(question):
        found.add("substitute")
    if WHATIF.search(question):
        found.add("whatif")
    if POLICY.search(question):
        found.add("policy")
    if COMPARE.search(question):
        found.add("compare")
    if KPI.search(question):
        found.add("kpi")
    if PATH.search(question):
        found.add("path")
    return found


def decide(question: str, called: set[str]) -> Decision:
    intents = _intents(question)
    category = _category_id(question)

    if "rank" in intents and "rank_categories" not in called:
        return Decision(
            kind="action",
            thought=(
                "The question asks which shelf prices rose fastest, so I need the "
                "latest published yearly changes for supermarket lines."
            ),
            tool="rank_categories",
            arguments={"metric": "yoy", "n": 5, "direction": "worst", "scope": "shelf"},
        )
    if "substitute" in intents and "substitution_hints" not in called:
        return Decision(
            kind="action",
            thought=(
                "The question asks for a substitute, so I need the same aisle's "
                "published yearly changes, not a guess."
            ),
            tool="substitution_hints",
            arguments={"category": category or "beef"},
        )
    if "whatif" in intents and "what_if_basket" not in called:
        scenario = None
        lowered = question.lower()
        if any(word in lowered for word in ("egg", "pork")) and any(
            word in lowered for word in ("beef", "fruit")
        ):
            scenario = SCENARIO
        return Decision(
            kind="action",
            thought=(
                "The question asks for a basket shift, so I need to reweight the "
                "published price changes with the published basket weights."
            ),
            tool="what_if_basket",
            arguments={"scenario": scenario} if scenario else {},
        )
    needs_snapshot = bool(intents & {"policy", "compare", "kpi"}) or not intents
    if needs_snapshot and "get_kpi_snapshot" not in called and "rank" not in intents:
        return Decision(
            kind="action",
            thought="I need the latest published headline figures before answering.",
            tool="get_kpi_snapshot",
            arguments={},
        )
    if "policy" in intents and "retrieve_insights" not in called:
        return Decision(
            kind="action",
            thought="I will check the stored briefing notes for what to watch next.",
            tool="retrieve_insights",
            arguments={"query": question, "k": 3},
        )
    if "path" in intents and category and "query_gold_sql" not in called:
        return Decision(
            kind="action",
            thought="I need the published monthly path for that line, not a single month.",
            tool="query_gold_sql",
            arguments={
                "sql": (
                    "select period, plain_name, yoy_pct from mart_category_monthly "
                    f"where index_id = '{category}' and yoy_pct is not null "
                    "and period >= '2025-09' order by period"
                )
            },
        )
    return Decision(
        kind="final",
        thought="The published figures I need are already in the observations.",
    )
