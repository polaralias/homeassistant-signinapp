"""The Sign In App integration."""
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import aiohttp_client, config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_REMOTE_SITE_ID,
    CONF_OFFICE_SITE_ID,
    CONF_DEVICE_TRACKER,
    CONF_OFFICE_DISTANCE,
)
from .api import SignInAppApi

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_SIGN_IN = "sign_in"
SERVICE_SIGN_OUT = "sign_out"

ATTR_SITE_TYPE = "site_type"
ATTR_DEVICE_ID = "device_id"
SITE_TYPE_OFFICE = "office"
SITE_TYPE_REMOTE = "remote"

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

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "config": entry.data
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
        if state:
            lat = float(state.attributes.get("latitude", 0))
            lng = float(state.attributes.get("longitude", 0))
            accuracy = float(distance)
        else:
            _LOGGER.warning("Person/Tracker entity %s not found, using 0", tracker_entity)
            lat = 0.0
            lng = 0.0
            accuracy = 0.0
    else: # Remote or Default
        lat = 0.0
        lng = 0.0
        accuracy = 0.0
    return lat, lng, accuracy

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

        _LOGGER.debug(
            "Signing in to site_id=%s with lat=%s, lng=%s, accuracy=%s",
            site_id, lat, lng, accuracy
        )
        try:
            await api.sign_in(site_id, lat, lng, accuracy)
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
        site_id = None

        # If site_type is not provided, auto-detect
        if not site_type:
            try:
                _LOGGER.debug("Auto-detecting site for sign out")
                status_data = await api.get_config()
                returning_visitor = status_data.get("returningVisitor", {})
                current_site_id = returning_visitor.get("siteId")

                if current_site_id:
                    site_id = current_site_id
                    # Try to determine site_type for location purposes
                    if site_id == config_data.get(CONF_OFFICE_SITE_ID):
                        site_type = SITE_TYPE_OFFICE
                    elif site_id == config_data.get(CONF_REMOTE_SITE_ID):
                        site_type = SITE_TYPE_REMOTE
                    else:
                        site_type = "unknown"
                    _LOGGER.debug("Auto-detected site_id: %s, site_type: %s", site_id, site_type)
                else:
                    _LOGGER.warning("Could not auto-detect current site ID. User might be signed out.")
                    pass

            except Exception as e:
                _LOGGER.error("Error fetching status for auto-sign out: %s", e)

        if not site_id:
            # Fallback to manual selection logic if auto-detect failed or site_type was provided
             if site_type == SITE_TYPE_OFFICE:
                site_id = config_data[CONF_OFFICE_SITE_ID]
             elif site_type == SITE_TYPE_REMOTE:
                site_id = config_data[CONF_REMOTE_SITE_ID]
             else:
                 # If we still don't have a site_id, we can't proceed
                 _LOGGER.warning("No site specified or detected for sign out.")
                 return

        lat, lng, accuracy = await get_location(hass, config_data, site_type)

        _LOGGER.debug(
            "Signing out from site_id=%s with lat=%s, lng=%s, accuracy=%s",
            site_id, lat, lng, accuracy
        )
        try:
            await api.sign_out(site_id, lat, lng, accuracy)
            _LOGGER.debug("Sign out successful")
        except Exception as e:
            _LOGGER.error("Sign out failed: %s", e)
            raise
    return handle_sign_out
