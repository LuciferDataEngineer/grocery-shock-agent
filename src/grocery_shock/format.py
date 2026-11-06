"""Plain-language formatting. Numbers stay tied to the values passed in."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from grocery_shock.paths import MELBOURNE

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def period_label(period: str) -> str:
    year, month = period.split("-")
    return f"{MONTHS[int(month) - 1]} {year}"


def prose_change(value: float, digits: int = 1) -> str:
    """Describe a percent change without adding a number that was not supplied."""
    number = float(value)
    shown = f"{abs(number):.{digits}f}"
    if abs(number) < 0.05:
        return "flat on a year ago"
    if number > 0:
        return f"up {shown}%"
    return f"down {shown}%"


def bare_percent(value: float, digits: int = 1) -> str:
    return f"{float(value):.{digits}f}%"


def weight_period_label(period: str) -> str:
    if period.endswith("-Q4"):
        return f"late {period[:4]}"
    return period


def signed_number(value: float, digits: int = 1) -> str:
    number = float(value)
    if number > 0:
        return f"+{number:.{digits}f}"
    return f"{number:.{digits}f}"


def melbourne_now() -> datetime:
    return datetime.now(ZoneInfo(MELBOURNE))


def melbourne_stamp(moment: datetime | None = None) -> str:
    current = moment or melbourne_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=ZoneInfo(MELBOURNE))
    else:
        current = current.astimezone(ZoneInfo(MELBOURNE))
    hour = current.strftime("%I").lstrip("0") or "12"
    return (
        f"{current.day} {current.strftime('%B %Y')}, "
        f"{hour}:{current.strftime('%M %p')} Melbourne"
    )
