"""Opt-in calendar quota conversion and public-holiday adjustment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
import math

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass(frozen=True)
class ReportingOptions:
    quota_hours: float = 37.5
    quota_unit: str = "weeks"
    quota_length: int = 1
    quota_anchor: date = date(2000, 1, 3)
    workdays: tuple[int, ...] = (0, 1, 2, 3, 4)
    quota_rollups: bool = False
    holiday_adjustment: bool = False
    country: str = ""
    subdivision: str = ""
    custom_holidays: tuple[date, ...] = ()
    quota_basis: str = "working"

    @classmethod
    def from_mapping(cls, options: dict) -> ReportingOptions:
        hours = float(options.get("quota_hours", 37.5))
        unit = options.get("quota_unit", "weeks")
        length = options.get("quota_length", 1)
        days = tuple(sorted({DAYS.index(d) for d in options.get("workdays", DAYS[:5])}))
        basis = options.get("quota_basis", "working")
        if (
            not days
            or not math.isfinite(hours)
            or hours < 0
            or hours > 10000
            or unit not in ("days", "weeks", "months")
            or isinstance(length, bool)
            or not isinstance(length, (int, float))
            or int(length) != length
            or not 1 <= length <= {"days": 366, "weeks": 52, "months": 12}.get(unit, 0)
            or basis not in ("working", "signed_in")
        ):
            raise ValueError("Invalid reporting quota configuration.")
        anchor = date.fromisoformat(
            options.get("quota_anchor")
            or ("2000-01-01" if unit == "months" else "2000-01-03")
        )
        if unit == "weeks" and anchor.weekday() != 0:
            raise ValueError("Weekly quota anchor must be a Monday.")
        if unit == "months" and anchor.day != 1:
            raise ValueError("Monthly quota anchor must be the first of a month.")
        raw_custom = options.get("custom_holidays", "")
        custom = (
            tuple(
                sorted(
                    {
                        date.fromisoformat(d.strip())
                        for d in raw_custom.replace(",", "\n").splitlines()
                        if d.strip()
                    }
                )
            )
            if isinstance(raw_custom, str)
            else tuple(date.fromisoformat(d) for d in raw_custom)
        )
        country = options.get("holiday_country", "") or ""
        subdivision = options.get("holiday_subdivision", "") or ""
        if country:
            import holidays

            supported = holidays.list_supported_countries(include_aliases=False)
            if country not in supported or (
                subdivision and subdivision not in supported[country]
            ):
                raise ValueError("Invalid public holiday region.")
        elif subdivision:
            raise ValueError("A subdivision requires a country.")
        for key in ("quota_rollups", "holiday_adjustment"):
            if key in options and not isinstance(options[key], bool):
                raise ValueError("Reporting switches must be booleans.")
        return cls(
            hours,
            unit,
            int(length),
            anchor,
            days,
            options.get("quota_rollups", False),
            options.get("holiday_adjustment", False),
            country,
            subdivision,
            custom,
            basis,
        )


def add_months(day: date, amount: int) -> date:
    absolute = day.year * 12 + day.month - 1 + amount
    return date(absolute // 12, absolute % 12 + 1, 1)


def quota_window(day: date, options: ReportingOptions) -> tuple[date, date]:
    """Anchor fixed-day, multi-week and calendar-month periods deterministically."""
    if options.quota_unit == "months":
        distance = (
            (day.year - options.quota_anchor.year) * 12
            + day.month
            - options.quota_anchor.month
        )
        block = distance // options.quota_length
        start = add_months(options.quota_anchor, block * options.quota_length)
        return start, add_months(start, options.quota_length)
    span = options.quota_length * (7 if options.quota_unit == "weeks" else 1)
    start = options.quota_anchor + timedelta(
        days=((day - options.quota_anchor).days // span) * span
    )
    return start, start + timedelta(days=span)


@lru_cache(maxsize=64)
def public_holidays(country: str, subdivision: str, year: int) -> frozenset[date]:
    if not country:
        return frozenset()
    import holidays

    return frozenset(
        holidays.country_holidays(
            country, subdiv=subdivision or None, years=year, observed=True
        )
    )


def quota_for_period(start: date, end: date, today: date, options: ReportingOptions):
    """Allocate nominal quota across ordinary workdays; holidays reduce requirements.

    Rollups are optional. A converted period is a sum of its daily allocations in
    each relevant base period, so monthly contracts handle different month lengths.
    """
    if not options.quota_rollups and (start, end) != quota_window(today, options):
        return None, None
    nominal = adjusted = 0.0
    denominators = {}
    day = start
    while day < end:
        if day.weekday() in options.workdays:
            bounds = quota_window(day, options)
            if bounds not in denominators:
                denominators[bounds] = sum(
                    (bounds[0] + timedelta(days=i)).weekday() in options.workdays
                    for i in range((bounds[1] - bounds[0]).days)
                )
            count = denominators[bounds]
            allocation = options.quota_hours / count if count else 0.0
            nominal += allocation
            excluded = options.holiday_adjustment and (
                day in options.custom_holidays
                or day
                in public_holidays(options.country, options.subdivision, day.year)
            )
            if not excluded:
                adjusted += allocation
        day += timedelta(days=1)
    return adjusted, nominal
