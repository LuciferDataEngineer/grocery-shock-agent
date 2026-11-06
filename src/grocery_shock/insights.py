"""Write retrieval notes and the decision memo from gold tables only."""

from __future__ import annotations

from grocery_shock.format import bare_percent, period_label, prose_change
from grocery_shock.paths import insights_dir, project_root
from grocery_shock.warehouse import connect


def _one(connection, sql: str, params: list | None = None) -> dict:
    cursor = connection.execute(sql, params or [])
    columns = [item[0] for item in cursor.description]
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"missing row for {sql}")
    return dict(zip(columns, row, strict=True))


def _load() -> dict:
    connection = connect()
    try:
        headline = _one(connection, "select * from mart_headline")
        latest_rate = _one(
            connection,
            """
            select cash_rate_target, rate_date as date
            from stg_cash_rate
            order by rate_date desc
            limit 1
            """,
        )
        hikes = connection.execute(
            """
            select decision_date, previous_target, cash_rate_target,
                   change_from_level, cash_rate_change_published
            from mart_rate_decisions
            where cast(decision_date as varchar) like '2026%'
              and move = 'hike'
            order by decision_date
            """
        ).fetchall()
        fruit_aug = _one(
            connection,
            """
            select yoy_pct from mart_category_monthly
            where index_id = '114121' and period = '2026-08'
            """,
        )["yoy_pct"]
        beef_jul = _one(
            connection,
            """
            select yoy_pct from mart_category_monthly
            where index_id = '40009' and period = '2026-07'
            """,
        )["yoy_pct"]
        lines = {
            row[0]: row[1]
            for row in connection.execute(
                """
                select index_id, yoy_pct from mart_latest
                where index_id in (
                    '114122', '40012', '40010', '40015', '40002', '40005',
                    '40006', '40030', '115501', '40025', '40026', '40001'
                )
                """
            ).fetchall()
        }
    finally:
        connection.close()
    return {
        "headline": headline,
        "latest_rate": latest_rate,
        "hikes": hikes,
        "fruit_aug": fruit_aug,
        "beef_jul": beef_jul,
        "lines": lines,
    }


def _pct(value: float) -> str:
    return f"{float(value):.1f}%"


def _points(value: float) -> str:
    return f"{float(value):.2f}"


def build_documents(facts: dict) -> list[dict[str, str]]:
    h = facts["headline"]
    lines = facts["lines"]
    period = period_label(h["period"])
    rate = f"{float(facts['latest_rate']['cash_rate_target']):.2f}"
    hike_count = len(facts["hikes"])
    start_rate = f"{float(facts['hikes'][0][1]):.2f}" if facts["hikes"] else "n/a"
    blank = next(
        (
            hike
            for hike in facts["hikes"]
            if hike[4] is None
        ),
        None,
    )
    blank_sentence = ""
    if blank is not None:
        blank_sentence = (
            f" The {blank[0]} move to {float(blank[2]):.2f} percent shows up in the "
            "target and the overnight rate; the published change column for that day is blank."
        )
    docs = [
        {
            "doc_id": "fruit-spike",
            "title": "Fruit price spike in September",
            "body": (
                f"Fruit prices were {prose_change(h['fruit_yoy'])} in {period} compared with a year "
                f"earlier, after {bare_percent(facts['fruit_aug'])} in August. Vegetables were "
                f"{prose_change(lines['114122'])}. Fruit added {_points(h['fruit_contribution_pp'])} "
                "points to the national yearly rise because it is a small share of the basket. "
                "Households feel the shelf price. The national index barely moves."
            ),
        },
        {
            "doc_id": "protein-swaps",
            "title": "Beef, pork, poultry and eggs",
            "body": (
                f"Beef was {prose_change(h['beef_yoy'])} in {period}, after "
                f"a {bare_percent(facts['beef_jul'])} pace in July, so it is cooling. "
                f"Pork was {prose_change(h['pork_yoy'])}. Poultry was {prose_change(h['poultry_yoy'])}. "
                f"Lamb was {prose_change(lines['40010'])}. Fish was {prose_change(lines['40015'])}. "
                f"Eggs were {prose_change(h['eggs_yoy'])}. A household looking for a cheaper protein "
                "than beef can look at pork, poultry, and fish on price alone. Eggs are the relief "
                "line in the same shop. This is a price signal, not diet advice."
            ),
        },
        {
            "doc_id": "cereals-milk",
            "title": "Breakfast cereals and milk",
            "body": (
                f"Breakfast cereals were {prose_change(h['cereals_yoy'])} in {period}. "
                f"Milk was {prose_change(h['milk_yoy'])}. Cheese was {prose_change(lines['40002'])}. "
                f"Bread was {prose_change(lines['40005'])}. The cereal aisle and the milk fridge are "
                f"still hot even though the food group was {prose_change(h['food_yoy'])}."
            ),
        },
        {
            "doc_id": "food-versus-headline",
            "title": "Food group versus overall prices",
            "body": (
                f"Overall prices were {prose_change(h['headline_yoy'])} in {period}. Food and "
                f"non-alcoholic beverages were {prose_change(h['food_yoy'])} and added "
                f"{_points(h['food_contribution_pp'])} points to the national yearly rise. "
                "The grocery group is rising more slowly than overall prices. The pain is uneven "
                "inside the basket."
            ),
        },
        {
            "doc_id": "watch-next",
            "title": "What policymakers should watch next",
            "body": (
                "Policymakers should watch petrol, electricity, housing, and the cash rate ahead of "
                f"the average supermarket aisle. Petrol was {prose_change(h['petrol_yoy'])} and added "
                f"{_points(h['petrol_contribution_pp'])} points. Transport was "
                f"{prose_change(h['transport_yoy'])} and added {_points(h['transport_contribution_pp'])} "
                f"points. Housing was {prose_change(h['housing_yoy'])} and added "
                f"{_points(h['housing_contribution_pp'])} points. Electricity was "
                f"{prose_change(h['electricity_yoy'])}. Rents were {prose_change(h['rents_yoy'])}. "
                f"The cash rate target is {rate} percent after {hike_count} rises in 2026. "
                "Fruit's shelf jump is real for households but small in the national index."
            ),
        },
        {
            "doc_id": "cash-rate",
            "title": "Cash rate path and mortgage pressure",
            "body": (
                f"The Reserve Bank cash rate target was {rate} percent on "
                f"{facts['latest_rate']['date']}. It rose {hike_count} times in 2026, from "
                f"{start_rate} percent before the first rise.{blank_sentence} Mortgage repayments "
                "sit outside the grocery price index. Households can face both a higher cash rate "
                "and uneven grocery prices."
            ),
        },
        {
            "doc_id": "eating-out",
            "title": "Meals out versus cooking at home",
            "body": (
                f"Meals out and takeaway added {_points(h['meals_out_contribution_pp'])} points to the "
                f"national yearly rise, more than fruit's {_points(h['fruit_contribution_pp'])} points, "
                "because eating out has a much larger weight. Restaurant meals were "
                f"{prose_change(lines['40025'])}. Takeaway was {prose_change(lines['40026'])}."
            ),
        },
        {
            "doc_id": "relief-aisle",
            "title": "Lines that are cheaper than a year ago",
            "body": (
                f"Eggs were {prose_change(h['eggs_yoy'])}. Pork was {prose_change(h['pork_yoy'])}. "
                f"Coffee and tea were {prose_change(lines['40030'])}. Cakes and biscuits were "
                f"{prose_change(lines['40006'])}. Snacks were {prose_change(lines['115501'])}. "
                f"Poultry was {prose_change(h['poultry_yoy'])}. These are the relief lines in the "
                f"{period} shop."
            ),
        },
    ]
    return docs


def decision_memo(facts: dict) -> str:
    h = facts["headline"]
    period = period_label(h["period"])
    rate = f"{float(facts['latest_rate']['cash_rate_target']):.2f}"
    hike_lines = "\n".join(
        (
            f"- {hike[0]}: {float(hike[1]):.2f}% to {float(hike[2]):.2f}% "
            f"({float(hike[3]):+.2f} from the previous target"
            + (
                "; published change column blank"
                if hike[4] is None
                else f"; published change {float(hike[4]):+.2f}"
            )
            + ")"
        )
        for hike in facts["hikes"]
    )
    return f"""# Where the grocery basket hurts — {period}

These findings are read from the gold tables built on the committed ABS and RBA snapshots. Access date: 6 November 2026.

## The decision in one page

Overall prices were **{prose_change(h['headline_yoy'])}** in {period}. Food and drinks were **{prose_change(h['food_yoy'])}** and added **{_points(h['food_contribution_pp'])} points** to that national rise. The food group is not the main driver.

Housing was {prose_change(h['housing_yoy'])} and added {_points(h['housing_contribution_pp'])} points. Transport was {prose_change(h['transport_yoy'])} and added {_points(h['transport_contribution_pp'])} points. Petrol alone was {prose_change(h['petrol_yoy'])} and added {_points(h['petrol_contribution_pp'])} points. Electricity was {prose_change(h['electricity_yoy'])}.

The cash rate target is **{rate}%**. It was raised {len(facts['hikes'])} times in 2026. Mortgage repayments are not inside the grocery price index, so households can be squeezed by the rate and by a few shelf prices at the same time.

## What households should do

- Treat fruit ({prose_change(h['fruit_yoy'])}, after {bare_percent(facts['fruit_aug'])} in August) as a spike, not the new normal for the whole shop. Vegetables were {prose_change(facts['lines']['114122'])}.
- Beef is still {prose_change(h['beef_yoy'])}, down from {bare_percent(facts['beef_jul'])} in July. Pork was {prose_change(h['pork_yoy'])}, poultry {prose_change(h['poultry_yoy'])}, fish {prose_change(facts['lines']['40015'])}. Eggs were {prose_change(h['eggs_yoy'])}.
- Breakfast cereals ({prose_change(h['cereals_yoy'])}) and milk ({prose_change(h['milk_yoy'])}) are the other hot supermarket lines. Cheese was {prose_change(facts['lines']['40002'])} and bread {prose_change(facts['lines']['40005'])}.
- Eating out adds more to the national rise ({_points(h['meals_out_contribution_pp'])} points) than fruit ({_points(h['fruit_contribution_pp'])} points) because it has a much larger weight.

Price gaps are not diet advice. They only say which published lines moved less.

## What policymakers should watch next

1. Petrol and transport. The September yearly rise in petrol is large enough to move the national figure on its own.
2. Housing, including electricity ({prose_change(h['electricity_yoy'])}) and rents ({prose_change(h['rents_yoy'])}).
3. Whether the fruit spike fades next month. It jumped from {bare_percent(facts['fruit_aug'])} in August to {bare_percent(h['fruit_yoy'])} in September.
4. Whether beef keeps cooling. The shelf price is still high, but the yearly pace has already fallen since July.
5. The cash rate at {rate}% after this year's rises. It will not show up inside the food index, and it still changes household budgets.

## 2026 cash-rate rises

{hike_lines}

The September step is included because the target and the overnight rate both moved. The source file left the change column blank that day.

## What not to conclude

- Do not treat the food group ({prose_change(h['food_yoy'])}) as the hottest part of the national basket. It is rising more slowly than overall prices.
- Do not read housing prices in this index as mortgage interest. The cash rate is a separate series from the Reserve Bank.
- A big shelf jump on a small line (fruit, breakfast cereals) hurts that shopper and barely moves the national index. A moderate rise on petrol or housing does the opposite.
"""


def write_insights() -> list[str]:
    facts = _load()
    folder = insights_dir()
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for document in build_documents(facts):
        path = folder / f"{document['doc_id']}.md"
        path.write_text(f"# {document['title']}\n\n{document['body']}\n")
        written.append(document["doc_id"])
    memo = project_root() / "INSIGHTS.md"
    memo.write_text(decision_memo(facts))
    return written
