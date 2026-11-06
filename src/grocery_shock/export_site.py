"""Build the static stakeholder briefing from gold tables and agent traces."""

from __future__ import annotations

import json

from agent.demo import run_questions
from agent.questions import DEMO_QUESTIONS
from agent.tools import substitution_hints
from grocery_shock.format import (
    bare_percent,
    melbourne_stamp,
    period_label,
    prose_change,
    signed_number,
)
from grocery_shock.paths import manifest_path, site_dir
from grocery_shock.warehouse import connect

PATH_IDS = ("114121", "40007", "40009", "40027", "131178")
SWAP_IDS = ("40009", "40001", "114121", "40007")
CONTEXT_IDS = (
    ("10001", "Overall prices"),
    ("20001", "Food and drinks"),
    ("20003", "Housing"),
    ("20005", "Transport"),
    ("40081", "Petrol"),
    ("40055", "Electricity"),
    ("115522", "Rents"),
)


def _rows(connection, sql: str, params: list | None = None) -> list[dict]:
    cursor = connection.execute(sql, params or [])
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _tone_for_change(value: float) -> str:
    if value >= 8:
        return "bad"
    if value >= 4:
        return "watch"
    if value < 0:
        return "good"
    return "calm"


def build_briefing() -> dict:
    connection = connect()
    try:
        headline = _rows(connection, "select * from mart_headline")[0]
        shelf = _rows(
            connection,
            """
            select plain_name, yoy_pct, mom_pct
            from mart_latest
            where shelf = 1 and yoy_pct is not null
            order by yoy_pct desc
            """,
        )
        context = _rows(
            connection,
            """
            select index_id, plain_name, yoy_pct, contribution_pp
            from mart_latest
            where index_id in ({})
            """.format(",".join("'" + item[0] + "'" for item in CONTEXT_IDS)),
        )
        paths = _rows(
            connection,
            """
            select period, index_id, plain_name, yoy_pct
            from mart_category_monthly
            where index_id in ({})
              and period >= '2025-09'
              and yoy_pct is not null
            order by period
            """.format(",".join(f"'{item}'" for item in PATH_IDS)),
        )
        rates = _rows(
            connection,
            """
            select rate_date as date, cash_rate_target
            from stg_cash_rate
            where rate_date >= date '2025-01-01'
            order by rate_date
            """,
        )
        hikes = _rows(
            connection,
            """
            select decision_date, previous_target, cash_rate_target
            from mart_rate_decisions
            where cast(decision_date as varchar) >= '2026-01-01'
              and move = 'hike'
            order by decision_date
            """,
        )
        fruit_aug = _rows(
            connection,
            """
            select yoy_pct from mart_category_monthly
            where index_id = '114121' and period = '2026-08'
            """,
        )[0]["yoy_pct"]
        beef_jul = _rows(
            connection,
            """
            select yoy_pct from mart_category_monthly
            where index_id = '40009' and period = '2026-07'
            """,
        )[0]["yoy_pct"]
    finally:
        connection.close()

    by_id = {row["index_id"]: row for row in context}
    period = headline["period"]
    label = period_label(period)
    manifest = json.loads(manifest_path().read_text())
    access = manifest["access_date"]
    access_label = "6 November 2026"
    rate = float(hikes[-1]["cash_rate_target"])
    before = float(hikes[0]["previous_target"])

    kpis = [
        {
            "label": "Cash rate",
            "value": f"{rate:.2f}%",
            "detail": (
                f"{len(hikes)} rises in 2026, from {before:.2f}% before the first one. "
                "This is the bill on a mortgage, not a grocery price."
            ),
            "tone": "bad",
        },
        {
            "label": "Overall prices",
            "value": signed_number(headline["headline_yoy"]) + "%",
            "detail": f"{label} compared with a year earlier.",
            "tone": _tone_for_change(headline["headline_yoy"]),
        },
        {
            "label": "Food and drinks",
            "value": signed_number(headline["food_yoy"]) + "%",
            "detail": "The whole grocery group is rising more slowly than overall prices.",
            "tone": "calm" if headline["food_yoy"] < headline["headline_yoy"] else "watch",
        },
        {
            "label": "Fruit",
            "value": signed_number(headline["fruit_yoy"]) + "%",
            "detail": (
                f"The sharpest supermarket jump. It was {signed_number(fruit_aug)}% in August."
            ),
            "tone": "bad",
        },
        {
            "label": "Eggs",
            "value": signed_number(headline["eggs_yoy"]) + "%",
            "detail": f"Cheaper than a year ago. Pork is {signed_number(headline['pork_yoy'])}% too.",
            "tone": "good",
        },
    ]

    hero_rows = [
        {
            "name": row["plain_name"],
            "yoy": round(float(row["yoy_pct"]), 1),
            "mom": None if row["mom_pct"] is None else round(float(row["mom_pct"]), 1),
        }
        for row in shelf
    ]
    periods = []
    for row in paths:
        if row["period"] not in periods:
            periods.append(row["period"])
    series = []
    for index_id in PATH_IDS:
        values = []
        name = next(row["plain_name"] for row in paths if row["index_id"] == index_id)
        lookup = {
            row["period"]: round(float(row["yoy_pct"]), 1)
            for row in paths
            if row["index_id"] == index_id
        }
        for month in periods:
            values.append(lookup.get(month))
        series.append({"name": name, "values": values})

    context_rows = []
    for index_id, name in CONTEXT_IDS:
        row = by_id[index_id]
        context_rows.append(
            {
                "name": name,
                "yoy": round(float(row["yoy_pct"]), 1),
                "points": round(float(row["contribution_pp"]), 2),
            }
        )

    swaps = []
    for index_id in SWAP_IDS:
        hint = substitution_hints(_name_for(index_id))
        swaps.append(
            {
                "item": hint["plain_name"],
                "change": prose_change(hint["yoy_pct"]),
                "alternatives": [
                    {"name": item["plain_name"], "change": prose_change(item["yoy_pct"])}
                    for item in hint["alternatives"][:3]
                ],
            }
        )

    traces = run_questions(DEMO_QUESTIONS)
    qa = [
        {"question": trace["question"], "answer": trace["answer"], "checked": trace["citations"]}
        for trace in traces
    ]
    means = (
        f"In {label} the grocery group ({prose_change(headline['food_yoy'])}) is not the main "
        f"source of the national rise ({prose_change(headline['headline_yoy'])}). Housing added "
        f"{float(headline['housing_contribution_pp']):.2f} points and transport added "
        f"{float(headline['transport_contribution_pp']):.2f}, with petrol alone adding "
        f"{float(headline['petrol_contribution_pp']):.2f}. Inside the shop the pain is uneven: "
        f"fruit is {prose_change(headline['fruit_yoy'])} after {bare_percent(fruit_aug)} in August, "
        f"breakfast cereals are {prose_change(headline['cereals_yoy'])}, and beef is still "
        f"{prose_change(headline['beef_yoy'])} but cooler than the {bare_percent(beef_jul)} pace in July. "
        f"Eggs are {prose_change(headline['eggs_yoy'])} and pork is {prose_change(headline['pork_yoy'])}. "
        f"The cash rate at {rate:.2f}% is a separate pressure on mortgages."
    )
    return {
        "period_label": label,
        "access_label": access_label,
        "access_date": access,
        "prepared_label": melbourne_stamp(),
        "lede": (
            f"September 2026 prices, from the {access_label} public release. "
            "Fruit jumped. The average grocery aisle did not."
        ),
        "kpis": kpis,
        "hero": {
            "title": "Fruit and breakfast cereals jumped. Eggs and pork got cheaper.",
            "note": "Change from a year earlier for supermarket lines. Longer bars mean a bigger rise.",
            "rows": hero_rows,
        },
        "paths": {
            "title": "Beef is cooling. Fruit spiked in the latest month.",
            "note": "Each line is the change from the same month a year earlier.",
            "periods": periods,
            "labels": [_short_period(item) for item in periods],
            "series": series,
        },
        "context": {
            "title": "Petrol and housing are doing more of the damage than the grocery aisle.",
            "note": (
                "Bar length is the price change from a year earlier. "
                "The list under the chart is how many points that line added to the national rise. "
                "A big shelf jump can still add very little."
            ),
            "rows": context_rows,
        },
        "cash_rate": {
            "title": f"The cash rate is {rate:.2f}%, after {len(hikes)} rises in 2026.",
            "note": "Daily target. Dots mark the 2026 rises.",
            "points": [
                {"date": _iso(row["date"]), "rate": round(float(row["cash_rate_target"]), 2)}
                for row in rates
            ],
            "hikes": [
                {"date": _iso(row["decision_date"]), "rate": round(float(row["cash_rate_target"]), 2)}
                for row in hikes
            ],
        },
        "swaps": swaps,
        "means": means,
        "qa": qa,
        "sources": [
            {
                "publisher": item["publisher"],
                "name": item["name"],
                "licence": item["licence"],
                "url": item["url"],
            }
            for item in manifest["datasets"]
        ],
    }


def _name_for(index_id: str) -> str:
    names = {
        "40009": "Beef",
        "40001": "Milk",
        "114121": "Fruit",
        "40007": "Breakfast cereals",
    }
    return names[index_id]


def _iso(value) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _short_period(period: str) -> str:
    short = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    year, month = period.split("-")
    return f"{short[int(month) - 1]} {year[2:]}"


def build_site() -> dict:
    briefing = build_briefing()
    folder = site_dir()
    folder.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(briefing, ensure_ascii=False).replace("<", "\\u003c")
    (folder / "data").mkdir(exist_ok=True)
    (folder / "data" / "briefing.json").write_text(payload + "\n")
    template = (folder / "index.template.html").read_text()
    (folder / "index.html").write_text(template.replace("__BRIEFING_JSON__", payload))
    return {"questions": len(briefing["qa"]), "lines": len(briefing["hero"]["rows"])}
