"""Exact, timezone-aware attendance reporting independent of Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import math
from typing import Any
from zoneinfo import ZoneInfo
from .quotas import ReportingOptions, quota_for_period, quota_window

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
BASE_METRICS = (
    "signed_in",
    "working",
    "non_working",
    "unclassified",
    "unclassified_activity",
    "session_count",
    "quota",
    "quota_used",
    "quota_remaining",
    "quota_overtime",
    "quota_balance",
    "quota_percentage",
    "quota_remaining_percentage",
    "quota_overtime_percentage",
    "quota_nominal",
    "quota_holiday_reduction",
)


class ReportingDataError(ValueError):
    """The backend snapshot cannot support trustworthy time totals."""


@dataclass(frozen=True)
class Period:
    key: str
    start: datetime
    end: datetime
    quota: float | None
    nominal_quota: float | None


def periods(now: datetime, timezone: str, options: ReportingOptions) -> list[Period]:
    """Use local calendar boundaries; elapsed seconds use UTC timestamps across DST."""
    tz = ZoneInfo(timezone)
    today = now.astimezone(tz).date()
    monday = today - timedelta(days=today.weekday())
    first = today.replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)

    def midnight(d):
        return datetime.combine(d, time.min, tzinfo=tz)

    yesterday = today - timedelta(days=1)
    completed_week = yesterday - timedelta(days=yesterday.weekday())
    quota_start, quota_end = quota_window(today, options)
    bounds = [
        ("today", today, today + timedelta(days=1)),
        ("week", monday, monday + timedelta(days=7)),
        ("month", first, next_month),
        ("quota_period", quota_start, quota_end),
        ("yesterday", yesterday, today),
        ("week_to_yesterday", completed_week, today),
    ]
    for i, key in enumerate(DAYS):
        day = monday + timedelta(days=i)
        bounds.append((key, day, day + timedelta(days=1)))
    result = []
    for key, start, end in bounds:
        quota, nominal = quota_for_period(start, end, today, options)
        result.append(Period(key, midnight(start), midnight(end), quota, nominal))
    return result


def history_window(
    now: datetime, timezone: str, options: ReportingOptions
) -> tuple[date, date]:
    """One request covers the current calendar month and any earlier week days."""
    today = now.astimezone(ZoneInfo(timezone)).date()
    yesterday = today - timedelta(days=1)
    return min(
        today.replace(day=1),
        yesterday - timedelta(days=yesterday.weekday()),
        quota_window(today, options)[0],
    ), today + timedelta(days=1)


def timestamp(value: Any) -> float | None:
    """Accept observed epoch seconds or ISO datetimes; never accept naive times."""
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) and value > 0 else None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                return parsed.timestamp()
        except ValueError:
            pass
    return None


def _activities(config: dict, rows: list[dict]) -> dict[str, dict]:
    result = {}
    candidates = [
        change.get("status")
        for row in rows
        for change in (row.get("activityStatusChanges") or [])
    ]
    candidates += list(config.get("archivedStatuses") or []) + list(
        config.get("activityStatuses") or []
    )
    for status in candidates:
        if not isinstance(status, dict) or status.get("id") is None:
            continue
        key = str(status["id"])
        result[key] = {
            "name": str(status.get("name") or "Activity " + key),
            "is_working": status.get("isWorking")
            if isinstance(status.get("isWorking"), bool)
            else None,
        }
    return result


def _segments(rows: list[dict], config: dict, now: float):
    """Normalise sessions and status changes; return clipped, classified segments."""
    visitor = config.get("returningVisitor") or {}
    live_in = timestamp(visitor.get("lastIn"))
    live_status = visitor.get("status")
    segments = []
    sessions = []
    seen = {}
    matched_live = False
    for row in rows:
        identity = row.get("id")
        if identity is None or isinstance(identity, bool):
            raise ReportingDataError("History session identity is missing.")
        start = timestamp(row.get("inTimestamp")) or timestamp(row.get("inDateTime"))
        end = timestamp(row.get("outTimestamp")) or timestamp(row.get("outDateTime"))
        if start is None:
            raise ReportingDataError("History session start is invalid.")
        if start > now + 60:
            raise ReportingDataError("History session start is in the future.")
        if end is None:
            if (
                live_status != "signed_in"
                or live_in is None
                or abs(start - live_in) > 2
            ):
                raise ReportingDataError(
                    "An open history session could not be confirmed."
                )
            end = now
            matched_live = True
        elif (
            live_in is not None
            and abs(start - live_in) <= 2
            and live_status == "signed_in"
        ):
            raise ReportingDataError("Current attendance and history disagree.")
        if end < start:
            raise ReportingDataError("History session ends before it starts.")
        changes = row.get("activityStatusChanges") or []
        if not isinstance(changes, list):
            raise ReportingDataError("History activities are invalid.")
        points = []
        for change in changes:
            if not isinstance(change, dict):
                raise ReportingDataError("History activity is invalid.")
            when = timestamp(change.get("changedAt"))
            status = change.get("status")
            if when is None or not isinstance(status, dict):
                raise ReportingDataError("History activity change is invalid.")
            key = str(status["id"]) if status.get("id") is not None else None
            working = status.get("isWorking")
            if not isinstance(working, bool):
                working = None
            points.append((when, key, working))
        points.sort(key=lambda p: p[0])
        signature = (start, end, tuple(points))
        if str(identity) in seen:
            if seen[str(identity)] != signature:
                raise ReportingDataError("Conflicting duplicate history sessions.")
            continue
        seen[str(identity)] = signature
        sessions.append((start, end))
        cursor, activity, working = start, None, None
        for when, key, value in points:
            if when > end:
                continue
            if when > cursor:
                segments.append((cursor, min(when, end, now), activity, working))
                cursor = when
            activity, working = key, value
        if cursor < min(end, now):
            segments.append((cursor, min(end, now), activity, working))
    if live_status == "signed_in" and not matched_live:
        if live_in is None or live_in > now:
            raise ReportingDataError("Current sign-in start is invalid.")
        # The status endpoint proves signed-in time, but does not prove an activity.
        segments.append((live_in, now, None, None))
        sessions.append((live_in, now))
    return segments, sessions


def build_report(
    rows: list[dict],
    config: dict,
    now: datetime,
    timezone: str,
    options: ReportingOptions,
) -> dict:
    """Union intervals so duplicates/overlaps cannot inflate attendance or quotas."""
    if now.tzinfo is None:
        raise ValueError("Reporting clock must be timezone aware.")
    segments, sessions = _segments(rows, config, now.timestamp())
    activities = _activities(config, rows)
    result = {"periods": {}, "activities": activities, "generated_at": now.isoformat()}
    for period in periods(now, timezone, options):
        begin, finish = (
            period.start.timestamp(),
            min(period.end.timestamp(), now.timestamp()),
        )
        relevant = [
            (max(a, begin), min(b, finish), key, working)
            for a, b, key, working in segments
            if a < finish and b > begin
        ]
        edges = sorted({v for a, b, _, _ in relevant for v in (a, b)})
        seconds = dict(
            signed_in=0.0,
            working=0.0,
            non_working=0.0,
            unclassified=0.0,
            unclassified_activity=0.0,
        )
        per_activity = {key: 0.0 for key in activities}
        for a, b in zip(edges, edges[1:]):
            active = {
                (key, working)
                for left, right, key, working in relevant
                if left < b and right > a
            }
            if not active:
                continue
            duration = b - a
            seconds["signed_in"] += duration
            flags = {flag for _, flag in active}
            labels = {key for key, _ in active}
            if flags == {True}:
                seconds["working"] += duration
            elif flags == {False}:
                seconds["non_working"] += duration
            else:
                seconds["unclassified"] += duration
            if len(labels) == 1 and None not in labels:
                per_activity[next(iter(labels))] += duration
            else:
                seconds["unclassified_activity"] += duration
        values = {key: value / 3600 for key, value in seconds.items()}
        complete = seconds["unclassified"] == 0
        activity_complete = seconds["unclassified_activity"] == 0
        if not complete:
            values["working"] = values["non_working"] = None
        values["session_count"] = sum(a < finish and b > begin for a, b in sessions)
        values["quota"] = period.quota
        values["quota_nominal"] = period.nominal_quota
        values["quota_holiday_reduction"] = (
            period.nominal_quota - period.quota if period.quota is not None else None
        )
        used = values[options.quota_basis] if period.quota is not None else None
        values["quota_used"] = used
        values["quota_remaining"] = (
            max(period.quota - used, 0) if used is not None else None
        )
        values["quota_overtime"] = (
            max(used - period.quota, 0) if used is not None else None
        )
        values["quota_balance"] = period.quota - used if used is not None else None
        values["quota_percentage"] = (
            used / period.quota * 100 if used is not None and period.quota else None
        )
        values["quota_remaining_percentage"] = (
            max(100 - values["quota_percentage"], 0)
            if values["quota_percentage"] is not None
            else None
        )
        values["quota_overtime_percentage"] = (
            max(values["quota_percentage"] - 100, 0)
            if values["quota_percentage"] is not None
            else None
        )
        result["periods"][period.key] = {
            "start": period.start.isoformat(),
            "end": period.end.isoformat(),
            "classification_complete": complete,
            "activity_classification_complete": activity_complete,
            "values": values,
            "activities": {
                key: value / 3600 if activity_complete else None
                for key, value in per_activity.items()
            },
        }
    return result
