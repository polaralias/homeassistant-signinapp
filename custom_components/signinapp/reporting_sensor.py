"""Stable, independently selectable attendance and quota reporting entities."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .reporting import BASE_METRICS, DAYS

PERIOD_NAMES = {
    "today": "Today",
    "week": "This week",
    "month": "This month",
    "quota_period": "Quota period",
    "yesterday": "Yesterday",
    "week_to_yesterday": "Week through yesterday",
    **{d: d.title() for d in DAYS},
}
METRIC_NAMES = {
    "signed_in": "signed in",
    "working": "working time",
    "non_working": "non-working time",
    "unclassified": "unclassified working time",
    "unclassified_activity": "unclassified activity time",
    "session_count": "sessions",
    "quota": "quota",
    "quota_used": "quota used",
    "quota_remaining": "quota remaining",
    "quota_overtime": "overtime",
    "quota_balance": "quota balance",
    "quota_percentage": "quota completed",
    "quota_remaining_percentage": "quota remaining percentage",
    "quota_overtime_percentage": "overtime percentage",
    "quota_nominal": "nominal quota",
    "quota_holiday_reduction": "holiday quota reduction",
}
ACTIVITY_METRICS = {
    "activity": "",
    "activity_percentage": " share of signed-in time",
    "activity_working_percentage": " share of working time",
    "activity_quota_percentage": " quota contribution",
}


class ReportingSensor(CoordinatorEntity, SensorEntity):
    """Hours remain exact; presentation may round without altering quota triggers."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, period, metric, activity=None):
        super().__init__(coordinator)
        self.entry, self.period, self.metric, self.activity = (
            entry,
            period,
            metric,
            activity,
        )
        identity = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{identity}_report_{period}_{metric}" + (
            f"_{activity}" if activity is not None else ""
        )
        self._attr_icon = (
            "mdi:calendar-clock" if period in DAYS else "mdi:briefcase-clock"
        )
        self._attr_suggested_display_precision = 2
        if metric == "session_count":
            self._attr_native_unit_of_measurement = None
            self._attr_suggested_display_precision = 0
        elif metric.endswith("percentage"):
            self._attr_native_unit_of_measurement = PERCENTAGE
        else:
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.HOURS
        # All combinations exist in the registry. Enable current-period reports and
        # daily signed-in totals; secondary daily activity/quota combinations opt in.
        self._attr_entity_registry_enabled_default = (
            period in ("today", "week", "month", "quota_period")
            or metric == "signed_in"
        )
        if activity is not None and metric != "activity":
            self._attr_entity_registry_enabled_default = False

    @property
    def name(self):
        if self.activity is not None:
            activity = (
                (self.coordinator.data or {})
                .get("activities", {})
                .get(self.activity, {})
            )
            label = (
                activity.get("name") or "Activity " + self.activity
            ) + ACTIVITY_METRICS[self.metric]
        else:
            label = METRIC_NAMES[self.metric]
        return PERIOD_NAMES[self.period] + " " + label

    @property
    def native_value(self):
        period = (self.coordinator.data or {}).get("periods", {}).get(self.period, {})
        if self.activity is not None:
            hours = period.get("activities", {}).get(self.activity)
            if self.metric == "activity" or hours is None:
                return hours
            values = period.get("values", {})
            working = (
                (self.coordinator.data or {})
                .get("activities", {})
                .get(self.activity, {})
                .get("is_working")
            )
            if self.metric == "activity_percentage":
                denominator = values.get("signed_in")
            elif self.metric == "activity_working_percentage":
                if working is not True:
                    return None
                denominator = values.get("working")
            else:
                if self.coordinator.options.quota_basis == "working":
                    if working is None:
                        return None
                    if not working:
                        return 0.0 if values.get("quota") is not None else None
                denominator = values.get("quota")
                if not denominator:
                    return None
            return (
                hours / denominator * 100
                if denominator
                else (0.0 if denominator == 0 else None)
            )
        return period.get("values", {}).get(self.metric)

    @property
    def available(self):
        return super().available and self.native_value is not None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        period = data.get("periods", {}).get(self.period, {})
        return {
            "report_period": self.period,
            "report_metric": self.metric,
            "activity_id": self.activity,
            "period_start": period.get("start"),
            "period_end": period.get("end"),
            "classification_complete": period.get("classification_complete"),
            "activity_classification_complete": period.get(
                "activity_classification_complete"
            ),
            "history_fetched_at": data.get("history_fetched_at"),
            "reporting_error": self.coordinator.error_reason,
            "quota_basis": self.coordinator.options.quota_basis,
        }

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.unique_id or self.entry.entry_id)}
        )


async def async_setup_reporting_sensors(hass, entry, coordinator, async_add_entities):
    """Add metric grid once and discover activity IDs without renaming existing IDs."""
    entities = [
        ReportingSensor(coordinator, entry, period, metric)
        for period in PERIOD_NAMES
        for metric in BASE_METRICS
    ]
    seen = set()

    @callback
    def discover():
        activities = (coordinator.data or {}).get("activities", {})
        added = []
        for activity in activities:
            if activity in seen:
                continue
            seen.add(activity)
            added.extend(
                ReportingSensor(coordinator, entry, period, metric, activity)
                for period in PERIOD_NAMES
                for metric in ACTIVITY_METRICS
            )
        if added:
            async_add_entities(added)

    async_add_entities(entities)
    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))
