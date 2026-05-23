"""The Sign In App integration."""
import inspect
from copy import deepcopy
import logging
from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_ACCESS_TOKEN, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client, config_validation as cv, device_registry as dr, issue_registry
from homeassistant.helpers.issue_registry import IssueSeverity
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import (
    COORDINATE_BEHAVIOR_DEVICE_TRACKER,
    COORDINATE_BEHAVIOR_REMOTE_ZERO,
    DOMAIN,
    CONF_COORDINATE_BEHAVIOR,
    CONF_REMOTE_SITE_ID,
    CONF_OFFICE_SITE_ID,
    CONF_DEVICE_TRACKER,
    CONF_OFFICE_DISTANCE,
    CONF_CONFIGURED_LOCATIONS,
    CONF_DISTANCE,
    CONF_SITE_ID,
    CONF_SITE_TYPE,
    SESSION_STATE_HASS_KEY,
    SESSION_STORE_HASS_KEY,
    SESSION_STORE_KEY,
    SESSION_STORE_VERSION,
    RUNTIME_STATUS_REASON_KEY,
    DRIFT_ISSUE_ID_PREFIX,
)
from .api import SignInAppApi
from .logic import (
    SITE_TYPE_OFFICE,
    SITE_TYPE_REMOTE,
    build_session_context,
    coerce_int,
    get_configured_location,
    get_configured_locations_by_site_type,
    infer_coordinate_behavior,
    iter_configured_locations,
    normalize_config_data,
    resolve_sign_out_context,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_SIGN_IN = "sign_in"
SERVICE_SIGN_OUT = "sign_out"

ATTR_SITE_TYPE = "site_type"
ATTR_SITE_ID = "site_id"
ATTR_DEVICE_ID = "device_id"

SERVICE_SCHEMA_SIGN_IN = vol.Schema({
    vol.Optional(ATTR_SITE_TYPE): vol.In([SITE_TYPE_OFFICE, SITE_TYPE_REMOTE]),
    vol.Optional(ATTR_SITE_ID): cv.positive_int,
    vol.Optional(ATTR_DEVICE_ID): cv.string,
})

SERVICE_SCHEMA_SIGN_OUT = vol.Schema({
    vol.Optional(ATTR_SITE_TYPE): vol.In([SITE_TYPE_OFFICE, SITE_TYPE_REMOTE]),
    vol.Optional(ATTR_SITE_ID): cv.positive_int,
    vol.Optional(ATTR_DEVICE_ID): cv.string,
})


def _config_drift_issue_id(entry_id: str) -> str:
    """Build a stable issue id for config drift on a config entry."""
    return f"{DRIFT_ISSUE_ID_PREFIX}_{entry_id}"


def _detect_config_drift(config_data: dict[str, Any], status_data: dict[str, Any] | None) -> list[str]:
    """Detect meaningful drift between configured target ids and backend-discovered sites."""
    if not status_data:
        return []

    sites = {
        coerce_int(site.get("id")): site
        for site in status_data.get("sites", [])
        if coerce_int(site.get("id")) is not None
    }
    if not sites:
        return []

    drift_reasons: list[str] = []
    for configured_location in iter_configured_locations(config_data):
        expected_kind = configured_location[CONF_SITE_TYPE]
        expected_coordinate_behavior = configured_location.get(
            CONF_COORDINATE_BEHAVIOR,
            infer_coordinate_behavior(expected_kind),
        )
        site_id = configured_location[CONF_SITE_ID]
        site = sites.get(site_id)
        if site is None:
            drift_reasons.append(f"{expected_kind} site {site_id} is no longer in the discovered site list")
            continue

        site_type = str(site.get("type", "")).lower()
        backend_coordinate_behavior = infer_coordinate_behavior(site_type)
        if (
            expected_coordinate_behavior == COORDINATE_BEHAVIOR_REMOTE_ZERO
            and backend_coordinate_behavior != COORDINATE_BEHAVIOR_REMOTE_ZERO
        ):
            drift_reasons.append(
                f"configured remote site {site_id} is now reported as type {site.get('type', 'unknown')}"
            )
        if (
            expected_coordinate_behavior == COORDINATE_BEHAVIOR_DEVICE_TRACKER
            and backend_coordinate_behavior == COORDINATE_BEHAVIOR_REMOTE_ZERO
        ):
            drift_reasons.append(
                f"configured office site {site_id} is now reported as type {site.get('type', 'unknown')}"
            )

    return drift_reasons


def async_sync_config_drift_issue(
    hass: HomeAssistant,
    entry: ConfigEntry,
    status_data: dict[str, Any] | None,
) -> None:
    """Create or clear an admin-facing drift issue for a config entry."""
    drift_reasons = _detect_config_drift(entry.data, status_data)
    issue_id = _config_drift_issue_id(entry.entry_id)
    if drift_reasons:
        issue_registry.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=True,
            is_persistent=False,
            severity=IssueSeverity.WARNING,
            translation_key="config_drift_detected",
            translation_placeholders={"details": "; ".join(drift_reasons)},
        )
        return

    issue_registry.async_delete_issue(hass, DOMAIN, issue_id)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Sign In App component."""
    _LOGGER.debug("Setting up Sign In App component")

    if SESSION_STORE_HASS_KEY not in hass.data:
        store = Store(hass, SESSION_STORE_VERSION, SESSION_STORE_KEY)
        hass.data[SESSION_STORE_HASS_KEY] = store
        hass.data[SESSION_STATE_HASS_KEY] = await store.async_load() or {}

    # Register static path for images
    static_url_path = f"/{DOMAIN}_static"
    static_local_path = hass.config.path(f"custom_components/{DOMAIN}/www")
    if hasattr(hass.http, "async_register_static_paths"):
        register_result = hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    static_url_path,
                    static_local_path,
                    cache_headers=True,
                )
            ]
        )
        if inspect.isawaitable(register_result):
            await register_result
    else:
        hass.http.register_static_path(
            static_url_path,
            static_local_path,
            cache_headers=True,
        )

    # Register services globally
    hass.services.async_register(DOMAIN, SERVICE_SIGN_IN, get_handle_sign_in(hass), schema=SERVICE_SCHEMA_SIGN_IN)
    hass.services.async_register(DOMAIN, SERVICE_SIGN_OUT, get_handle_sign_out(hass), schema=SERVICE_SCHEMA_SIGN_OUT)

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sign In App from a config entry."""
    _LOGGER.debug("Setting up Sign In App entry: %s", entry.entry_id)
    normalized_entry_data, config_changed = normalize_config_data(dict(entry.data))
    if config_changed and hass.config_entries.async_get_entry(entry.entry_id) is not None:
        hass.config_entries.async_update_entry(entry, data=normalized_entry_data)

    session = aiohttp_client.async_get_clientsession(hass)
    # Use HA's timezone
    timezone = hass.config.time_zone
    api = SignInAppApi(session, timezone=timezone)
    api.set_token(normalized_entry_data[CONF_ACCESS_TOKEN])

    session_state = hass.data.get(SESSION_STATE_HASS_KEY, {})
    persisted_session = session_state.get(entry.entry_id, {})

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "config": normalized_entry_data,
        "coordinator": None,
        "current_session": persisted_session.get("current_session"),
        "last_session": persisted_session.get("last_session"),
        RUNTIME_STATUS_REASON_KEY: None,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def get_location(
    hass: HomeAssistant,
    config_data: dict[str, Any],
    configured_location: dict[str, Any] | None = None,
    site_type: str | None = None,
):
    """Resolve coordinates from configured location behavior or legacy site type."""
    coordinate_behavior = (
        configured_location.get(CONF_COORDINATE_BEHAVIOR)
        if configured_location is not None
        else infer_coordinate_behavior(site_type)
    )

    if coordinate_behavior == COORDINATE_BEHAVIOR_DEVICE_TRACKER:
        tracker_entity = config_data[CONF_DEVICE_TRACKER]
        distance = (
            configured_location.get(CONF_DISTANCE)
            if configured_location is not None
            else config_data.get(CONF_OFFICE_DISTANCE, 0)
        )

        state = hass.states.get(tracker_entity)
        if not state:
            raise HomeAssistantError(
                f"Configured person entity {tracker_entity} was not found."
            )

        latitude = state.attributes.get("latitude")
        longitude = state.attributes.get("longitude")
        if latitude is None or longitude is None:
            raise HomeAssistantError(
                f"Configured person entity {tracker_entity} has no current coordinates."
            )

        lat = float(latitude)
        lng = float(longitude)
        accuracy = float(distance)
    elif coordinate_behavior == COORDINATE_BEHAVIOR_REMOTE_ZERO:
        lat = 0.0
        lng = 0.0
        accuracy = 0.0
    else:
        raise HomeAssistantError("Configured site has an unsupported coordinate behavior.")
    return lat, lng, accuracy


async def async_refresh_entry_state(entry_data):
    """Refresh the coordinator after a mutating action."""
    coordinator = entry_data.get("coordinator")
    if coordinator is not None:
        await coordinator.async_request_refresh()


def set_runtime_status_reason(entry_data: dict[str, Any], reason: str | None) -> None:
    """Update the transient runtime status reason for an entry."""
    entry_data[RUNTIME_STATUS_REASON_KEY] = reason


async def async_save_session_state(hass: HomeAssistant, entry_id: str, entry_data: dict[str, Any]) -> None:
    """Persist the current and last session context for a config entry."""
    session_state = hass.data.setdefault(SESSION_STATE_HASS_KEY, {})
    current_session = entry_data.get("current_session")
    last_session = entry_data.get("last_session")

    if current_session is None and last_session is None:
        session_state.pop(entry_id, None)
    else:
        session_state[entry_id] = {
            "current_session": deepcopy(current_session),
            "last_session": deepcopy(last_session),
        }

    store = hass.data.get(SESSION_STORE_HASS_KEY)
    if store is not None:
        await store.async_save(session_state)

def get_config_entry_from_device(hass: HomeAssistant, device_id: str):
    """Resolve device_id to config_entry."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    if not device:
        return None

    # Check config entries associated with this device
    for entry_id in device.config_entries:
        if entry_id in hass.data.get(DOMAIN, {}):
            return entry_id
    return None

def get_target_entry_id(hass: HomeAssistant, call: ServiceCall):
    """Get the target entry_id from the service call."""
    device_id = call.data.get(ATTR_DEVICE_ID)

    if device_id:
        entry_id = get_config_entry_from_device(hass, device_id)
        if entry_id:
             return entry_id
        raise ValueError(f"No valid Sign In App config entry found for device {device_id}")

    # Fallback: check if only one entry exists
    domain_data = hass.data.get(DOMAIN, {})
    if len(domain_data) == 1:
        return next(iter(domain_data))

    if len(domain_data) == 0:
        raise ValueError("No Sign In App config entries found.")

    raise ValueError("Multiple Sign In App config entries found. Please specify a device.")


def get_handle_sign_in(hass: HomeAssistant):
    async def handle_sign_in(call: ServiceCall):
        """Handle the sign in service."""
        _LOGGER.debug("Handling sign in call: %s", call.data)

        try:
            entry_id = get_target_entry_id(hass, call)
        except ValueError as err:
            _LOGGER.error(str(err))
            raise

        entry_data = hass.data[DOMAIN][entry_id]
        api = entry_data["api"]
        config_data = entry_data["config"]

        site_id = coerce_int(call.data.get(ATTR_SITE_ID))
        site_type = call.data.get(ATTR_SITE_TYPE)
        configured_location = None
        if site_id is not None:
            configured_location = get_configured_location(config_data, site_id=site_id)
            if configured_location is None:
                set_runtime_status_reason(entry_data, "target_not_configured")
                await async_refresh_entry_state(entry_data)
                raise HomeAssistantError(
                    f"Configured site {site_id} is not available for this integration entry."
                )
            site_id = configured_location[CONF_SITE_ID]
            site_type = configured_location[CONF_SITE_TYPE]
        elif site_type in (SITE_TYPE_OFFICE, SITE_TYPE_REMOTE):
            matching_locations = get_configured_locations_by_site_type(config_data, site_type)
            if len(matching_locations) == 0:
                set_runtime_status_reason(entry_data, "target_not_configured")
                await async_refresh_entry_state(entry_data)
                raise HomeAssistantError(
                    f"No configured {site_type} target is available for this integration entry."
                )
            if len(matching_locations) > 1:
                set_runtime_status_reason(entry_data, "routing_ambiguous")
                await async_refresh_entry_state(entry_data)
                raise HomeAssistantError(
                    f"Multiple configured {site_type} targets match this compatibility hint. Provide site_id."
                )
            configured_location = matching_locations[0]
            site_id = configured_location[CONF_SITE_ID]
            site_type = configured_location[CONF_SITE_TYPE]
        else:
            raise HomeAssistantError("Provide either site_id or site_type for sign in.")

        try:
            lat, lng, accuracy = await get_location(
                hass,
                config_data,
                configured_location,
                site_type,
            )
        except HomeAssistantError:
            set_runtime_status_reason(entry_data, "missing_location_context")
            await async_refresh_entry_state(entry_data)
            raise
        session_context = build_session_context(
            site_id,
            site_type,
            {"lat": lat, "lng": lng, "accuracy": accuracy},
        )

        _LOGGER.debug(
            "Signing in to site_id=%s with lat=%s, lng=%s, accuracy=%s",
            site_id, lat, lng, accuracy
        )
        try:
            await api.sign_in(site_id, lat, lng, accuracy)
            set_runtime_status_reason(entry_data, None)
            entry_data["current_session"] = deepcopy(session_context)
            entry_data["last_session"] = deepcopy(session_context)
            await async_save_session_state(hass, entry_id, entry_data)
            await async_refresh_entry_state(entry_data)
            _LOGGER.debug("Sign in successful")
        except Exception as e:
            set_runtime_status_reason(entry_data, "target_temporarily_unusable")
            await async_refresh_entry_state(entry_data)
            _LOGGER.error("Sign in failed: %s", e)
            raise
    return handle_sign_in

def get_handle_sign_out(hass: HomeAssistant):
    async def handle_sign_out(call: ServiceCall):
        """Handle the sign out service."""
        _LOGGER.debug("Handling sign out call: %s", call.data)

        try:
            entry_id = get_target_entry_id(hass, call)
        except ValueError as err:
            _LOGGER.error(str(err))
            raise

        entry_data = hass.data[DOMAIN][entry_id]
        api = entry_data["api"]
        config_data = entry_data["config"]

        site_type = call.data.get(ATTR_SITE_TYPE)
        explicit_site_id = coerce_int(call.data.get(ATTR_SITE_ID))
        status_data = None
        if not site_type and explicit_site_id is None:
            try:
                _LOGGER.debug("Fetching status data for sign out resolution")
                status_data = await api.get_config()
            except Exception as err:
                _LOGGER.warning("Could not fetch status before sign out: %s", err)

        sign_out_context = resolve_sign_out_context(
            config_data,
            site_type,
            status_data,
            entry_data.get("current_session"),
            explicit_site_id,
        )
        if not sign_out_context or sign_out_context.get("site_id") is None:
            if site_type in (SITE_TYPE_OFFICE, SITE_TYPE_REMOTE):
                matching_locations = get_configured_locations_by_site_type(config_data, site_type)
                reason = "routing_ambiguous" if len(matching_locations) > 1 else "target_not_configured"
            elif explicit_site_id is None:
                reason = "routing_ambiguous"
            else:
                reason = "target_not_configured"
            set_runtime_status_reason(entry_data, reason)
            await async_refresh_entry_state(entry_data)
            raise HomeAssistantError(
                "Could not determine which site to sign out from."
            )

        site_id = sign_out_context["site_id"]
        site_type = sign_out_context.get("site_type")
        configured_location = get_configured_location(config_data, site_id=site_id)
        if sign_out_context.get("use_cached_location"):
            location = entry_data["current_session"]["location"]
            lat = float(location["lat"])
            lng = float(location["lng"])
            accuracy = float(location["accuracy"])
        else:
            if configured_location is None and site_type not in (SITE_TYPE_OFFICE, SITE_TYPE_REMOTE):
                raise HomeAssistantError(
                    "Could not determine the correct location to use for sign out."
                )
            try:
                lat, lng, accuracy = await get_location(
                    hass,
                    config_data,
                    configured_location,
                    site_type,
                )
            except HomeAssistantError:
                set_runtime_status_reason(entry_data, "missing_location_context")
                await async_refresh_entry_state(entry_data)
                raise

        _LOGGER.debug(
            "Signing out from site_id=%s with lat=%s, lng=%s, accuracy=%s",
            site_id, lat, lng, accuracy
        )
        try:
            await api.sign_out(site_id, lat, lng, accuracy)
            set_runtime_status_reason(entry_data, None)
            if entry_data.get("current_session") is not None:
                entry_data["last_session"] = deepcopy(entry_data["current_session"])
            entry_data["current_session"] = None
            await async_save_session_state(hass, entry_id, entry_data)
            await async_refresh_entry_state(entry_data)
            _LOGGER.debug("Sign out successful")
        except Exception as e:
            set_runtime_status_reason(entry_data, "target_temporarily_unusable")
            await async_refresh_entry_state(entry_data)
            _LOGGER.error("Sign out failed: %s", e)
            raise
    return handle_sign_out
