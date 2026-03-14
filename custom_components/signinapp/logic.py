"""Pure logic helpers for the Sign In App integration."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


SITE_TYPE_OFFICE = "office"
SITE_TYPE_REMOTE = "remote"


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


def resolve_current_site_id(status_data: dict[str, Any] | None) -> int | None:
    """Extract the current site id from API status data."""
    if not status_data:
        return None

    returning_visitor = status_data.get("returningVisitor") or {}
    current_site = status_data.get("currentSite") or {}

    for candidate in (
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
        "location": deepcopy(location),
    }


def resolve_sign_out_context(
    config_data: dict[str, Any],
    explicit_site_type: str | None,
    status_data: dict[str, Any] | None,
    current_session: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Resolve which site/location context should be used for sign out."""
    office_site_id = config_data.get("office_site_id")
    remote_site_id = config_data.get("remote_site_id")
    current_session = current_session or {}

    current_session_site_id = coerce_int(current_session.get("site_id"))
    current_session_site_type = current_session.get("site_type")
    current_session_location = current_session.get("location")

    if explicit_site_type == SITE_TYPE_OFFICE:
        return {
            "site_id": (
                current_session_site_id
                if current_session_site_type == SITE_TYPE_OFFICE and current_session_site_id is not None
                else coerce_int(office_site_id)
            ),
            "site_type": SITE_TYPE_OFFICE,
            "use_cached_location": (
                current_session_site_type == SITE_TYPE_OFFICE and current_session_location is not None
            ),
        }

    if explicit_site_type == SITE_TYPE_REMOTE:
        return {
            "site_id": (
                current_session_site_id
                if current_session_site_type == SITE_TYPE_REMOTE and current_session_site_id is not None
                else coerce_int(remote_site_id)
            ),
            "site_type": SITE_TYPE_REMOTE,
            "use_cached_location": (
                current_session_site_type == SITE_TYPE_REMOTE and current_session_location is not None
            ),
        }

    api_site_id = resolve_current_site_id(status_data)
    api_site_type = resolve_site_type(api_site_id, office_site_id, remote_site_id)
    if api_site_id is not None:
        return {
            "site_id": api_site_id,
            "site_type": api_site_type,
            "use_cached_location": (
                current_session_site_id == api_site_id and current_session_location is not None
            ),
        }

    if current_session_site_id is not None and current_session_site_type in (SITE_TYPE_OFFICE, SITE_TYPE_REMOTE):
        return {
            "site_id": current_session_site_id,
            "site_type": current_session_site_type,
            "use_cached_location": current_session_location is not None,
        }

    return None


def resolve_sensor_state(
    status_data: dict[str, Any] | None,
    config_data: dict[str, Any],
    current_session: dict[str, Any] | None,
    last_session: dict[str, Any] | None,
) -> str:
    """Resolve the sensor translation key from API data and cached session state."""
    if not status_data:
        return "unknown"

    returning_visitor = status_data.get("returningVisitor") or {}
    status = returning_visitor.get("status")
    if not status:
        return "unknown"

    status = status.lower()
    site_type = resolve_site_type(
        resolve_current_site_id(status_data),
        config_data.get("office_site_id"),
        config_data.get("remote_site_id"),
    )

    if status == "signed_in":
        if site_type is None and current_session:
            site_type = current_session.get("site_type")
        if site_type == SITE_TYPE_OFFICE:
            return "signed_in_office"
        if site_type == SITE_TYPE_REMOTE:
            return "signed_in_remote"
        return status

    if status == "signed_out":
        if site_type is None and last_session:
            site_type = last_session.get("site_type")
        if site_type == SITE_TYPE_OFFICE:
            return "signed_out_office"
        if site_type == SITE_TYPE_REMOTE:
            return "signed_out_remote"
        return status

    return status


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
