"""Pure logic helpers for the Sign In App integration."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .const import (
    CONF_CONFIGURED_LOCATIONS,
    CONF_COORDINATE_BEHAVIOR,
    CONF_DISTANCE,
    CONF_ENABLED,
    CONF_LABEL,
    CONF_OFFICE_DISTANCE,
    CONF_OFFICE_SITE_ID,
    CONF_REMOTE_SITE_ID,
    CONF_SITE_ID,
    CONF_SITE_TYPE,
    COORDINATE_BEHAVIOR_DEVICE_TRACKER,
    COORDINATE_BEHAVIOR_REMOTE_ZERO,
    DEFAULT_OFFICE_DISTANCE,
)


SITE_TYPE_OFFICE = "office"
SITE_TYPE_REMOTE = "remote"


def infer_coordinate_behavior(site_type: str | None) -> str:
    """Infer the coordinate behavior for legacy or backend-derived site data."""
    if site_type == SITE_TYPE_REMOTE:
        return COORDINATE_BEHAVIOR_REMOTE_ZERO
    return COORDINATE_BEHAVIOR_DEVICE_TRACKER


def normalize_config_data(config_data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Normalize config data onto the configured_locations schema."""
    normalized_data = dict(config_data)
    normalized_locations = [
        {
            CONF_SITE_ID: location[CONF_SITE_ID],
            CONF_LABEL: location[CONF_LABEL],
            CONF_ENABLED: location[CONF_ENABLED],
            CONF_SITE_TYPE: location[CONF_SITE_TYPE],
            CONF_COORDINATE_BEHAVIOR: location[CONF_COORDINATE_BEHAVIOR],
            CONF_DISTANCE: location[CONF_DISTANCE],
        }
        for location in iter_configured_locations(config_data)
    ]

    changed = False
    if normalized_locations:
        if normalized_data.get(CONF_CONFIGURED_LOCATIONS) != normalized_locations:
            normalized_data[CONF_CONFIGURED_LOCATIONS] = normalized_locations
            changed = True

    for legacy_key in (CONF_OFFICE_SITE_ID, CONF_REMOTE_SITE_ID, CONF_OFFICE_DISTANCE):
        if legacy_key in normalized_data:
            normalized_data.pop(legacy_key, None)
            changed = True

    return normalized_data, changed


def normalize_companion_code(code: str) -> str:
    """Normalize companion codes to the API's expected format."""
    return "".join(char for char in code.upper().strip() if char.isalnum())


def coerce_int(value: Any) -> int | None:
    """Best-effort integer coercion for API/config values."""
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_site_type(
    site_id: Any,
    office_site_id: Any,
    remote_site_id: Any,
) -> str | None:
    """Map a site identifier to an integration site type."""
    site_id = coerce_int(site_id)
    office_site_id = coerce_int(office_site_id)
    remote_site_id = coerce_int(remote_site_id)

    if site_id is None:
        return None
    if site_id == office_site_id:
        return SITE_TYPE_OFFICE
    if site_id == remote_site_id:
        return SITE_TYPE_REMOTE
    return None


def iter_configured_locations(config_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return configured work locations in the new or legacy config format."""
    configured_locations = config_data.get(CONF_CONFIGURED_LOCATIONS)
    if isinstance(configured_locations, list):
        normalized_locations = []
        for index, location in enumerate(configured_locations):
            if not isinstance(location, dict):
                continue

            site_id = coerce_int(location.get(CONF_SITE_ID))
            if site_id is None:
                continue

            site_type = location.get(CONF_SITE_TYPE)
            if site_type not in (SITE_TYPE_OFFICE, SITE_TYPE_REMOTE):
                continue

            normalized_locations.append(
                {
                    CONF_SITE_ID: site_id,
                    CONF_SITE_TYPE: site_type,
                    CONF_COORDINATE_BEHAVIOR: location.get(
                        CONF_COORDINATE_BEHAVIOR,
                        infer_coordinate_behavior(site_type),
                    ),
                    CONF_LABEL: location.get(CONF_LABEL) or f"Site {site_id}",
                    CONF_ENABLED: bool(location.get(CONF_ENABLED, True)),
                    CONF_DISTANCE: location.get(
                        CONF_DISTANCE,
                        (
                            DEFAULT_OFFICE_DISTANCE
                            if infer_coordinate_behavior(site_type) == COORDINATE_BEHAVIOR_DEVICE_TRACKER
                            else 0.0
                        ),
                    ),
                    "_order": index,
                }
            )

        return normalized_locations

    legacy_locations: list[dict[str, Any]] = []
    office_site_id = coerce_int(config_data.get(CONF_OFFICE_SITE_ID))
    if office_site_id is not None:
        legacy_locations.append(
            {
                CONF_SITE_ID: office_site_id,
                CONF_SITE_TYPE: SITE_TYPE_OFFICE,
                CONF_COORDINATE_BEHAVIOR: COORDINATE_BEHAVIOR_DEVICE_TRACKER,
                CONF_LABEL: "Office",
                CONF_ENABLED: True,
                CONF_DISTANCE: config_data.get(CONF_OFFICE_DISTANCE, DEFAULT_OFFICE_DISTANCE),
                "_order": 0,
            }
        )

    remote_site_id = coerce_int(config_data.get(CONF_REMOTE_SITE_ID))
    if remote_site_id is not None:
        legacy_locations.append(
            {
                CONF_SITE_ID: remote_site_id,
                CONF_SITE_TYPE: SITE_TYPE_REMOTE,
                CONF_COORDINATE_BEHAVIOR: COORDINATE_BEHAVIOR_REMOTE_ZERO,
                CONF_LABEL: "Remote",
                CONF_ENABLED: True,
                CONF_DISTANCE: 0.0,
                "_order": 1,
            }
        )

    return legacy_locations


def get_configured_location(
    config_data: dict[str, Any],
    *,
    site_id: Any | None = None,
    site_type: str | None = None,
    coordinate_behavior: str | None = None,
    include_disabled: bool = False,
) -> dict[str, Any] | None:
    """Return a configured work location by site id or compatibility site type."""
    normalized_site_id = coerce_int(site_id)
    configured_locations = iter_configured_locations(config_data)

    if normalized_site_id is not None:
        for location in configured_locations:
            if not include_disabled and not location.get(CONF_ENABLED, True):
                continue
            if location.get(CONF_SITE_ID) == normalized_site_id:
                return location
        return None

    if site_type in (SITE_TYPE_OFFICE, SITE_TYPE_REMOTE):
        for location in configured_locations:
            if not include_disabled and not location.get(CONF_ENABLED, True):
                continue
            if location.get(CONF_SITE_TYPE) == site_type:
                return location
        return None

    if coordinate_behavior is not None:
        for location in configured_locations:
            if not include_disabled and not location.get(CONF_ENABLED, True):
                continue
            if location.get(CONF_COORDINATE_BEHAVIOR) == coordinate_behavior:
                return location
        return None

    return None


def get_configured_locations_by_site_type(
    config_data: dict[str, Any],
    site_type: str,
    *,
    include_disabled: bool = False,
) -> list[dict[str, Any]]:
    """Return all configured locations matching a compatibility site type."""
    configured_locations = iter_configured_locations(config_data)
    return [
        location
        for location in configured_locations
        if (include_disabled or location.get(CONF_ENABLED, True))
        and location.get(CONF_SITE_TYPE) == site_type
    ]


def resolve_site_type_from_config(site_id: Any, config_data: dict[str, Any]) -> str | None:
    """Resolve a site id to a configured site type using new or legacy config."""
    location = get_configured_location(config_data, site_id=site_id)
    if location is None:
        return None
    return location.get(CONF_SITE_TYPE)


def resolve_current_site_id(status_data: dict[str, Any] | None) -> int | None:
    """Extract the current site id from API status data."""
    if not status_data:
        return None

    returning_visitor = status_data.get("returningVisitor") or {}
    current_site = status_data.get("currentSite") or {}
    current_visit = status_data.get("currentVisit") or {}

    for candidate in (
        current_visit.get("siteId"),
        current_visit.get("id"),
        status_data.get("currentSiteId"),
        status_data.get("siteId"),
        current_site.get("id"),
        current_site.get("siteId"),
        returning_visitor.get("currentSiteId"),
        returning_visitor.get("siteId"),
    ):
        site_id = coerce_int(candidate)
        if site_id is not None:
            return site_id

    return None


def build_session_context(site_id: Any, site_type: str, location: dict[str, float]) -> dict[str, Any]:
    """Build a cached session payload for later sign-out calls."""
    return {
        "site_id": coerce_int(site_id),
        "site_type": site_type,
        "coordinate_behavior": infer_coordinate_behavior(site_type),
        "location": deepcopy(location),
    }


def resolve_sign_out_context(
    config_data: dict[str, Any],
    explicit_site_type: str | None,
    status_data: dict[str, Any] | None,
    current_session: dict[str, Any] | None,
    explicit_site_id: Any | None = None,
) -> dict[str, Any] | None:
    """Resolve which site/location context should be used for sign out."""
    current_session = current_session or {}

    current_session_site_id = coerce_int(current_session.get("site_id"))
    current_session_site_type = current_session.get("site_type")
    current_session_coordinate_behavior = current_session.get("coordinate_behavior")
    current_session_location = current_session.get("location")

    configured_location = get_configured_location(config_data, site_id=explicit_site_id)
    if configured_location is not None:
        configured_site_id = configured_location[CONF_SITE_ID]
        configured_site_type = configured_location[CONF_SITE_TYPE]
        return {
            "site_id": (
                current_session_site_id
                if current_session_site_id == configured_site_id and current_session_location is not None
                else configured_site_id
            ),
            "site_type": configured_site_type,
            "coordinate_behavior": configured_location[CONF_COORDINATE_BEHAVIOR],
            "use_cached_location": (
                current_session_site_id == configured_site_id and current_session_location is not None
            ),
        }

    if explicit_site_type == SITE_TYPE_OFFICE:
        if current_session_site_type == SITE_TYPE_OFFICE and current_session_site_id is not None:
            configured_location = get_configured_location(config_data, site_id=current_session_site_id)
            if configured_location is not None:
                return {
                    "site_id": current_session_site_id,
                    "site_type": SITE_TYPE_OFFICE,
                    "coordinate_behavior": configured_location[CONF_COORDINATE_BEHAVIOR],
                    "use_cached_location": current_session_location is not None,
                }

        matching_locations = get_configured_locations_by_site_type(config_data, SITE_TYPE_OFFICE)
        if len(matching_locations) != 1:
            return None
        configured_location = matching_locations[0]
        return {
            "site_id": configured_location.get(CONF_SITE_ID),
            "site_type": SITE_TYPE_OFFICE,
            "coordinate_behavior": configured_location[CONF_COORDINATE_BEHAVIOR],
            "use_cached_location": False,
        }

    if explicit_site_type == SITE_TYPE_REMOTE:
        if current_session_site_type == SITE_TYPE_REMOTE and current_session_site_id is not None:
            configured_location = get_configured_location(config_data, site_id=current_session_site_id)
            if configured_location is not None:
                return {
                    "site_id": current_session_site_id,
                    "site_type": SITE_TYPE_REMOTE,
                    "coordinate_behavior": configured_location[CONF_COORDINATE_BEHAVIOR],
                    "use_cached_location": current_session_location is not None,
                }

        matching_locations = get_configured_locations_by_site_type(config_data, SITE_TYPE_REMOTE)
        if len(matching_locations) != 1:
            return None
        configured_location = matching_locations[0]
        return {
            "site_id": configured_location.get(CONF_SITE_ID),
            "site_type": SITE_TYPE_REMOTE,
            "coordinate_behavior": configured_location[CONF_COORDINATE_BEHAVIOR],
            "use_cached_location": False,
        }

    api_site_id = resolve_current_site_id(status_data)
    api_site_type = resolve_site_type_from_config(api_site_id, config_data)
    if api_site_id is not None:
        return {
            "site_id": api_site_id,
            "site_type": api_site_type,
            "coordinate_behavior": (
                get_configured_location(config_data, site_id=api_site_id) or {}
            ).get(CONF_COORDINATE_BEHAVIOR),
            "use_cached_location": (
                current_session_site_id == api_site_id and current_session_location is not None
            ),
        }

    if current_session_site_id is not None and current_session_site_type in (SITE_TYPE_OFFICE, SITE_TYPE_REMOTE):
        return {
            "site_id": current_session_site_id,
            "site_type": current_session_site_type,
            "coordinate_behavior": current_session_coordinate_behavior,
            "use_cached_location": current_session_location is not None,
        }

    return None


def resolve_sensor_state(
    status_data: dict[str, Any] | None,
    config_data: dict[str, Any],
    current_session: dict[str, Any] | None,
    last_session: dict[str, Any] | None,
) -> str:
    """Resolve the canonical sensor state from API data and cached session state."""
    if not status_data:
        return "unknown"

    returning_visitor = status_data.get("returningVisitor") or {}
    status = returning_visitor.get("status")
    if not status:
        return "unknown"

    status = status.lower()
    status_reason = resolve_sensor_status_reason(
        status_data,
        config_data,
        current_session,
        last_session,
    )

    if status == "signed_in":
        if status_reason is not None:
            return "unknown"
        return "signed_in"

    if status == "signed_out":
        return "signed_out"

    return status


def resolve_sensor_status_reason(
    status_data: dict[str, Any] | None,
    config_data: dict[str, Any],
    current_session: dict[str, Any] | None,
    last_session: dict[str, Any] | None,
) -> str | None:
    """Resolve the operational reason associated with the sensor state."""
    del last_session

    if not status_data:
        return "backend_unavailable"

    returning_visitor = status_data.get("returningVisitor") or {}
    status = returning_visitor.get("status")
    if not status:
        return "backend_contract_mismatch"

    status = status.lower()
    api_site_id = resolve_current_site_id(status_data)
    site_type = resolve_site_type_from_config(api_site_id, config_data)

    if status == "signed_in":
        if api_site_id is not None and site_type is None:
            return "target_not_configured"
        if api_site_id is None:
            current_session = current_session or {}
            if coerce_int(current_session.get("site_id")) is None:
                return "routing_ambiguous"
        return None

    if status == "signed_out":
        return None

    if status == "unknown":
        return "backend_contract_mismatch"

    return None


def _lookup_site_label(status_data: dict[str, Any] | None, site_id: int | None) -> str | None:
    """Resolve a site label from the backend payload when available."""
    if site_id is None or not status_data:
        return None

    for site in status_data.get("sites", []):
        if coerce_int(site.get("id")) == site_id:
            name = site.get("name")
            return str(name) if name is not None else None

    return None


def resolve_sensor_attributes(
    status_data: dict[str, Any] | None,
    config_data: dict[str, Any],
    current_session: dict[str, Any] | None,
    last_session: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve the canonical sensor attribute contract."""
    status_class = resolve_sensor_state(status_data, config_data, current_session, last_session)
    status_reason = resolve_sensor_status_reason(
        status_data,
        config_data,
        current_session,
        last_session,
    )

    if status_class == "unknown":
        return {
            "status_class": "unknown",
            "active_work_location_id": None,
            "active_work_location_label": None,
            "last_active_work_location_id": None,
            "last_active_work_location_label": None,
            "status_reason": status_reason,
        }

    active_site_id = None
    if status_class == "signed_in":
        active_site_id = resolve_sensor_site_id(status_data, current_session, last_session)

    last_active_site_id = active_site_id
    if status_class == "signed_out":
        last_active_site_id = resolve_sensor_site_id(status_data, current_session, last_session)

    active_site_label = _lookup_site_label(status_data, active_site_id)
    last_active_site_label = _lookup_site_label(status_data, last_active_site_id)

    return {
        "status_class": status_class,
        "active_work_location_id": active_site_id,
        "active_work_location_label": active_site_label,
        "last_active_work_location_id": last_active_site_id,
        "last_active_work_location_label": last_active_site_label,
        "status_reason": status_reason,
    }


def resolve_sensor_site_id(
    status_data: dict[str, Any] | None,
    current_session: dict[str, Any] | None,
    last_session: dict[str, Any] | None,
) -> int | None:
    """Expose the best-known site id for sensor attributes."""
    api_site_id = resolve_current_site_id(status_data)
    if api_site_id is not None:
        return api_site_id

    returning_visitor = (status_data or {}).get("returningVisitor") or {}
    status = (returning_visitor.get("status") or "").lower()
    if status == "signed_in" and current_session:
        return coerce_int(current_session.get("site_id"))
    if status == "signed_out" and last_session:
        return coerce_int(last_session.get("site_id"))
    return None
