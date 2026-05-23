"""Lifecycle tests against a real Home Assistant core object."""

from __future__ import annotations

import asyncio
import ipaddress
import json
from pathlib import Path
import shutil
import tempfile
from types import MappingProxyType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries as ce, loader
from homeassistant.bootstrap import async_from_config_dict
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

integration = __import__("custom_components.signinapp", fromlist=["dummy"])
sensor_module = __import__("custom_components.signinapp.sensor", fromlist=["dummy"])

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "config_v2"

if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def load_fixture(name: str) -> dict:
    """Load a sanitized config-v2 fixture."""
    with (FIXTURES_DIR / name).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


class FakeApi:
    """API stub for lifecycle setup tests."""

    def __init__(self, session, timezone: str = "Europe/London"):
        self._session = session
        self._timezone = timezone
        self._token = None

    def set_token(self, token: str):
        self._token = token

    async def get_config(self):
        return {
            "returningVisitor": {
                "status": "signed_in",
                "name": "Lifecycle Tester",
                "lastIn": "2026-05-22T08:30:00Z",
                "lastOut": "2026-05-21T17:00:00Z",
                "groupId": 1,
            },
            "currentVisit": {"siteId": 100},
        }


class MutableApi(FakeApi):
    """API stub with mutable config state for coordinator refresh tests."""

    def __init__(self, session, timezone: str = "Europe/London", initial_config: dict | None = None):
        super().__init__(session, timezone=timezone)
        self._config = initial_config or load_fixture("signed_out_last_active_context.json")

    async def get_config(self):
        return json.loads(json.dumps(self._config))

    async def sign_in(self, site_id: int, lat: float, lng: float, accuracy: float):
        self._config = load_fixture("signed_in_current_visit_authoritative.json")
        self._config["currentVisit"]["siteId"] = site_id
        return {"success": True}

    async def sign_out(self, site_id: int, lat: float, lng: float, accuracy: float):
        self._config = load_fixture("signed_out_last_active_context.json")
        return {"success": True}


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="signinapp-ha-"))
        self.fchmod_patcher = patch(
            "homeassistant.util.file.os.fchmod",
            create=True,
            side_effect=lambda *args, **kwargs: None,
        )
        self.fchmod_patcher.start()
        self.hass = HomeAssistant(str(self.temp_dir))
        loader.async_setup(self.hass)
        await async_from_config_dict(
            {"homeassistant": {"name": "Test", "time_zone": "Europe/London"}},
            self.hass,
        )
        http = HomeAssistantHTTP(
            self.hass,
            None,
            None,
            None,
            ["127.0.0.1"],
            8123,
            [ipaddress.ip_network("127.0.0.1/32")],
            "modern",
        )
        await http.async_initialize(
            cors_origins=[],
            use_x_forwarded_for=False,
            login_threshold=-1,
            is_ban_enabled=False,
            use_x_frame_options=True,
        )
        self.hass.http = http

    async def asyncTearDown(self):
        await self.hass.async_stop(force=True)
        self.fchmod_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def make_entry(self, *, state: ConfigEntryState = ConfigEntryState.NOT_LOADED) -> ConfigEntry:
        return ConfigEntry(
            version=1,
            minor_version=1,
            domain=integration.DOMAIN,
            title="Sign In App",
            data={
                CONF_ACCESS_TOKEN: "token-1",
                integration.CONF_REMOTE_SITE_ID: 200,
                integration.CONF_OFFICE_SITE_ID: 100,
                integration.CONF_DEVICE_TRACKER: "person.james",
                integration.CONF_OFFICE_DISTANCE: 50,
            },
            source=ce.SOURCE_USER,
            state=state,
            options={},
            discovery_keys=MappingProxyType({}),
            unique_id="visitor-1",
            entry_id="entry-1",
        )

    async def test_async_setup_initializes_store_http_and_services(self):
        result = await integration.async_setup(self.hass, {})

        self.assertTrue(result)
        self.assertIn(integration.SESSION_STORE_HASS_KEY, self.hass.data)
        self.assertEqual(self.hass.data[integration.SESSION_STATE_HASS_KEY], {})
        self.assertTrue(self.hass.services.has_service(integration.DOMAIN, integration.SERVICE_SIGN_IN))
        self.assertTrue(self.hass.services.has_service(integration.DOMAIN, integration.SERVICE_SIGN_OUT))
        self.assertEqual(len(self.hass.http.app.router.resources()), 1)

    async def test_async_setup_entry_loads_persisted_session_and_forwards_platforms(self):
        await integration.async_setup(self.hass, {})
        entry = self.make_entry(state=ConfigEntryState.SETUP_IN_PROGRESS)
        persisted_session = integration.build_session_context(
            100,
            integration.SITE_TYPE_OFFICE,
            {"lat": 51.5007, "lng": -0.1246, "accuracy": 50.0},
        )
        self.hass.data[integration.SESSION_STATE_HASS_KEY] = {
            entry.entry_id: {"current_session": persisted_session, "last_session": persisted_session}
        }

        with (
            patch("custom_components.signinapp.SignInAppApi", FakeApi),
            patch.object(
                self.hass.config_entries, "async_forward_entry_setups", AsyncMock()
            ) as forward_setups,
        ):
            result = await integration.async_setup_entry(self.hass, entry)

        self.assertTrue(result)
        self.assertIn(entry.entry_id, self.hass.data[integration.DOMAIN])
        entry_data = self.hass.data[integration.DOMAIN][entry.entry_id]
        self.assertEqual(entry_data["current_session"]["site_id"], 100)
        self.assertEqual(entry_data["last_session"]["site_type"], integration.SITE_TYPE_OFFICE)
        self.assertIsInstance(entry_data["api"], FakeApi)
        forward_setups.assert_awaited_once()

    async def test_async_setup_entry_migrates_legacy_target_fields_to_configured_locations(self):
        await integration.async_setup(self.hass, {})
        entry = self.make_entry(state=ConfigEntryState.SETUP_IN_PROGRESS)

        with (
            patch("custom_components.signinapp.SignInAppApi", FakeApi),
            patch.object(
                self.hass.config_entries, "async_forward_entry_setups", AsyncMock()
            ),
            patch.object(self.hass.config_entries, "async_get_entry", return_value=entry),
            patch.object(self.hass.config_entries, "async_update_entry") as update_entry,
        ):
            result = await integration.async_setup_entry(self.hass, entry)

        self.assertTrue(result)
        update_entry.assert_called_once()
        migrated_data = update_entry.call_args.kwargs["data"]
        self.assertEqual(
            migrated_data[integration.CONF_CONFIGURED_LOCATIONS],
            [
                {
                    "site_id": 100,
                    "site_type": "office",
                    "coordinate_behavior": "device_tracker",
                    "label": "Office",
                    "enabled": True,
                    "distance": 50,
                },
                {
                    "site_id": 200,
                    "site_type": "remote",
                    "coordinate_behavior": "remote_zero",
                    "label": "Remote",
                    "enabled": True,
                    "distance": 0.0,
                },
            ],
        )
        self.assertNotIn(integration.CONF_OFFICE_SITE_ID, migrated_data)
        self.assertNotIn(integration.CONF_REMOTE_SITE_ID, migrated_data)
        self.assertNotIn(integration.CONF_OFFICE_DISTANCE, migrated_data)
        self.assertEqual(
            self.hass.data[integration.DOMAIN][entry.entry_id]["config"][integration.CONF_CONFIGURED_LOCATIONS],
            migrated_data[integration.CONF_CONFIGURED_LOCATIONS],
        )

    async def test_restart_like_setup_recovers_signed_in_state_from_persisted_current_session(self):
        await integration.async_setup(self.hass, {})
        entry = self.make_entry(state=ConfigEntryState.SETUP_IN_PROGRESS)
        persisted_session = integration.build_session_context(
            100,
            integration.SITE_TYPE_OFFICE,
            {"lat": 51.5007, "lng": -0.1246, "accuracy": 50.0},
        )
        self.hass.data[integration.SESSION_STATE_HASS_KEY] = {
            entry.entry_id: {"current_session": persisted_session, "last_session": persisted_session}
        }
        added_entities: list[object] = []

        def add_entities(entities, update_before_add=False):
            added_entities.extend(entities)

        with (
            patch(
                "custom_components.signinapp.SignInAppApi",
                lambda session, timezone="Europe/London": MutableApi(
                    session,
                    timezone=timezone,
                    initial_config=load_fixture("signed_in_missing_current_site.json"),
                ),
            ),
            patch.object(self.hass.config_entries, "async_forward_entry_setups", AsyncMock()),
        ):
            await integration.async_setup_entry(self.hass, entry)
            await sensor_module.async_setup_entry(self.hass, entry, add_entities)

        sensor = added_entities[0]
        self.assertEqual(sensor.native_value, "signed_in")
        self.assertEqual(sensor.extra_state_attributes["active_work_location_id"], 100)
        self.assertEqual(sensor.extra_state_attributes["status_reason"], None)

    async def test_restart_like_setup_recovers_signed_out_state_from_persisted_last_session(self):
        await integration.async_setup(self.hass, {})
        entry = self.make_entry(state=ConfigEntryState.SETUP_IN_PROGRESS)
        last_session = integration.build_session_context(
            200,
            integration.SITE_TYPE_REMOTE,
            {"lat": 0.0, "lng": 0.0, "accuracy": 0.0},
        )
        self.hass.data[integration.SESSION_STATE_HASS_KEY] = {
            entry.entry_id: {"current_session": None, "last_session": last_session}
        }
        added_entities: list[object] = []

        def add_entities(entities, update_before_add=False):
            added_entities.extend(entities)

        with (
            patch(
                "custom_components.signinapp.SignInAppApi",
                lambda session, timezone="Europe/London": MutableApi(
                    session,
                    timezone=timezone,
                    initial_config=load_fixture("signed_out_last_active_context.json"),
                ),
            ),
            patch.object(self.hass.config_entries, "async_forward_entry_setups", AsyncMock()),
        ):
            await integration.async_setup_entry(self.hass, entry)
            await sensor_module.async_setup_entry(self.hass, entry, add_entities)

        sensor = added_entities[0]
        self.assertEqual(sensor.native_value, "signed_out")
        self.assertEqual(sensor.extra_state_attributes["active_work_location_id"], None)
        self.assertEqual(sensor.extra_state_attributes["last_active_work_location_id"], 200)
        self.assertEqual(sensor.extra_state_attributes["status_reason"], None)

    async def test_async_unload_entry_removes_entry_data(self):
        await integration.async_setup(self.hass, {})
        entry = self.make_entry()
        self.hass.data.setdefault(integration.DOMAIN, {})[entry.entry_id] = {
            "api": FakeApi(None),
            "config": entry.data,
            "coordinator": None,
            "current_session": None,
            "last_session": None,
        }

        with patch.object(
            self.hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
        ) as unload_platforms:
            result = await integration.async_unload_entry(self.hass, entry)

        self.assertTrue(result)
        unload_platforms.assert_awaited_once()
        self.assertNotIn(entry.entry_id, self.hass.data[integration.DOMAIN])

    async def test_sensor_async_setup_entry_creates_entity_and_coordinator(self):
        await integration.async_setup(self.hass, {})
        entry = self.make_entry(state=ConfigEntryState.SETUP_IN_PROGRESS)
        entry_data = {
            "api": FakeApi(None),
            "config": entry.data,
            "coordinator": None,
            "current_session": None,
            "last_session": None,
        }
        self.hass.data.setdefault(integration.DOMAIN, {})[entry.entry_id] = entry_data
        added_entities: list[object] = []

        def add_entities(entities, update_before_add=False):
            added_entities.extend(entities)

        await sensor_module.async_setup_entry(self.hass, entry, add_entities)

        self.assertEqual(len(added_entities), 1)
        self.assertIsNotNone(self.hass.data[integration.DOMAIN][entry.entry_id]["coordinator"])
        self.assertEqual(added_entities[0].native_value, "signed_in")
        self.assertEqual(added_entities[0].extra_state_attributes["status_class"], "signed_in")
        self.assertEqual(added_entities[0].extra_state_attributes["active_work_location_id"], 100)

    async def test_sign_in_mutation_refreshes_real_coordinator_and_sensor_state(self):
        await integration.async_setup(self.hass, {})
        entry = self.make_entry(state=ConfigEntryState.SETUP_IN_PROGRESS)
        entry_data = {
            "api": MutableApi(None, initial_config=load_fixture("signed_out_last_active_context.json")),
            "config": entry.data,
            "coordinator": None,
            "current_session": None,
            "last_session": integration.build_session_context(
                200,
                integration.SITE_TYPE_REMOTE,
                {"lat": 0.0, "lng": 0.0, "accuracy": 0.0},
            ),
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        self.hass.data.setdefault(integration.DOMAIN, {})[entry.entry_id] = entry_data
        added_entities: list[object] = []

        def add_entities(entities, update_before_add=False):
            added_entities.extend(entities)

        await sensor_module.async_setup_entry(self.hass, entry, add_entities)
        sensor = added_entities[0]
        self.hass.states.async_set(
            "person.james",
            "home",
            {"latitude": 51.5007, "longitude": -0.1246},
        )

        await integration.get_handle_sign_in(self.hass)(
            SimpleNamespace(data={integration.ATTR_SITE_TYPE: integration.SITE_TYPE_OFFICE})
        )

        self.assertEqual(sensor.native_value, "signed_in")
        self.assertEqual(sensor.extra_state_attributes["status_class"], "signed_in")
        self.assertEqual(sensor.extra_state_attributes["active_work_location_id"], 100)
        self.assertIsNone(sensor.extra_state_attributes["status_reason"])

    async def test_sign_out_mutation_refreshes_real_coordinator_and_sensor_state(self):
        await integration.async_setup(self.hass, {})
        entry = self.make_entry(state=ConfigEntryState.SETUP_IN_PROGRESS)
        current_session = integration.build_session_context(
            100,
            integration.SITE_TYPE_OFFICE,
            {"lat": 51.5007, "lng": -0.1246, "accuracy": 50.0},
        )
        entry_data = {
            "api": MutableApi(None, initial_config=load_fixture("signed_in_current_visit_authoritative.json")),
            "config": entry.data,
            "coordinator": None,
            "current_session": current_session,
            "last_session": current_session,
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        self.hass.data.setdefault(integration.DOMAIN, {})[entry.entry_id] = entry_data
        added_entities: list[object] = []

        def add_entities(entities, update_before_add=False):
            added_entities.extend(entities)

        await sensor_module.async_setup_entry(self.hass, entry, add_entities)
        sensor = added_entities[0]

        await integration.get_handle_sign_out(self.hass)(SimpleNamespace(data={}))

        self.assertEqual(sensor.native_value, "signed_out")
        self.assertEqual(sensor.extra_state_attributes["status_class"], "signed_out")
        self.assertIsNone(sensor.extra_state_attributes["active_work_location_id"])
        self.assertEqual(sensor.extra_state_attributes["last_active_work_location_id"], 100)
        self.assertIsNone(sensor.extra_state_attributes["status_reason"])

    async def test_async_save_session_state_persists_to_store(self):
        await integration.async_setup(self.hass, {})
        entry = self.make_entry()
        session_context = integration.build_session_context(
            200,
            integration.SITE_TYPE_REMOTE,
            {"lat": 0.0, "lng": 0.0, "accuracy": 0.0},
        )
        entry_data = {"current_session": session_context, "last_session": session_context}

        await integration.async_save_session_state(self.hass, entry.entry_id, entry_data)

        reloaded = await self.hass.data[integration.SESSION_STORE_HASS_KEY].async_load()
        self.assertEqual(reloaded[entry.entry_id]["current_session"]["site_type"], "remote")


if __name__ == "__main__":
    unittest.main()
