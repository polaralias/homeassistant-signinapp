"""Config flow for Sign In App integration."""
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import (
    DOMAIN,
    CONF_COMPANION_CODE,
    CONF_REMOTE_SITE_ID,
    CONF_OFFICE_SITE_ID,
    CONF_DEVICE_TRACKER,
    CONF_OFFICE_DISTANCE,
    DEFAULT_OFFICE_DISTANCE,
)
from .api import SignInAppApi
from .logic import normalize_companion_code

_LOGGER = logging.getLogger(__name__)

class SignInAppConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sign In App."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.token = None
        self.sites = {}
        self.config_unique_id = None
        self.visitor_name = None
        self.site_fetch_failed = False

    def _store_config_context(self, config_data: dict[str, Any]) -> None:
        """Persist config-derived context for later steps."""
        self.site_fetch_failed = False
        returning_visitor = config_data.get("returningVisitor", {})
        visitor_id = returning_visitor.get("id")
        if visitor_id is not None:
            self.config_unique_id = str(visitor_id)

        self.visitor_name = returning_visitor.get("name")
        self.sites = {
            int(site["id"]): site
            for site in config_data.get("sites", [])
            if site.get("id") is not None
        }

    def _coerce_site_id(self, value: Any) -> int | None:
        """Convert a site value from UI or config to an integer."""
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _site_options(self, site_kind: str) -> list[dict[str, str]]:
        """Build selector options for office or remote sites."""
        sites = list(self.sites.values())
        if not sites:
            return []

        if site_kind == "remote":
            preferred_sites = [site for site in sites if site.get("type") == "remote"]
            if not preferred_sites:
                preferred_sites = [
                    site for site in sites if "remote" in str(site.get("name", "")).lower()
                ]
        else:
            preferred_sites = [site for site in sites if site.get("type") != "remote"]
            if not preferred_sites:
                preferred_sites = [
                    site for site in sites if "office" in str(site.get("name", "")).lower()
                ]

        options_source = preferred_sites or sites
        return [
            {"label": f"{site['name']} ({site['id']})", "value": str(site["id"])}
            for site in sorted(options_source, key=lambda site: str(site.get("name", "")).lower())
        ]

    def _suggested_site_id(self, site_kind: str, defaults: dict[str, Any]) -> str | None:
        """Infer the most likely site id for a selector."""
        config_key = CONF_REMOTE_SITE_ID if site_kind == "remote" else CONF_OFFICE_SITE_ID
        configured_site_id = self._coerce_site_id(defaults.get(config_key))
        if configured_site_id in self.sites:
            return str(configured_site_id)

        options = self._site_options(site_kind)
        if len(options) == 1:
            return options[0]["value"]

        return None

    def _suggested_office_distance(self, defaults: dict[str, Any]) -> int | float:
        """Use the configured distance or the site's geofence radius when available."""
        configured_distance = defaults.get(CONF_OFFICE_DISTANCE)
        if configured_distance is not None:
            return configured_distance

        suggested_office_site = self._suggested_site_id("office", defaults)
        office_site = self.sites.get(self._coerce_site_id(suggested_office_site))
        site_location = office_site.get("location") if office_site else None
        site_radius = site_location.get("radius") if isinstance(site_location, dict) else None
        if isinstance(site_radius, (int, float)):
            return site_radius

        return DEFAULT_OFFICE_DISTANCE

    def _site_field(
        self,
        site_kind: str,
        config_key: str,
        defaults: dict[str, Any],
    ) -> tuple[vol.Marker, object]:
        """Build a schema field for a site selector with fallback to manual entry."""
        suggested_value = self._suggested_site_id(site_kind, defaults)
        options = self._site_options(site_kind)
        if options:
            field_kwargs = {}
            if suggested_value is not None:
                field_kwargs["description"] = {"suggested_value": suggested_value}
            return (
                vol.Required(config_key, **field_kwargs),
                SelectSelector(
                    SelectSelectorConfig(options=options)
                ),
            )

        return (
            vol.Required(
                config_key,
                default=defaults.get(config_key),
            ),
            int,
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        _LOGGER.debug("Starting user step in config flow")
        errors = {}
        if user_input is not None:
            session = aiohttp_client.async_get_clientsession(self.hass)
            api = SignInAppApi(session, timezone=self.hass.config.time_zone)
            try:
                _LOGGER.debug("Attempting to connect with provided code")
                normalized_code = normalize_companion_code(user_input[CONF_COMPANION_CODE])
                self.token = await api.connect(normalized_code)
                _LOGGER.debug("Connection successful, token received")

                api.set_token(self.token)
                _LOGGER.debug("Fetching sites and config for validation and unique ID")
                config_data = await api.get_config()
                self._store_config_context(config_data)

                if self.config_unique_id:
                    await self.async_set_unique_id(self.config_unique_id)
                    self._abort_if_unique_id_configured()
                else:
                    _LOGGER.warning("Could not find unique ID in config data")

                _LOGGER.debug("Fetched %d sites", len(self.sites))

                return await self.async_step_sites()
            except Exception as e:
                _LOGGER.exception("Error connecting: %s", e)
                errors["base"] = "connect_error"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_COMPANION_CODE): str
            }),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        """Handle the reconfiguration step."""
        _LOGGER.debug("Starting reconfigure step")
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry:
            self.token = entry.data.get(CONF_ACCESS_TOKEN)

            # Fetch sites again to ensure we have the latest list
            session = aiohttp_client.async_get_clientsession(self.hass)
            api = SignInAppApi(session, timezone=self.hass.config.time_zone)
            api.set_token(self.token)
            try:
                config_data = await api.get_config()
                self._store_config_context(config_data)
                if self.config_unique_id and entry.unique_id != self.config_unique_id:
                    _LOGGER.debug("Updating entry unique ID to: %s", self.config_unique_id)
                    self.hass.config_entries.async_update_entry(entry, unique_id=self.config_unique_id)
            except Exception as e:
                _LOGGER.warning("Could not fetch sites during reconfigure: %s", e)
                self.site_fetch_failed = True

        return await self.async_step_sites()

    async def async_step_sites(self, user_input=None):
        """Handle the sites configuration step."""
        _LOGGER.debug("Starting sites step in config flow")
        errors = {}

        if user_input is not None:
            remote_site_id = self._coerce_site_id(user_input.get(CONF_REMOTE_SITE_ID))
            office_site_id = self._coerce_site_id(user_input.get(CONF_OFFICE_SITE_ID))

            if remote_site_id is None or office_site_id is None:
                errors["base"] = "site_selection_invalid"
            elif remote_site_id == office_site_id:
                errors["base"] = "duplicate_sites"
            else:
                _LOGGER.debug("Creating entry with data: %s", user_input)
                entry_id = self.context.get("entry_id")
                entry = self.hass.config_entries.async_get_entry(entry_id) if entry_id else None
                existing_data = entry.data if entry else {}
                data = {
                    CONF_ACCESS_TOKEN: self.token or existing_data.get(CONF_ACCESS_TOKEN),
                    CONF_REMOTE_SITE_ID: remote_site_id,
                    CONF_OFFICE_SITE_ID: office_site_id,
                    CONF_DEVICE_TRACKER: user_input[CONF_DEVICE_TRACKER],
                    CONF_OFFICE_DISTANCE: user_input.get(CONF_OFFICE_DISTANCE, DEFAULT_OFFICE_DISTANCE),
                }

                if self.context.get("source") == config_entries.SOURCE_RECONFIGURE:
                    if entry:
                        self.hass.config_entries.async_update_entry(entry, data=data)
                        await self.hass.config_entries.async_reload(entry.entry_id)
                        return self.async_abort(reason="reconfigure_successful")

                title = self.visitor_name or "Sign In App"
                return self.async_create_entry(title=title, data=data)

        # Pre-fill values if reconfiguring
        defaults = {}
        if self.context.get("source") == config_entries.SOURCE_RECONFIGURE:
            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            if entry:
                defaults = entry.data

        schema_fields = dict(
            [
                self._site_field("remote", CONF_REMOTE_SITE_ID, defaults),
                self._site_field("office", CONF_OFFICE_SITE_ID, defaults),
            ]
        )
        tracker_field_kwargs = {}
        if defaults.get(CONF_DEVICE_TRACKER) is not None:
            tracker_field_kwargs["description"] = {
                "suggested_value": defaults.get(CONF_DEVICE_TRACKER)
            }
        schema_fields[vol.Required(CONF_DEVICE_TRACKER, **tracker_field_kwargs)] = EntitySelector(
            EntitySelectorConfig(domain="person")
        )
        schema_fields[
            vol.Optional(
                CONF_OFFICE_DISTANCE,
                description={"suggested_value": self._suggested_office_distance(defaults)},
            )
        ] = NumberSelector(
            NumberSelectorConfig(min=0, mode=NumberSelectorMode.BOX, unit_of_measurement="m")
        )
        schema = vol.Schema(schema_fields)

        if self.sites:
            sites_text = "\n".join(
                [
                    f"{site_id}: {site['name']} ({site.get('type', 'standard')})"
                    for site_id, site in sorted(self.sites.items(), key=lambda item: str(item[1].get("name", "")).lower())
                ]
            )
        else:
            sites_text = "No site list available. Enter IDs manually."

        return self.async_show_form(
            step_id="sites",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "sites_list": sites_text,
                "site_fetch_status": (
                    "The site list could not be refreshed, so manual ID entry is shown."
                    if self.site_fetch_failed
                    else "Choose from the detected sites. Defaults are preselected when the API makes them obvious."
                ),
            },
        )
