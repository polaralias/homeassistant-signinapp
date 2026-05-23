"""Focused tests for Sign In App config-flow selection behavior."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch


config_flow_module = importlib.import_module("custom_components.signinapp.config_flow")

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "config_v2"


def load_fixture(name: str) -> dict:
    """Load a sanitized config-v2 fixture."""
    with (FIXTURES_DIR / name).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


class ConfigFlowSelectionTests(unittest.TestCase):
    def setUp(self):
        self.flow = config_flow_module.SignInAppConfigFlow()
        self.flow._store_config_context(load_fixture("signed_in_current_visit_authoritative.json"))

    def test_store_config_context_tracks_unique_id_and_sites(self):
        self.assertEqual(self.flow.visitor_name, "Sanitized Visitor")
        self.assertEqual(self.flow.sites[100]["name"], "HQ")
        self.assertEqual(self.flow.sites[200]["type"], "remote")

    def test_ordered_site_records_include_backend_discovered_sites(self):
        records = self.flow._ordered_site_records({})

        self.assertEqual([record["id"] for record in records], [100, 200])

    def test_suggested_site_label_prefers_existing_configured_override(self):
        defaults = {
            "configured_locations": [
                {"site_id": 100, "label": "Main Office", "enabled": True, "site_type": "office", "distance": 60}
            ]
        }
        records = self.flow._ordered_site_records(defaults)

        self.assertEqual(self.flow._suggested_site_label(records[0]), "Main Office")

    def test_ordered_site_records_preserve_configured_site_when_backend_list_has_drifted(self):
        defaults = {
            "configured_locations": [
                {"site_id": 999, "label": "Configured Site", "enabled": True, "site_type": "office", "distance": 50}
            ]
        }

        records = self.flow._ordered_site_records(defaults)
        missing_record = next(record for record in records if record["id"] == 999)

        self.assertTrue(missing_record["_missing"])

    def test_build_configured_locations_uses_enabled_sites_and_label_overrides(self):
        user_input = {
            "site_100_enabled": True,
            "site_100_label": "Main Office",
            "site_100_distance": 60,
            "site_200_enabled": False,
            "site_200_label": "Remote",
        }

        configured_locations = self.flow._build_configured_locations(user_input, {})

        self.assertEqual(
            configured_locations,
            [
                {
                    "site_id": 100,
                    "label": "Main Office",
                    "enabled": True,
                    "site_type": "office",
                    "coordinate_behavior": "device_tracker",
                    "distance": 60,
                }
            ],
        )


class ConfigFlowReconfigureTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.flow = config_flow_module.SignInAppConfigFlow()
        self.entry = SimpleNamespace(
            entry_id="entry-1",
            unique_id="visitor-old",
            data={
                "access_token": "token-1",
                "configured_locations": [
                    {"site_id": 100, "label": "HQ", "enabled": True, "site_type": "office", "distance": 50},
                    {"site_id": 200, "label": "Remote", "enabled": True, "site_type": "remote", "distance": 0.0},
                ],
                "device_tracker": "person.james",
            },
        )
        self.hass = SimpleNamespace(
            config=SimpleNamespace(time_zone="Europe/London"),
            data={},
            config_entries=SimpleNamespace(
                async_get_entry=lambda entry_id: self.entry if entry_id == self.entry.entry_id else None,
                async_update_entry=Mock(),
                async_reload=AsyncMock(),
            ),
        )
        self.flow.hass = self.hass
        self.flow.context = {"source": "reconfigure", "entry_id": self.entry.entry_id}

    async def test_reconfigure_updates_entry_unique_id_when_backend_identity_changes(self):
        config_data = load_fixture("signed_in_current_visit_authoritative.json")
        config_data["returningVisitor"]["id"] = "visitor-new"

        with (
            patch.object(config_flow_module, "SignInAppApi") as api_cls,
            patch.object(config_flow_module.aiohttp_client, "async_get_clientsession", return_value=object()),
        ):
            api = api_cls.return_value
            api.get_config = AsyncMock(return_value=config_data)

            result = await self.flow.async_step_reconfigure()

        self.hass.config_entries.async_update_entry.assert_called_once_with(
            self.entry,
            unique_id="visitor-new",
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "sites")
        self.assertFalse(self.flow.site_fetch_failed)
        self.assertEqual(self.flow.sites[100]["name"], "HQ")

    async def test_reconfigure_falls_back_to_manual_ids_when_site_refresh_fails(self):
        with (
            patch.object(config_flow_module, "SignInAppApi") as api_cls,
            patch.object(config_flow_module.aiohttp_client, "async_get_clientsession", return_value=object()),
        ):
            api = api_cls.return_value
            api.get_config = AsyncMock(side_effect=RuntimeError("backend unavailable"))

            result = await self.flow.async_step_reconfigure()

        self.hass.config_entries.async_update_entry.assert_not_called()
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "sites")
        self.assertTrue(self.flow.site_fetch_failed)
        self.assertIn("100: HQ", result["description_placeholders"]["sites_list"])
        self.assertIn("could not be refreshed", result["description_placeholders"]["site_fetch_status"])
        self.assertNotIn("manual", result["description_placeholders"]["site_fetch_status"].lower())


class ConfigFlowCreateEntryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.flow = config_flow_module.SignInAppConfigFlow()
        self.flow._store_config_context(load_fixture("signed_in_current_visit_authoritative.json"))
        self.flow.token = "token-1"
        self.flow.context = {"source": "user"}
        self.flow.hass = SimpleNamespace(config_entries=SimpleNamespace(async_get_entry=lambda entry_id: None))

    async def test_sites_step_creates_open_ended_configured_locations(self):
        user_input = {
            "site_100_enabled": True,
            "site_100_label": "Main Office",
            "site_100_distance": 60,
            "site_200_enabled": True,
            "site_200_label": "WFH",
            "device_tracker": "person.james",
        }

        result = await self.flow.async_step_sites(user_input)

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(
            result["data"]["configured_locations"],
            [
                {
                    "site_id": 100,
                    "label": "Main Office",
                    "enabled": True,
                    "site_type": "office",
                    "coordinate_behavior": "device_tracker",
                    "distance": 60,
                },
                {
                    "site_id": 200,
                    "label": "WFH",
                    "enabled": True,
                    "site_type": "remote",
                    "coordinate_behavior": "remote_zero",
                    "distance": 0.0,
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
