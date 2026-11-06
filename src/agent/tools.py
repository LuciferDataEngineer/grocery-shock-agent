"""Tools the agent is allowed to call. Every figure comes from DuckDB."""

from __future__ import annotations

import re
from typing import Any

from grocery_shock.format import period_label
from grocery_shock.warehouse import connect

ALLOWED_TABLES = {
    "mart_latest",
    "mart_category_monthly",
    "mart_headline",
    "mart_rate_decisions",
}
BANNED = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|copy|export|import|"
    r"pragma|install|load|call|truncate|grant|revoke|replace|merge|vacuum|"
    r"read_parquet|read_csv|read_json|glob)\b",
    re.I,
)
TABLE_REF = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)", re.I)

SCENARIO = "shift_beef_fruit_to_eggs_pork"
BEEF = "40009"
FRUIT = "114121"
EGGS = "40027"
PORK = "131178"


def _rows(sql: str, params: list | None = None, *, load_vss: bool = False) -> list[dict[str, Any]]:
    connection = connect(read_only=True, load_vss=load_vss)
    try:
        cursor = connection.execute(sql, params or [])
        columns = [item[0] for item in cursor.description]
        records = []
        for row in cursor.fetchall():
            records.append({column: _plain(value) for column, value in zip(columns, row, strict=True)})
        return records
    finally:
        connection.close()


def _plain(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 6)
    return value


def _latest_map() -> dict[str, dict]:
    rows = _rows(
        """
        select index_id, plain_name, family, level, shelf, aisle, period, yoy_pct,
               mom_pct, contribution_pp, weight_pct, weight_period, abs_name
        from mart_latest
        """
    )
    return {row["index_id"]: row for row in rows}


def query_gold_sql(sql: str) -> dict:
    """Run one read-only select against the gold marts."""
    statement = sql.strip().rstrip(";")
    if not statement:
        raise ValueError("SQL is empty")
    if ";" in statement:
        raise ValueError("Only one statement is allowed")
    if BANNED.search(statement):
        raise ValueError("Only read-only selects on the gold marts are allowed")
    if not re.match(r"(?is)^(select|with)\b", statement):
        raise ValueError("Only SELECT statements are allowed")
    tables = [name.split(".")[-1].lower() for name in TABLE_REF.findall(statement)]
    if not tables or any(name not in ALLOWED_TABLES for name in tables):
        raise ValueError("Query must read only the gold marts")
    wrapped = f"select * from ({statement}) as gold_query limit 200"
    rows = _rows(wrapped)
    return {"row_count": len(rows), "rows": rows}


def get_kpi_snapshot() -> dict:
    headline = _rows("select * from mart_headline")[0]
    latest = _rows(
        """
        select decision_date, cash_rate_target, previous_target, change_from_level,
               cash_rate_change_published, move
        from mart_rate_decisions
        order by decision_date
        """
    )
    hikes_2026 = [
        row
        for row in latest
        if str(row["decision_date"]).startswith("2026") and row["move"] == "hike"
    ]
    current = hikes_2026[-1] if hikes_2026 else latest[-1]
    return {
        "period": headline["period"],
        "period_label": period_label(headline["period"]),
        "headline_yoy": headline["headline_yoy"],
        "food_yoy": headline["food_yoy"],
        "housing_yoy": headline["housing_yoy"],
        "transport_yoy": headline["transport_yoy"],
        "petrol_yoy": headline["petrol_yoy"],
        "electricity_yoy": headline["electricity_yoy"],
        "rents_yoy": headline["rents_yoy"],
        "fruit_yoy": headline["fruit_yoy"],
        "beef_yoy": headline["beef_yoy"],
        "cereals_yoy": headline["cereals_yoy"],
        "eggs_yoy": headline["eggs_yoy"],
        "pork_yoy": headline["pork_yoy"],
        "poultry_yoy": headline["poultry_yoy"],
        "milk_yoy": headline["milk_yoy"],
        "food_contribution_pp": headline["food_contribution_pp"],
        "housing_contribution_pp": headline["housing_contribution_pp"],
        "transport_contribution_pp": headline["transport_contribution_pp"],
        "petrol_contribution_pp": headline["petrol_contribution_pp"],
        "fruit_contribution_pp": headline["fruit_contribution_pp"],
        "electricity_contribution_pp": headline["electricity_contribution_pp"],
        "meals_out_contribution_pp": headline["meals_out_contribution_pp"],
        "cash_rate_target": current["cash_rate_target"],
        "cash_rate_date": current["decision_date"],
        "hikes_2026": len(hikes_2026),
        "rate_before_2026_rises": hikes_2026[0]["previous_target"] if hikes_2026 else None,
        "rate_path_2026": hikes_2026,
        "latest_decision": hikes_2026[-1] if hikes_2026 else None,
    }


def rank_categories(metric: str = "yoy", n: int = 5, direction: str = "worst", scope: str = "shelf") -> dict:
    if metric != "yoy":
        raise ValueError("Only the published yearly change is ranked")
    if direction not in {"worst", "best"}:
        raise ValueError("direction must be worst or best")
    if scope != "shelf":
        raise ValueError("scope must be shelf")
    count = max(1, min(int(n), 12))
    order = "desc" if direction == "worst" else "asc"
    rows = _rows(
        f"""
        select plain_name, index_id, yoy_pct, mom_pct, contribution_pp, weight_pct, period
        from mart_latest
        where shelf = 1 and yoy_pct is not null
        order by yoy_pct {order}
        limit ?
        """,
        [count],
    )
    relief = _rows(
        """
        select plain_name, index_id, yoy_pct
        from mart_latest
        where shelf = 1 and yoy_pct is not null
        order by yoy_pct asc
        limit 3
        """
    )
    headline = _rows("select period, food_yoy, headline_yoy from mart_headline")[0]
    return {
        "period": headline["period"],
        "period_label": period_label(headline["period"]),
        "direction": direction,
        "food_yoy": headline["food_yoy"],
        "headline_yoy": headline["headline_yoy"],
        "rows": rows,
        "relief": relief,
    }


def _resolve_category(category: str, catalog: dict[str, dict]) -> dict:
    needle = category.strip().lower()
    by_name = {row["plain_name"].lower(): row for row in catalog.values()}
    aliases = {
        "beef": "40009",
        "veal": "40009",
        "pork": "131178",
        "chicken": "40012",
        "poultry": "40012",
        "lamb": "40010",
        "fish": "40015",
        "fruit": "114121",
        "vegetables": "114122",
        "veg": "114122",
        "milk": "40001",
        "cheese": "40002",
        "eggs": "40027",
        "egg": "40027",
        "bread": "40005",
        "breakfast cereals": "40007",
        "cereal": "40007",
        "cereals": "40007",
        "coffee": "40030",
        "tea": "40030",
        "petrol": "40081",
        "fuel": "40081",
        "soft drinks": "115520",
        "takeaway": "40026",
        "restaurant": "40025",
    }
    if needle in by_name:
        return by_name[needle]
    if needle in aliases and aliases[needle] in catalog:
        return catalog[aliases[needle]]
    if needle in catalog:
        return catalog[needle]
    for name, row in sorted(by_name.items(), key=lambda item: len(item[0]), reverse=True):
        if name in needle:
            return row
    raise ValueError(f"No published line matches {category}")


def substitution_hints(category: str) -> dict:
    catalog = _latest_map()
    chosen = _resolve_category(category, catalog)
    family = [
        row
        for row in catalog.values()
        if row["family"] == chosen["family"]
        and row["level"] == "class"
        and row["aisle"] != "rollup"
        and row["index_id"] != chosen["index_id"]
        and row["yoy_pct"] is not None
        and row["yoy_pct"] < chosen["yoy_pct"]
    ]
    family.sort(key=lambda row: row["yoy_pct"])
    alternatives = [
        {
            "plain_name": row["plain_name"],
            "index_id": row["index_id"],
            "yoy_pct": row["yoy_pct"],
            "gap_pp": round(row["yoy_pct"] - chosen["yoy_pct"], 4),
        }
        for row in family[:4]
    ]
    return {
        "period": chosen["period"],
        "period_label": period_label(chosen["period"]),
        "plain_name": chosen["plain_name"],
        "index_id": chosen["index_id"],
        "family": chosen["family"],
        "yoy_pct": chosen["yoy_pct"],
        "alternatives": alternatives,
        "note": "Relative published price changes only. Not diet advice.",
    }


def _supermarket(catalog: dict[str, dict]) -> list[dict]:
    rows = [
        row
        for row in catalog.values()
        if row["shelf"] == 1 and row["weight_pct"] is not None and row["yoy_pct"] is not None
    ]
    if not rows:
        raise ValueError("Supermarket weights are missing")
    return rows


def _weighted(rows: list[dict], weights: dict[str, float]) -> float:
    total = sum(weights[row["index_id"]] for row in rows)
    if total == 0:
        raise ValueError("Basket weights sum to zero")
    return sum(weights[row["index_id"]] * row["yoy_pct"] for row in rows) / total


def what_if_basket(scenario: str | None = None, weights: dict | None = None) -> dict:
    catalog = _latest_map()
    rows = _supermarket(catalog)
    base_weights = {row["index_id"]: float(row["weight_pct"]) for row in rows}
    weight_period = rows[0]["weight_period"]
    period = rows[0]["period"]
    baseline = _weighted(rows, base_weights)
    applied = dict(base_weights)
    scenario_name = scenario or "custom_weights"
    if weights:
        for key, share in weights.items():
            if key in catalog:
                index_id = key
            else:
                index_id = _resolve_category(str(key), catalog)["index_id"]
            if index_id not in base_weights:
                raise ValueError(f"{key} is not in the supermarket basket")
            applied[index_id] = float(share)
    elif scenario == SCENARIO:
        applied[BEEF] = base_weights[BEEF] * 0.5
        applied[FRUIT] = base_weights[FRUIT] * 0.5
        moved = (base_weights[BEEF] - applied[BEEF]) + (base_weights[FRUIT] - applied[FRUIT])
        applied[EGGS] = base_weights[EGGS] + moved / 2
        applied[PORK] = base_weights[PORK] + moved / 2
    else:
        scenario_name = "baseline"
    scenario_yoy = _weighted(rows, applied)
    return {
        "period": period,
        "period_label": period_label(period),
        "weight_period": weight_period,
        "scenario": scenario_name,
        "baseline_yoy": round(baseline, 4),
        "scenario_yoy": round(scenario_yoy, 4),
        "difference_pp": round(scenario_yoy - baseline, 4),
        "beef_yoy": catalog[BEEF]["yoy_pct"],
        "fruit_yoy": catalog[FRUIT]["yoy_pct"],
        "eggs_yoy": catalog[EGGS]["yoy_pct"],
        "pork_yoy": catalog[PORK]["yoy_pct"],
    }


def retrieve_insights(query: str, k: int = 3) -> dict:
    from grocery_shock.embed import DIM, embed

    vector = embed(query)
    limit = max(1, min(int(k), 8))
    rows = _rows(
        f"""
        select doc_id, title, body,
               array_cosine_distance(embedding, ?::FLOAT[{DIM}]) as distance
        from memory.insight_chunks
        order by distance
        limit ?
        """,
        [vector, limit],
        load_vss=True,
    )
    return {"query": query, "matches": rows}


TOOLS = {
    "query_gold_sql": query_gold_sql,
    "get_kpi_snapshot": get_kpi_snapshot,
    "rank_categories": rank_categories,
    "substitution_hints": substitution_hints,
    "retrieve_insights": retrieve_insights,
    "what_if_basket": what_if_basket,
}


def call_tool(name: str, arguments: dict) -> dict:
    if name not in TOOLS:
        raise ValueError(f"Unknown tool {name}")
    return TOOLS[name](**arguments)
