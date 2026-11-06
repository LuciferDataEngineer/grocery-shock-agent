"""Turn tool payloads into sentences. No number is introduced here."""

from __future__ import annotations

from grocery_shock.format import period_label, prose_change, weight_period_label


def _join(parts: list[str]) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def render(payloads: dict[str, dict]) -> dict:
    paragraphs: list[str] = []
    citations: list[str] = []

    if "get_kpi_snapshot" in payloads:
        text, used = _kpi(payloads["get_kpi_snapshot"], broad="rank_categories" not in payloads)
        paragraphs.append(text)
        citations.extend(used)
    if "rank_categories" in payloads:
        text, used = _rank(payloads["rank_categories"])
        paragraphs.append(text)
        citations.extend(used)
    if "substitution_hints" in payloads:
        text, used = _swap(payloads["substitution_hints"])
        paragraphs.append(text)
        citations.extend(used)
    if "what_if_basket" in payloads:
        text, used = _what_if(payloads["what_if_basket"])
        paragraphs.append(text)
        citations.extend(used)
    if "query_gold_sql" in payloads and payloads["query_gold_sql"].get("rows"):
        text, used = _path(payloads["query_gold_sql"])
        paragraphs.append(text)
        citations.extend(used)
    if "retrieve_insights" in payloads:
        titles = [match["title"] for match in payloads["retrieve_insights"].get("matches", [])]
        if titles:
            paragraphs.append(
                "The briefing notes point to the same watch list: petrol, power bills, "
                "housing, and the cash rate, ahead of the average supermarket aisle."
            )
            citations.extend(titles)

    if not paragraphs:
        paragraphs.append("I could not find a published figure for that question.")
    return {"answer": " ".join(paragraphs), "citations": citations}


def _kpi(payload: dict, *, broad: bool) -> tuple[str, list[str]]:
    rate = f"{float(payload['cash_rate_target']):.2f}%"
    before = payload.get("rate_before_2026_rises")
    before_text = f"{float(before):.2f}%" if before is not None else "the prior target"
    core = (
        f"In {payload['period_label']}, overall prices were {prose_change(payload['headline_yoy'])}. "
        f"Food and drinks were {prose_change(payload['food_yoy'])} and added "
        f"{float(payload['food_contribution_pp']):.2f} points to the national yearly rise. "
        f"Housing was {prose_change(payload['housing_yoy'])} and added "
        f"{float(payload['housing_contribution_pp']):.2f} points. "
        f"Transport was {prose_change(payload['transport_yoy'])} and added "
        f"{float(payload['transport_contribution_pp']):.2f} points, with petrol "
        f"{prose_change(payload['petrol_yoy'])} and adding "
        f"{float(payload['petrol_contribution_pp']):.2f} points. "
        f"Electricity was {prose_change(payload['electricity_yoy'])} and rents were "
        f"{prose_change(payload['rents_yoy'])}. "
        f"The cash rate target is {rate} after {payload['hikes_2026']} rises in 2026, "
        f"from {before_text} before the first rise. "
        "Mortgage repayments are not part of the grocery price index."
    )
    if not broad:
        core = (
            f"The cash rate target is {rate}. Overall prices were "
            f"{prose_change(payload['headline_yoy'])} and food and drinks were "
            f"{prose_change(payload['food_yoy'])}."
        )
    citations = [
        f"Overall prices {prose_change(payload['headline_yoy'])}",
        f"Food and drinks {prose_change(payload['food_yoy'])}",
        f"Housing {prose_change(payload['housing_yoy'])}",
        f"Transport {prose_change(payload['transport_yoy'])}",
        f"Petrol {prose_change(payload['petrol_yoy'])}",
        f"Cash rate {rate}",
    ]
    return core, citations


def _rank(payload: dict) -> tuple[str, list[str]]:
    worst = [
        f"{row['plain_name']} ({prose_change(row['yoy_pct'])})" for row in payload["rows"]
    ]
    relief = [
        f"{row['plain_name']} ({prose_change(row['yoy_pct'])})" for row in payload["relief"]
    ]
    text = (
        f"In {payload['period_label']}, the sharpest rises on the supermarket shelf were "
        f"{_join(worst)}. Food and drinks as a whole were {prose_change(payload['food_yoy'])}, "
        f"slower than overall prices, which were {prose_change(payload['headline_yoy'])}. "
        f"The lines that eased were {_join(relief)}."
    )
    citations = [
        f"{row['plain_name']} {prose_change(row['yoy_pct'])}"
        for row in [*payload["rows"], *payload["relief"]]
    ]
    return text, citations


def _swap(payload: dict) -> tuple[str, list[str]]:
    if not payload["alternatives"]:
        text = (
            f"{payload['plain_name']} was {prose_change(payload['yoy_pct'])} in "
            f"{payload['period_label']}, and no other line in that aisle was rising more slowly."
        )
        return text, [f"{payload['plain_name']} {prose_change(payload['yoy_pct'])}"]
    options = [
        f"{row['plain_name']} ({prose_change(row['yoy_pct'])})" for row in payload["alternatives"]
    ]
    text = (
        f"{payload['plain_name']} was {prose_change(payload['yoy_pct'])} in "
        f"{payload['period_label']}. In the same part of the shop, slower price rises were "
        f"{_join(options)}. {payload['note']}"
    )
    citations = [f"{payload['plain_name']} {prose_change(payload['yoy_pct'])}"]
    citations.extend(
        f"{row['plain_name']} {prose_change(row['yoy_pct'])}" for row in payload["alternatives"]
    )
    return text, citations


def _what_if(payload: dict) -> tuple[str, list[str]]:
    gap = float(payload["difference_pp"])
    if abs(gap) < 0.05:
        change = "The basket's yearly rise barely changes."
    elif gap < 0:
        change = f"That trims the basket's yearly rise by {abs(gap):.1f} percentage points."
    else:
        change = f"That adds {gap:.1f} percentage points to the basket's yearly rise."
    text = (
        f"Using the {weight_period_label(payload['weight_period'])} basket weights, "
        "a supermarket basket weighted "
        f"like the national shopping basket was {prose_change(payload['baseline_yoy'])} in "
        f"{payload['period_label']}. "
    )
    if payload["scenario"] == "shift_beef_fruit_to_eggs_pork":
        text += (
            "Moving half of the beef weight and half of the fruit weight onto eggs and pork, "
            f"split evenly, leaves that basket {prose_change(payload['scenario_yoy'])}. {change} "
            f"Beef was {prose_change(payload['beef_yoy'])}, fruit {prose_change(payload['fruit_yoy'])}, "
            f"eggs {prose_change(payload['eggs_yoy'])}, and pork {prose_change(payload['pork_yoy'])}."
        )
    else:
        text += (
            f"The reweighted basket was {prose_change(payload['scenario_yoy'])}. {change}"
        )
    citations = [
        f"Baseline basket {prose_change(payload['baseline_yoy'])}",
        f"Shifted basket {prose_change(payload['scenario_yoy'])}",
        f"Difference {gap:.1f} percentage points",
    ]
    return text, citations


def _path(payload: dict) -> tuple[str, list[str]]:
    rows = payload["rows"]
    first, last = rows[0], rows[-1]
    text = (
        f"{last['plain_name']} was {prose_change(last['yoy_pct'])} in {period_label(last['period'])}. "
        f"In {period_label(first['period'])} it was {prose_change(first['yoy_pct'])}."
    )
    citations = [
        f"{period_label(row['period'])} {prose_change(row['yoy_pct'])}" for row in (first, last)
    ]
    return text, citations
