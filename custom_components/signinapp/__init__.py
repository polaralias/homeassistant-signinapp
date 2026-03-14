"""The Sign In App integration."""
from copy import deepcopy
import logging
from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_ACCESS_TOKEN, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client, config_validation as cv, device_registry as dr
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_REMOTE_SITE_ID,
    CONF_OFFICE_SITE_ID,
    CONF_DEVICE_TRACKER,
    CONF_OFFICE_DISTANCE,
    SESSION_STATE_HASS_KEY,
    SESSION_STORE_HASS_KEY,
    SESSION_STORE_KEY,
    SESSION_STORE_VERSION,
)
from .api import SignInAppApi
from .logic import (
    SITE_TYPE_OFFICE,
    SITE_TYPE_REMOTE,
    build_session_context,
    resolve_sign_out_context,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_SIGN_IN = "sign_in"
SERVICE_SIGN_OUT = "sign_out"

ATTR_SITE_TYPE = "site_type"
ATTR_DEVICE_ID = "device_id"

SERVICE_SCHEMA_SIGN_IN = vol.Schema({
    vol.Required(ATTR_SITE_TYPE): vol.In([SITE_TYPE_OFFICE, SITE_TYPE_REMOTE]),
    vol.Optional(ATTR_DEVICE_ID): cv.string,
})

SERVICE_SCHEMA_SIGN_OUT = vol.Schema({
    vol.Optional(ATTR_SITE_TYPE): vol.In([SITE_TYPE_OFFICE, SITE_TYPE_REMOTE]),
    vol.Optional(ATTR_DEVICE_ID): cv.string,
})

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
        hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    static_url_path,
                    static_local_path,
                    cache_headers=True,
                )
            ]
        )
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
    session = aiohttp_client.async_get_clientsession(hass)
    # Use HA's timezone
    timezone = hass.config.time_zone
    api = SignInAppApi(session, timezone=timezone)
    api.set_token(entry.data[CONF_ACCESS_TOKEN])

    session_state = hass.data.get(SESSION_STATE_HASS_KEY, {})
    persisted_session = session_state.get(entry.entry_id, {})

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "config": entry.data,
        "coordinator": None,
        "current_session": persisted_session.get("current_session"),
        "last_session": persisted_session.get("last_session"),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def get_location(hass: HomeAssistant, config_data, site_type):
    """Helper to get location based on site type."""
    if site_type == SITE_TYPE_OFFICE:
        tracker_entity = config_data[CONF_DEVICE_TRACKER]
        distance = config_data[CONF_OFFICE_DISTANCE]

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
    else: # Remote or Default
        lat = 0.0
        lng = 0.0
        accuracy = 0.0
    return lat, lng, accuracy


async def async_refresh_entry_state(entry_data):
    """Refresh the coordinator after a mutating action."""
    coordinator = entry_data.get("coordinator")
    if coordinator is not None:
        await coordinator.async_request_refresh()


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

        site_type = call.data[ATTR_SITE_TYPE]

        if site_type == SITE_TYPE_OFFICE:
            site_id = config_data[CONF_OFFICE_SITE_ID]
        else:
            site_id = config_data[CONF_REMOTE_SITE_ID]

        lat, lng, accuracy = await get_location(hass, config_data, site_type)
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
            entry_data["current_session"] = deepcopy(session_context)
            entry_data["last_session"] = deepcopy(session_context)
            await async_save_session_state(hass, entry_id, entry_data)
            await async_refresh_entry_state(entry_data)
            _LOGGER.debug("Sign in successful")
        except Exception as e:
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
        status_data = None
        if not site_type:
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
        )
        if not sign_out_context or sign_out_context.get("site_id") is None:
            raise HomeAssistantError(
                "Could not determine which site to sign out from."
            )

        site_id = sign_out_context["site_id"]
        site_type = sign_out_context.get("site_type")
        if sign_out_context.get("use_cached_location"):
            location = entry_data["current_session"]["location"]
            lat = float(location["lat"])
            lng = float(location["lng"])
            accuracy = float(location["accuracy"])
        else:
            if site_type not in (SITE_TYPE_OFFICE, SITE_TYPE_REMOTE):
                raise HomeAssistantError(
                    "Could not determine the correct location to use for sign out."
                )
            lat, lng, accuracy = await get_location(hass, config_data, site_type)

        _LOGGER.debug(
            "Signing out from site_id=%s with lat=%s, lng=%s, accuracy=%s",
            site_id, lat, lng, accuracy
        )
        try:
            await api.sign_out(site_id, lat, lng, accuracy)
            if entry_data.get("current_session") is not None:
                entry_data["last_session"] = deepcopy(entry_data["current_session"])
            entry_data["current_session"] = None
            await async_save_session_state(hass, entry_id, entry_data)
            await async_refresh_entry_state(entry_data)
            _LOGGER.debug("Sign out successful")
        except Exception as e:
            _LOGGER.error("Sign out failed: %s", e)
            raise
    return handle_sign_out
