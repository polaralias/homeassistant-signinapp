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
        self._site_records = []
        self._site_index = 0
        self._site_input = {}

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

    def _configuration_defaults(self) -> dict[str, Any]:
        """Read persisted defaults without changing the config entry."""
        if self.context.get("source") == config_entries.SOURCE_RECONFIGURE:
            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            if entry:
                return entry.data
        return {}

    async def async_step_sites(self, user_input=None):
        """Choose the person tracker before configuring each discovered site."""
        defaults = self._configuration_defaults()
        self._site_records = self._ordered_site_records(defaults)
        errors = {}
        if user_input is not None:
            if not self._site_records:
                errors["base"] = "no_sites_available"
            else:
                self._site_index = 0
                self._site_input = {
                    CONF_DEVICE_TRACKER: user_input[CONF_DEVICE_TRACKER]
                }
                return await self.async_step_site()

        tracker_field_kwargs = {}
        if defaults.get(CONF_DEVICE_TRACKER) is not None:
            tracker_field_kwargs["description"] = {
                "suggested_value": defaults[CONF_DEVICE_TRACKER]
            }
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE_TRACKER, **tracker_field_kwargs
                ): EntitySelector(EntitySelectorConfig(domain="person"))
            }
        )
        sites_text = (
            "\n".join(
                f"{site['name']} ({site.get('type', 'standard')})"
                for site in self._site_records
            )
            or "No site list is currently available from backend discovery."
        )
        return self.async_show_form(
            step_id="sites",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
            description_placeholders={
                "sites_list": sites_text,
                "site_fetch_status": (
                    "The site list could not be refreshed. Previously configured locations are shown when available."
                    if self.site_fetch_failed
                    else "Choose your person tracker, then review each detected site."
                ),
            },
        )

    async def async_step_site(self, user_input=None):
        """Use stable translatable field keys for every site."""
        if not self._site_records:
            return await self.async_step_sites()
        errors = {}
        site = self._site_records[self._site_index]
        site_id = int(site["id"])
        if user_input is not None:
            self._site_input[self._site_enabled_key(site_id)] = user_input[CONF_ENABLED]
            self._site_input[self._site_label_key(site_id)] = user_input[CONF_LABEL]
            self._site_input[self._site_distance_key(site_id)] = user_input.get(
                CONF_DISTANCE, self._suggested_site_distance(site)
            )
            self._site_index += 1
            if self._site_index < len(self._site_records):
                return await self.async_step_site()
            configured_locations = self._build_configured_locations(
                self._site_input, self._configuration_defaults()
            )
            if configured_locations:
                return await self._async_finish_sites(configured_locations)
            # Preserve all answers while allowing the user to enable a site.
            self._site_index = 0
            site = self._site_records[0]
            site_id = int(site["id"])
            errors["base"] = "site_selection_invalid"

        schema_fields = {
            vol.Required(
                CONF_ENABLED,
                default=self._site_input.get(
                    self._site_enabled_key(site_id), self._suggested_site_enabled(site)
                ),
            ): BooleanSelector(BooleanSelectorConfig()),
            vol.Required(
                CONF_LABEL,
                description={
                    "suggested_value": self._site_input.get(
                        self._site_label_key(site_id), self._suggested_site_label(site)
                    )
                },
            ): TextSelector(TextSelectorConfig()),
        }
        if (
            infer_coordinate_behavior(str(site.get("type", "")).lower())
            != COORDINATE_BEHAVIOR_REMOTE_ZERO
        ):
            schema_fields[
                vol.Optional(
                    CONF_DISTANCE,
                    description={
                        "suggested_value": self._site_input.get(
                            self._site_distance_key(site_id),
                            self._suggested_site_distance(site),
                        )
                    },
                )
            ] = NumberSelector(
                NumberSelectorConfig(
                    min=0, mode=NumberSelectorMode.BOX, unit_of_measurement="m"
                )
            )
        return self.async_show_form(
            step_id="site",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
            last_step=self._site_index == len(self._site_records) - 1,
            description_placeholders={
                "site_name": self._suggested_site_label(site),
                "progress": f"{self._site_index + 1} / {len(self._site_records)}",
                "site_status": (
                    "This previously configured site was not rediscovered. Its saved settings are available for review."
                    if site.get("_missing")
                    else "Review whether to include this site and adjust its settings."
                ),
            },
        )

    async def _async_finish_sites(self, configured_locations):
        """Persist confirmed routing only after every site has been reviewed."""
        entry_id = self.context.get("entry_id")
        entry = self.hass.config_entries.async_get_entry(entry_id) if entry_id else None
        existing_data = entry.data if entry else {}
        data = {
            CONF_ACCESS_TOKEN: self.token or existing_data.get(CONF_ACCESS_TOKEN),
            CONF_CONFIGURED_LOCATIONS: configured_locations,
            CONF_DEVICE_TRACKER: self._site_input[CONF_DEVICE_TRACKER],
        }
        if self.context.get("source") == config_entries.SOURCE_RECONFIGURE and entry:
            self.hass.config_entries.async_update_entry(entry, data=data)
            await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_abort(reason="reconfigure_successful")
        return self.async_create_entry(
            title=self.visitor_name or "Sign In App", data=data
        )
