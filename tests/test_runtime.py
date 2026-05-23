"""Runtime-oriented unit tests for Sign In App service and sensor behavior."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from homeassistant.exceptions import HomeAssistantError


integration = importlib.import_module("custom_components.signinapp")
sensor_module = importlib.import_module("custom_components.signinapp.sensor")

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "config_v2"


def load_fixture(name: str) -> dict:
    """Load a sanitized config-v2 fixture."""
    with (FIXTURES_DIR / name).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


class FakeStates:
    """Tiny Home Assistant state registry shim."""

    def __init__(self, states: dict[str, object]):
        self._states = states

    def get(self, entity_id: str):
        return self._states.get(entity_id)


class FakeApi:
    """Async API stub for service handler tests."""

    def __init__(self, *, status_data: dict | None = None):
        self.status_data = status_data
        self.sign_in = AsyncMock(return_value={"success": True})
        self.sign_out = AsyncMock(return_value={"success": True})
        self.get_config = AsyncMock(return_value=status_data)


class FakeCoordinator:
    """Coordinator stub that records refresh requests."""

    def __init__(self, data: dict):
        self.data = data
        self.async_request_refresh = AsyncMock()


class ServiceHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.entry_id = "entry-1"
        self.config_data = {
            integration.CONF_REMOTE_SITE_ID: 200,
            integration.CONF_OFFICE_SITE_ID: 100,
            integration.CONF_DEVICE_TRACKER: "person.james",
            integration.CONF_OFFICE_DISTANCE: 75,
        }
        self.person_state = SimpleNamespace(
            attributes={"latitude": 51.5007, "longitude": -0.1246}
        )

    def build_hass(self, entry_data: dict) -> SimpleNamespace:
        return SimpleNamespace(
            data={integration.DOMAIN: {self.entry_id: entry_data}},
            states=FakeStates({"person.james": self.person_state}),
        )

    async def test_get_location_uses_person_coordinates_for_office(self):
        hass = self.build_hass({})

        lat, lng, accuracy = await integration.get_location(
            hass, self.config_data, None, integration.SITE_TYPE_OFFICE
        )

        self.assertEqual((lat, lng, accuracy), (51.5007, -0.1246, 75.0))

    async def test_get_location_raises_when_person_entity_missing(self):
        hass = SimpleNamespace(data={}, states=FakeStates({}))

        with self.assertRaises(HomeAssistantError):
            await integration.get_location(
                hass, self.config_data, None, integration.SITE_TYPE_OFFICE
            )

    async def test_get_location_prefers_configured_coordinate_behavior_over_site_type_hint(self):
        hass = self.build_hass({})

        lat, lng, accuracy = await integration.get_location(
            hass,
            self.config_data,
            {
                "site_id": 300,
                "label": "Remote-like site",
                "enabled": True,
                "site_type": "office",
                "coordinate_behavior": "remote_zero",
                "distance": 120,
            },
            integration.SITE_TYPE_OFFICE,
        )

        self.assertEqual((lat, lng, accuracy), (0.0, 0.0, 0.0))

    async def test_sign_in_handler_updates_cached_sessions_and_refreshes(self):
        api = FakeApi()
        coordinator = FakeCoordinator(load_fixture("signed_in_current_visit_authoritative.json"))
        entry_data = {
            "api": api,
            "config": self.config_data,
            "coordinator": coordinator,
            "current_session": None,
            "last_session": None,
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        hass = self.build_hass(entry_data)
        call = SimpleNamespace(data={integration.ATTR_SITE_TYPE: integration.SITE_TYPE_OFFICE})

        with (
            patch.object(integration, "async_save_session_state", AsyncMock()) as save_state,
            patch.object(integration, "async_refresh_entry_state", AsyncMock()) as refresh_state,
        ):
            await integration.get_handle_sign_in(hass)(call)

        api.sign_in.assert_awaited_once_with(100, 51.5007, -0.1246, 75.0)
        self.assertEqual(entry_data["current_session"]["site_id"], 100)
        self.assertEqual(entry_data["current_session"]["site_type"], integration.SITE_TYPE_OFFICE)
        self.assertEqual(entry_data["last_session"], entry_data["current_session"])
        self.assertIsNone(entry_data[integration.RUNTIME_STATUS_REASON_KEY])
        save_state.assert_awaited_once()
        refresh_state.assert_awaited_once_with(entry_data)

    async def test_sign_in_handler_accepts_concrete_site_id_input(self):
        api = FakeApi()
        entry_data = {
            "api": api,
            "config": {
                integration.CONF_DEVICE_TRACKER: "person.james",
                integration.CONF_CONFIGURED_LOCATIONS: [
                    {
                        "site_id": 100,
                        "label": "Main Office",
                        "enabled": True,
                        "site_type": "office",
                        "coordinate_behavior": "device_tracker",
                        "distance": 60,
                    },
                    {
                        "site_id": 300,
                        "label": "Site B",
                        "enabled": True,
                        "site_type": "office",
                        "coordinate_behavior": "device_tracker",
                        "distance": 90,
                    },
                ],
            },
            "coordinator": None,
            "current_session": None,
            "last_session": None,
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        hass = self.build_hass(entry_data)
        call = SimpleNamespace(data={integration.ATTR_SITE_ID: 300})

        with (
            patch.object(integration, "async_save_session_state", AsyncMock()) as save_state,
            patch.object(integration, "async_refresh_entry_state", AsyncMock()) as refresh_state,
        ):
            await integration.get_handle_sign_in(hass)(call)

        api.sign_in.assert_awaited_once_with(300, 51.5007, -0.1246, 90.0)
        self.assertEqual(entry_data["current_session"]["site_id"], 300)
        self.assertEqual(entry_data["current_session"]["site_type"], integration.SITE_TYPE_OFFICE)
        save_state.assert_awaited_once()
        refresh_state.assert_awaited_once_with(entry_data)

    async def test_sign_in_handler_rejects_ambiguous_office_hint_when_multiple_targets_match(self):
        api = FakeApi()
        entry_data = {
            "api": api,
            "config": {
                integration.CONF_DEVICE_TRACKER: "person.james",
                integration.CONF_CONFIGURED_LOCATIONS: [
                    {
                        "site_id": 100,
                        "label": "Main Office",
                        "enabled": True,
                        "site_type": "office",
                        "coordinate_behavior": "device_tracker",
                        "distance": 60,
                    },
                    {
                        "site_id": 300,
                        "label": "Site B",
                        "enabled": True,
                        "site_type": "office",
                        "coordinate_behavior": "device_tracker",
                        "distance": 90,
                    },
                ],
            },
            "coordinator": None,
            "current_session": None,
            "last_session": None,
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        hass = self.build_hass(entry_data)
        call = SimpleNamespace(data={integration.ATTR_SITE_TYPE: integration.SITE_TYPE_OFFICE})

        with (
            patch.object(integration, "async_save_session_state", AsyncMock()) as save_state,
            patch.object(integration, "async_refresh_entry_state", AsyncMock()) as refresh_state,
        ):
            with self.assertRaises(HomeAssistantError):
                await integration.get_handle_sign_in(hass)(call)

        api.sign_in.assert_not_awaited()
        self.assertEqual(entry_data[integration.RUNTIME_STATUS_REASON_KEY], "routing_ambiguous")
        save_state.assert_not_awaited()
        refresh_state.assert_awaited_once_with(entry_data)

    async def test_sign_out_handler_uses_backend_current_visit_for_target_resolution(self):
        api = FakeApi(status_data=load_fixture("signed_in_current_visit_authoritative.json"))
        current_session = integration.build_session_context(
            100,
            integration.SITE_TYPE_OFFICE,
            {"lat": 51.5007, "lng": -0.1246, "accuracy": 75.0},
        )
        entry_data = {
            "api": api,
            "config": self.config_data,
            "coordinator": None,
            "current_session": current_session,
            "last_session": None,
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        hass = self.build_hass(entry_data)
        call = SimpleNamespace(data={})

        with (
            patch.object(integration, "async_save_session_state", AsyncMock()) as save_state,
            patch.object(integration, "async_refresh_entry_state", AsyncMock()) as refresh_state,
        ):
            await integration.get_handle_sign_out(hass)(call)

        api.get_config.assert_awaited_once()
        api.sign_out.assert_awaited_once_with(100, 51.5007, -0.1246, 75.0)
        self.assertIsNone(entry_data["current_session"])
        self.assertEqual(entry_data["last_session"]["site_id"], 100)
        self.assertIsNone(entry_data[integration.RUNTIME_STATUS_REASON_KEY])
        save_state.assert_awaited_once()
        refresh_state.assert_awaited_once_with(entry_data)

    async def test_sign_in_handler_fails_hard_when_office_location_context_is_missing(self):
        api = FakeApi()
        coordinator = FakeCoordinator(load_fixture("signed_in_current_visit_authoritative.json"))
        entry_data = {
            "api": api,
            "config": self.config_data,
            "coordinator": coordinator,
            "current_session": None,
            "last_session": None,
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        hass = SimpleNamespace(
            data={integration.DOMAIN: {self.entry_id: entry_data}},
            states=FakeStates({}),
        )
        call = SimpleNamespace(data={integration.ATTR_SITE_TYPE: integration.SITE_TYPE_OFFICE})

        with (
            patch.object(integration, "async_save_session_state", AsyncMock()) as save_state,
            patch.object(integration, "async_refresh_entry_state", AsyncMock()) as refresh_state,
        ):
            with self.assertRaises(HomeAssistantError):
                await integration.get_handle_sign_in(hass)(call)

        api.sign_in.assert_not_awaited()
        self.assertIsNone(entry_data["current_session"])
        self.assertIsNone(entry_data["last_session"])
        self.assertEqual(entry_data[integration.RUNTIME_STATUS_REASON_KEY], "missing_location_context")
        save_state.assert_not_awaited()
        refresh_state.assert_awaited_once_with(entry_data)

    async def test_sign_out_handler_fails_hard_for_explicit_office_target_when_location_context_is_missing(self):
        api = FakeApi()
        current_session = integration.build_session_context(
            200,
            integration.SITE_TYPE_REMOTE,
            {"lat": 0.0, "lng": 0.0, "accuracy": 0.0},
        )
        entry_data = {
            "api": api,
            "config": self.config_data,
            "coordinator": None,
            "current_session": current_session,
            "last_session": None,
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        hass = SimpleNamespace(
            data={integration.DOMAIN: {self.entry_id: entry_data}},
            states=FakeStates({}),
        )
        call = SimpleNamespace(data={integration.ATTR_SITE_TYPE: integration.SITE_TYPE_OFFICE})

        with (
            patch.object(integration, "async_save_session_state", AsyncMock()) as save_state,
            patch.object(integration, "async_refresh_entry_state", AsyncMock()) as refresh_state,
        ):
            with self.assertRaises(HomeAssistantError):
                await integration.get_handle_sign_out(hass)(call)

        api.sign_out.assert_not_awaited()
        self.assertEqual(entry_data["current_session"]["site_id"], 200)
        self.assertIsNone(entry_data["last_session"])
        self.assertEqual(entry_data[integration.RUNTIME_STATUS_REASON_KEY], "missing_location_context")
        save_state.assert_not_awaited()
        refresh_state.assert_awaited_once_with(entry_data)

    async def test_sign_in_handler_marks_target_temporarily_unusable_when_api_fails(self):
        api = FakeApi()
        api.sign_in = AsyncMock(side_effect=RuntimeError("backend 503"))
        entry_data = {
            "api": api,
            "config": self.config_data,
            "coordinator": None,
            "current_session": None,
            "last_session": None,
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        hass = self.build_hass(entry_data)
        call = SimpleNamespace(data={integration.ATTR_SITE_TYPE: integration.SITE_TYPE_OFFICE})

        with (
            patch.object(integration, "async_save_session_state", AsyncMock()) as save_state,
            patch.object(integration, "async_refresh_entry_state", AsyncMock()) as refresh_state,
        ):
            with self.assertRaises(RuntimeError):
                await integration.get_handle_sign_in(hass)(call)

        self.assertEqual(entry_data[integration.RUNTIME_STATUS_REASON_KEY], "target_temporarily_unusable")
        self.assertIsNone(entry_data["current_session"])
        save_state.assert_not_awaited()
        refresh_state.assert_awaited_once_with(entry_data)

    async def test_explicit_remote_sign_out_hint_does_not_fall_back_to_conflicting_office_session(self):
        api = FakeApi()
        current_session = integration.build_session_context(
            100,
            integration.SITE_TYPE_OFFICE,
            {"lat": 51.5007, "lng": -0.1246, "accuracy": 75.0},
        )
        entry_data = {
            "api": api,
            "config": self.config_data,
            "coordinator": None,
            "current_session": current_session,
            "last_session": None,
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        hass = self.build_hass(entry_data)
        call = SimpleNamespace(data={integration.ATTR_SITE_TYPE: integration.SITE_TYPE_REMOTE})

        with (
            patch.object(integration, "async_save_session_state", AsyncMock()) as save_state,
            patch.object(integration, "async_refresh_entry_state", AsyncMock()) as refresh_state,
        ):
            await integration.get_handle_sign_out(hass)(call)

        api.sign_out.assert_awaited_once_with(200, 0.0, 0.0, 0.0)
        self.assertIsNone(entry_data["current_session"])
        self.assertEqual(entry_data["last_session"]["site_id"], 100)
        self.assertIsNone(entry_data[integration.RUNTIME_STATUS_REASON_KEY])
        save_state.assert_awaited_once()
        refresh_state.assert_awaited_once_with(entry_data)

    async def test_explicit_office_sign_out_hint_does_not_fall_back_to_conflicting_remote_session(self):
        api = FakeApi()
        current_session = integration.build_session_context(
            200,
            integration.SITE_TYPE_REMOTE,
            {"lat": 0.0, "lng": 0.0, "accuracy": 0.0},
        )
        entry_data = {
            "api": api,
            "config": self.config_data,
            "coordinator": None,
            "current_session": current_session,
            "last_session": None,
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        hass = self.build_hass(entry_data)
        call = SimpleNamespace(data={integration.ATTR_SITE_TYPE: integration.SITE_TYPE_OFFICE})

        with (
            patch.object(integration, "async_save_session_state", AsyncMock()) as save_state,
            patch.object(integration, "async_refresh_entry_state", AsyncMock()) as refresh_state,
        ):
            await integration.get_handle_sign_out(hass)(call)

        api.sign_out.assert_awaited_once_with(100, 51.5007, -0.1246, 75.0)
        self.assertIsNone(entry_data["current_session"])
        self.assertEqual(entry_data["last_session"]["site_id"], 200)
        self.assertIsNone(entry_data[integration.RUNTIME_STATUS_REASON_KEY])
        save_state.assert_awaited_once()
        refresh_state.assert_awaited_once_with(entry_data)

    async def test_sign_out_handler_rejects_ambiguous_office_hint_when_multiple_targets_match(self):
        api = FakeApi()
        entry_data = {
            "api": api,
            "config": {
                integration.CONF_DEVICE_TRACKER: "person.james",
                integration.CONF_CONFIGURED_LOCATIONS: [
                    {
                        "site_id": 100,
                        "label": "Main Office",
                        "enabled": True,
                        "site_type": "office",
                        "coordinate_behavior": "device_tracker",
                        "distance": 60,
                    },
                    {
                        "site_id": 300,
                        "label": "Site B",
                        "enabled": True,
                        "site_type": "office",
                        "coordinate_behavior": "device_tracker",
                        "distance": 90,
                    },
                ],
            },
            "coordinator": None,
            "current_session": None,
            "last_session": None,
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        hass = self.build_hass(entry_data)
        call = SimpleNamespace(data={integration.ATTR_SITE_TYPE: integration.SITE_TYPE_OFFICE})

        with (
            patch.object(integration, "async_save_session_state", AsyncMock()) as save_state,
            patch.object(integration, "async_refresh_entry_state", AsyncMock()) as refresh_state,
        ):
            with self.assertRaises(HomeAssistantError):
                await integration.get_handle_sign_out(hass)(call)

        api.sign_out.assert_not_awaited()
        self.assertEqual(entry_data[integration.RUNTIME_STATUS_REASON_KEY], "routing_ambiguous")
        save_state.assert_not_awaited()
        refresh_state.assert_awaited_once_with(entry_data)

    async def test_sign_out_handler_uses_matching_current_session_to_disambiguate_office_hint(self):
        api = FakeApi()
        current_session = integration.build_session_context(
            300,
            integration.SITE_TYPE_OFFICE,
            {"lat": 51.5007, "lng": -0.1246, "accuracy": 90.0},
        )
        entry_data = {
            "api": api,
            "config": {
                integration.CONF_DEVICE_TRACKER: "person.james",
                integration.CONF_CONFIGURED_LOCATIONS: [
                    {
                        "site_id": 100,
                        "label": "Main Office",
                        "enabled": True,
                        "site_type": "office",
                        "coordinate_behavior": "device_tracker",
                        "distance": 60,
                    },
                    {
                        "site_id": 300,
                        "label": "Site B",
                        "enabled": True,
                        "site_type": "office",
                        "coordinate_behavior": "device_tracker",
                        "distance": 90,
                    },
                ],
            },
            "coordinator": None,
            "current_session": current_session,
            "last_session": None,
            integration.RUNTIME_STATUS_REASON_KEY: None,
        }
        hass = self.build_hass(entry_data)
        call = SimpleNamespace(data={integration.ATTR_SITE_TYPE: integration.SITE_TYPE_OFFICE})

        with (
            patch.object(integration, "async_save_session_state", AsyncMock()) as save_state,
            patch.object(integration, "async_refresh_entry_state", AsyncMock()) as refresh_state,
        ):
            await integration.get_handle_sign_out(hass)(call)

        api.sign_out.assert_awaited_once_with(300, 51.5007, -0.1246, 90.0)
        self.assertIsNone(entry_data["current_session"])
        self.assertEqual(entry_data["last_session"]["site_id"], 300)
        self.assertIsNone(entry_data[integration.RUNTIME_STATUS_REASON_KEY])
        save_state.assert_awaited_once()
        refresh_state.assert_awaited_once_with(entry_data)


class SensorProjectionTests(unittest.TestCase):
    def test_sensor_projects_signed_in_state_and_attributes(self):
        entry = SimpleNamespace(entry_id="entry-1", unique_id="visitor-1", data={"office_site_id": 100, "remote_site_id": 200})
        coordinator = FakeCoordinator(load_fixture("signed_in_current_visit_authoritative.json"))
        hass = SimpleNamespace(
            data={
                sensor_module.DOMAIN: {
                    entry.entry_id: {"current_session": None, "last_session": None}
                }
            }
        )

        sensor = sensor_module.SignInAppSensor(hass, coordinator, entry)

        self.assertEqual(sensor.native_value, "signed_in")
        self.assertEqual(sensor.extra_state_attributes["status_class"], "signed_in")
        self.assertEqual(sensor.extra_state_attributes["active_work_location_id"], 100)
        self.assertEqual(sensor.extra_state_attributes["active_work_location_label"], "HQ")
        self.assertEqual(sensor.extra_state_attributes["last_active_work_location_id"], 100)
        self.assertEqual(sensor.extra_state_attributes["status_reason"], None)
        self.assertEqual(sensor.entity_picture, "/signinapp_static/icon.png")

    def test_sensor_uses_last_session_for_signed_out_projection(self):
        entry = SimpleNamespace(entry_id="entry-1", unique_id=None, data={"office_site_id": 100, "remote_site_id": 200})
        coordinator = FakeCoordinator(load_fixture("signed_out_last_active_context.json"))
        hass = SimpleNamespace(
            data={
                sensor_module.DOMAIN: {
                    entry.entry_id: {
                        "current_session": None,
                        "last_session": {"site_id": 200, "site_type": "remote", "location": {"lat": 0.0, "lng": 0.0, "accuracy": 0.0}},
                    }
                }
            }
        )

        sensor = sensor_module.SignInAppSensor(hass, coordinator, entry)

        self.assertEqual(sensor.native_value, "signed_out")
        self.assertEqual(sensor.extra_state_attributes["status_class"], "signed_out")
        self.assertEqual(sensor.extra_state_attributes["active_work_location_id"], None)
        self.assertEqual(sensor.extra_state_attributes["last_active_work_location_id"], 200)
        self.assertEqual(sensor.extra_state_attributes["last_active_work_location_label"], "Remote")

    def test_sensor_projects_unknown_reason_when_backend_data_is_missing(self):
        entry = SimpleNamespace(entry_id="entry-1", unique_id="visitor-1", data={"office_site_id": 100, "remote_site_id": 200})
        coordinator = FakeCoordinator(None)
        hass = SimpleNamespace(
            data={
                sensor_module.DOMAIN: {
                    entry.entry_id: {"current_session": None, "last_session": None}
                }
            }
        )

        sensor = sensor_module.SignInAppSensor(hass, coordinator, entry)

        self.assertEqual(sensor.native_value, "unknown")
        self.assertEqual(
            sensor.extra_state_attributes,
            {
                "status_class": "unknown",
                "active_work_location_id": None,
                "active_work_location_label": None,
                "last_active_work_location_id": None,
                "last_active_work_location_label": None,
                "status_reason": "backend_unavailable",
            },
        )

    def test_sensor_projects_unknown_reason_when_backend_is_ambiguous(self):
        entry = SimpleNamespace(entry_id="entry-1", unique_id="visitor-1", data={"office_site_id": 100, "remote_site_id": 200})
        coordinator = FakeCoordinator(load_fixture("signed_in_missing_current_site.json"))
        hass = SimpleNamespace(
            data={
                sensor_module.DOMAIN: {
                    entry.entry_id: {"current_session": None, "last_session": None}
                }
            }
        )

        sensor = sensor_module.SignInAppSensor(hass, coordinator, entry)

        self.assertEqual(sensor.native_value, "unknown")
        self.assertEqual(sensor.extra_state_attributes["status_reason"], "routing_ambiguous")

    def test_sensor_projects_unknown_reason_when_backend_site_is_not_configured(self):
        entry = SimpleNamespace(entry_id="entry-1", unique_id="visitor-1", data={"office_site_id": 100, "remote_site_id": 200})
        coordinator = FakeCoordinator(load_fixture("signed_in_unconfigured_site.json"))
        hass = SimpleNamespace(
            data={
                sensor_module.DOMAIN: {
                    entry.entry_id: {"current_session": None, "last_session": None}
                }
            }
        )

        sensor = sensor_module.SignInAppSensor(hass, coordinator, entry)

        self.assertEqual(sensor.native_value, "unknown")
        self.assertEqual(sensor.extra_state_attributes["status_reason"], "target_not_configured")

    def test_sensor_projects_unknown_reason_when_backend_contract_is_missing_status(self):
        entry = SimpleNamespace(entry_id="entry-1", unique_id="visitor-1", data={"office_site_id": 100, "remote_site_id": 200})
        coordinator = FakeCoordinator(load_fixture("backend_contract_missing_status.json"))
        hass = SimpleNamespace(
            data={
                sensor_module.DOMAIN: {
                    entry.entry_id: {"current_session": None, "last_session": None}
                }
            }
        )

        sensor = sensor_module.SignInAppSensor(hass, coordinator, entry)

        self.assertEqual(sensor.native_value, "unknown")
        self.assertEqual(sensor.extra_state_attributes["status_reason"], "backend_contract_mismatch")

    def test_sensor_projects_runtime_reason_when_backend_state_is_otherwise_known(self):
        entry = SimpleNamespace(entry_id="entry-1", unique_id="visitor-1", data={"office_site_id": 100, "remote_site_id": 200})
        coordinator = FakeCoordinator(load_fixture("signed_out_last_active_context.json"))
        hass = SimpleNamespace(
            data={
                sensor_module.DOMAIN: {
                    entry.entry_id: {
                        "current_session": None,
                        "last_session": {"site_id": 200, "site_type": "remote", "location": {"lat": 0.0, "lng": 0.0, "accuracy": 0.0}},
                        integration.RUNTIME_STATUS_REASON_KEY: "target_temporarily_unusable",
                    }
                }
            }
        )

        sensor = sensor_module.SignInAppSensor(hass, coordinator, entry)

        self.assertEqual(sensor.native_value, "signed_out")
        self.assertEqual(sensor.extra_state_attributes["status_reason"], "target_temporarily_unusable")


class DriftIssueTests(unittest.TestCase):
    def test_creates_issue_when_backend_site_list_drops_configured_site(self):
        hass = SimpleNamespace()
        entry = SimpleNamespace(
            entry_id="entry-1",
            data={"office_site_id": 100, "remote_site_id": 200},
        )
        status_data = load_fixture("signed_in_current_visit_authoritative.json")
        status_data["sites"] = [site for site in status_data["sites"] if site["id"] != 200]

        with (
            patch.object(integration.issue_registry, "async_create_issue") as create_issue,
            patch.object(integration.issue_registry, "async_delete_issue") as delete_issue,
        ):
            integration.async_sync_config_drift_issue(hass, entry, status_data)

        create_issue.assert_called_once()
        delete_issue.assert_not_called()

    def test_clears_issue_when_backend_sites_match_configured_targets(self):
        hass = SimpleNamespace()
        entry = SimpleNamespace(
            entry_id="entry-1",
            data={"office_site_id": 100, "remote_site_id": 200},
        )
        status_data = load_fixture("signed_in_current_visit_authoritative.json")

        with (
            patch.object(integration.issue_registry, "async_create_issue") as create_issue,
            patch.object(integration.issue_registry, "async_delete_issue") as delete_issue,
        ):
            integration.async_sync_config_drift_issue(hass, entry, status_data)

        create_issue.assert_not_called()
        delete_issue.assert_called_once_with(
            hass,
            integration.DOMAIN,
            f"{integration.DRIFT_ISSUE_ID_PREFIX}_{entry.entry_id}",
        )

    def test_creates_issue_when_backend_site_type_drifts(self):
        hass = SimpleNamespace()
        entry = SimpleNamespace(
            entry_id="entry-1",
            data={"office_site_id": 100, "remote_site_id": 200},
        )
        original_data = dict(entry.data)
        status_data = load_fixture("signed_in_current_visit_authoritative.json")
        for site in status_data["sites"]:
            if site["id"] == 200:
                site["type"] = "office"

        with (
            patch.object(integration.issue_registry, "async_create_issue") as create_issue,
            patch.object(integration.issue_registry, "async_delete_issue") as delete_issue,
        ):
            integration.async_sync_config_drift_issue(hass, entry, status_data)

        create_issue.assert_called_once()
        delete_issue.assert_not_called()
        self.assertEqual(entry.data, original_data)

    def test_drift_detection_does_not_raise_issue_without_backend_site_list(self):
        hass = SimpleNamespace()
        entry = SimpleNamespace(
            entry_id="entry-1",
            data={"office_site_id": 100, "remote_site_id": 200},
        )
        status_data = {"returningVisitor": {"status": "signed_in"}}

        with (
            patch.object(integration.issue_registry, "async_create_issue") as create_issue,
            patch.object(integration.issue_registry, "async_delete_issue") as delete_issue,
        ):
            integration.async_sync_config_drift_issue(hass, entry, status_data)

        create_issue.assert_not_called()
        delete_issue.assert_called_once_with(
            hass,
            integration.DOMAIN,
            f"{integration.DRIFT_ISSUE_ID_PREFIX}_{entry.entry_id}",
        )


if __name__ == "__main__":
    unittest.main()
