"""Config flow for Sign In App integration."""
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    DOMAIN,
    CONF_COMPANION_CODE,
    CONF_CONFIGURED_LOCATIONS,
    CONF_COORDINATE_BEHAVIOR,
    CONF_DISTANCE,
    CONF_REMOTE_SITE_ID,
    CONF_OFFICE_SITE_ID,
    CONF_DEVICE_TRACKER,
    CONF_ENABLED,
    CONF_LABEL,
    CONF_OFFICE_DISTANCE,
    CONF_SITE_ID,
    CONF_SITE_TYPE,
    COORDINATE_BEHAVIOR_DEVICE_TRACKER,
    COORDINATE_BEHAVIOR_REMOTE_ZERO,
    DEFAULT_OFFICE_DISTANCE,
)
from .api import SignInAppApi
from .logic import (
    SITE_TYPE_OFFICE,
    SITE_TYPE_REMOTE,
    infer_coordinate_behavior,
    iter_configured_locations,
    normalize_companion_code,
)

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

    def _site_enabled_key(self, site_id: int) -> str:
        return f"site_{site_id}_enabled"

    def _site_label_key(self, site_id: int) -> str:
        return f"site_{site_id}_label"

    def _site_distance_key(self, site_id: int) -> str:
        return f"site_{site_id}_distance"

    def _defaults_configured_locations(self, defaults: dict[str, Any]) -> dict[int, dict[str, Any]]:
        """Map persisted configured locations by site id for reconfigure defaults."""
        return {
            location[CONF_SITE_ID]: location
            for location in iter_configured_locations(defaults)
            if location.get(CONF_SITE_ID) is not None
        }

    def _ordered_site_records(self, defaults: dict[str, Any]) -> list[dict[str, Any]]:
        """Merge backend-discovered sites with persisted configured locations."""
        configured_locations = self._defaults_configured_locations(defaults)
        ordered_sites = [
            {
                **site,
                "id": int(site["id"]),
                "_configured": configured_locations.get(int(site["id"])),
            }
            for site in self.sites.values()
        ]

        missing_configured_sites = []
        for site_id, configured_location in configured_locations.items():
            if site_id in self.sites:
                continue
            missing_configured_sites.append(
                {
                    "id": site_id,
                    "name": configured_location.get(CONF_LABEL) or f"Configured site {site_id}",
                    "type": configured_location.get(CONF_SITE_TYPE, "unknown"),
                    "_configured": configured_location,
                    "_missing": True,
                }
            )

        return sorted(
            ordered_sites + missing_configured_sites,
            key=lambda site: str(site.get("name", "")).lower(),
        )

    def _suggested_site_label(self, site: dict[str, Any]) -> str:
        """Prefer configured labels over backend-discovered names."""
        configured_location = site.get("_configured") or {}
        return str(configured_location.get(CONF_LABEL) or site.get("name") or f"Site {site['id']}")

    def _suggested_site_enabled(self, site: dict[str, Any]) -> bool:
        """Default discovered sites to enabled and preserve configured inclusion."""
        configured_location = site.get("_configured") or {}
        return bool(configured_location.get(CONF_ENABLED, True))

    def _suggested_site_distance(self, site: dict[str, Any]) -> int | float:
        """Use persisted distance, backend radius, or the default office distance."""
        configured_location = site.get("_configured") or {}
        configured_distance = configured_location.get(CONF_DISTANCE)
        if configured_distance is not None:
            return configured_distance

        site_location = site.get("location") if isinstance(site.get("location"), dict) else None
        site_radius = site_location.get("radius") if isinstance(site_location, dict) else None
        if isinstance(site_radius, (int, float)):
            return site_radius

        return DEFAULT_OFFICE_DISTANCE

    def _build_configured_locations(
        self,
        user_input: dict[str, Any],
        defaults: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Translate config-flow input into durable configured-location records."""
        configured_locations: list[dict[str, Any]] = []
        for site in self._ordered_site_records(defaults):
            site_id = int(site["id"])
            if not user_input.get(self._site_enabled_key(site_id), False):
                continue

            site_type = str(site.get("type", "")).lower()
            coordinate_behavior = infer_coordinate_behavior(site_type)
            if coordinate_behavior == COORDINATE_BEHAVIOR_REMOTE_ZERO:
                distance = 0.0
                normalized_site_type = SITE_TYPE_REMOTE
            else:
                distance = user_input.get(self._site_distance_key(site_id), self._suggested_site_distance(site))
                normalized_site_type = SITE_TYPE_OFFICE

            configured_locations.append(
                {
                    CONF_SITE_ID: site_id,
                    CONF_LABEL: user_input.get(self._site_label_key(site_id), self._suggested_site_label(site)),
                    CONF_ENABLED: True,
                    CONF_SITE_TYPE: normalized_site_type,
                    CONF_COORDINATE_BEHAVIOR: coordinate_behavior,
                    CONF_DISTANCE: distance,
                }
            )

        return configured_locations

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

        # Pre-fill values if reconfiguring
        defaults = {}
        if self.context.get("source") == config_entries.SOURCE_RECONFIGURE:
            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            if entry:
                defaults = entry.data

        if user_input is not None:
            configured_locations = self._build_configured_locations(user_input, defaults)

            if not configured_locations:
                errors["base"] = "site_selection_invalid"
            else:
                _LOGGER.debug("Creating entry with data: %s", user_input)
                entry_id = self.context.get("entry_id")
                entry = self.hass.config_entries.async_get_entry(entry_id) if entry_id else None
                existing_data = entry.data if entry else {}
                data = {
                    CONF_ACCESS_TOKEN: self.token or existing_data.get(CONF_ACCESS_TOKEN),
                    CONF_CONFIGURED_LOCATIONS: configured_locations,
                    CONF_DEVICE_TRACKER: user_input[CONF_DEVICE_TRACKER],
                }

                if self.context.get("source") == config_entries.SOURCE_RECONFIGURE:
                    if entry:
                        self.hass.config_entries.async_update_entry(entry, data=data)
                        await self.hass.config_entries.async_reload(entry.entry_id)
                        return self.async_abort(reason="reconfigure_successful")

                title = self.visitor_name or "Sign In App"
                return self.async_create_entry(title=title, data=data)

        schema_fields: dict[vol.Marker, object] = {}
        site_records = self._ordered_site_records(defaults)
        for site in site_records:
            site_id = int(site["id"])
            missing_site = bool(site.get("_missing"))
            schema_fields[
                vol.Required(
                    self._site_enabled_key(site_id),
                    default=self._suggested_site_enabled(site),
                )
            ] = BooleanSelector(BooleanSelectorConfig())
            schema_fields[
                vol.Required(
                    self._site_label_key(site_id),
                    description={"suggested_value": self._suggested_site_label(site)},
                )
            ] = TextSelector(TextSelectorConfig())
            if infer_coordinate_behavior(str(site.get("type", "")).lower()) != COORDINATE_BEHAVIOR_REMOTE_ZERO:
                schema_fields[
                    vol.Optional(
                        self._site_distance_key(site_id),
                        description={"suggested_value": self._suggested_site_distance(site)},
                    )
                ] = NumberSelector(
                    NumberSelectorConfig(min=0, mode=NumberSelectorMode.BOX, unit_of_measurement="m")
                )
            if missing_site:
                _LOGGER.debug("Configured site %s missing from backend discovery; preserving manual fields", site_id)

        tracker_field_kwargs = {}
        if defaults.get(CONF_DEVICE_TRACKER) is not None:
            tracker_field_kwargs["description"] = {
                "suggested_value": defaults.get(CONF_DEVICE_TRACKER)
            }
        schema_fields[vol.Required(CONF_DEVICE_TRACKER, **tracker_field_kwargs)] = EntitySelector(
            EntitySelectorConfig(domain="person")
        )
        schema = vol.Schema(schema_fields)

        if site_records:
            sites_text = "\n".join(
                [
                    (
                        f"{site['id']}: {site['name']} ({site.get('type', 'standard')})"
                        if not site.get("_missing")
                        else f"{site['id']}: {site['name']} ({site.get('type', 'unknown')}, configured but not rediscovered)"
                    )
                    for site in site_records
                ]
            )
        else:
            sites_text = "No site list is currently available from backend discovery."

        return self.async_show_form(
            step_id="sites",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "sites_list": sites_text,
                "site_fetch_status": (
                    "The site list could not be refreshed. Previously configured locations are shown when available."
                    if self.site_fetch_failed
                    else "Choose from the detected sites. Defaults are preselected when the API makes them obvious."
                ),
            },
        )
