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
        self.flow._store_config_context(
            load_fixture("signed_in_current_visit_authoritative.json")
        )

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
                {
                    "site_id": 100,
                    "label": "Main Office",
                    "enabled": True,
                    "site_type": "office",
                    "distance": 60,
                }
            ]
        }
        records = self.flow._ordered_site_records(defaults)

        self.assertEqual(self.flow._suggested_site_label(records[0]), "Main Office")

    def test_ordered_site_records_preserve_configured_site_when_backend_list_has_drifted(
        self,
    ):
        defaults = {
            "configured_locations": [
                {
                    "site_id": 999,
                    "label": "Configured Site",
                    "enabled": True,
                    "site_type": "office",
                    "distance": 50,
                }
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
                    {
                        "site_id": 100,
                        "label": "HQ",
                        "enabled": True,
                        "site_type": "office",
                        "distance": 50,
                    },
                    {
                        "site_id": 200,
                        "label": "Remote",
                        "enabled": True,
                        "site_type": "remote",
                        "distance": 0.0,
                    },
                ],
                "device_tracker": "person.james",
            },
        )
        self.hass = SimpleNamespace(
            config=SimpleNamespace(time_zone="Europe/London"),
            data={},
            config_entries=SimpleNamespace(
                async_get_entry=lambda entry_id: (
                    self.entry if entry_id == self.entry.entry_id else None
                ),
                async_update_entry=Mock(),
                async_reload=AsyncMock(),
            ),
        )
        self.flow.hass = self.hass
        self.flow.context = {"source": "reconfigure", "entry_id": self.entry.entry_id}

    async def test_reconfigure_updates_entry_unique_id_when_backend_identity_changes(
        self,
    ):
        config_data = load_fixture("signed_in_current_visit_authoritative.json")
        config_data["returningVisitor"]["id"] = "visitor-new"

        with (
            patch.object(config_flow_module, "SignInAppApi") as api_cls,
            patch.object(
                config_flow_module.aiohttp_client,
                "async_get_clientsession",
                return_value=object(),
            ),
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
            patch.object(
                config_flow_module.aiohttp_client,
                "async_get_clientsession",
                return_value=object(),
            ),
        ):
            api = api_cls.return_value
            api.get_config = AsyncMock(side_effect=RuntimeError("backend unavailable"))

            result = await self.flow.async_step_reconfigure()

        self.hass.config_entries.async_update_entry.assert_not_called()
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "sites")
        self.assertTrue(self.flow.site_fetch_failed)
        self.assertIn("HQ", result["description_placeholders"]["sites_list"])
        self.assertIn(
            "could not be refreshed",
            result["description_placeholders"]["site_fetch_status"],
        )
        self.assertNotIn(
            "manual", result["description_placeholders"]["site_fetch_status"].lower()
        )


class ConfigFlowCreateEntryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.flow = config_flow_module.SignInAppConfigFlow()
        self.flow._store_config_context(
            load_fixture("signed_in_current_visit_authoritative.json")
        )
        self.flow.token = "token-1"
        self.flow.context = {"source": "user"}
        self.flow.hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_get_entry=lambda entry_id: None)
        )

    async def test_sites_step_creates_open_ended_configured_locations(self):
        first = await self.flow.async_step_sites({"device_tracker": "person.james"})
        self.assertEqual(first["step_id"], "site")
        await self.flow.async_step_site(
            {"enabled": True, "label": "Main Office", "distance": 60}
        )
        result = await self.flow.async_step_site({"enabled": True, "label": "WFH"})

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


class TranslatedSiteFormTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.flow = config_flow_module.SignInAppConfigFlow()
        self.flow._store_config_context(
            load_fixture("signed_in_current_visit_authoritative.json")
        )
        self.flow.token = "token-1"
        self.flow.context = {"source": "user"}
        self.flow.hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_get_entry=lambda entry_id: None)
        )

    async def test_forms_only_emit_translatable_stable_field_keys(self):
        result = await self.flow.async_step_sites()
        self.assertEqual(
            {key.schema for key in result["data_schema"].schema}, {"device_tracker"}
        )
        result = await self.flow.async_step_sites({"device_tracker": "person.test"})
        self.assertEqual(result["step_id"], "site")
        self.assertFalse(result["last_step"])
        self.assertEqual(
            {key.schema for key in result["data_schema"].schema},
            {"enabled", "label", "distance"},
        )
        self.assertEqual(result["description_placeholders"]["site_name"], "HQ")
        result = await self.flow.async_step_site(
            {"enabled": True, "label": "Office", "distance": 0}
        )
        self.assertEqual(
            {key.schema for key in result["data_schema"].schema}, {"enabled", "label"}
        )
        self.assertTrue(result["last_step"])
        self.assertEqual(result["description_placeholders"]["site_name"], "Remote")
        result = await self.flow.async_step_site({"enabled": True, "label": "Home"})
        self.assertEqual(result["data"]["device_tracker"], "person.test")
        self.assertEqual(
            [loc["distance"] for loc in result["data"]["configured_locations"]],
            [0, 0.0],
        )
        self.assertEqual(
            [loc["site_id"] for loc in result["data"]["configured_locations"]],
            [100, 200],
        )

    async def test_disabled_sites_are_excluded(self):
        await self.flow.async_step_sites({"device_tracker": "person.test"})
        await self.flow.async_step_site({"enabled": False, "label": "HQ"})
        result = await self.flow.async_step_site({"enabled": True, "label": "Home"})
        self.assertEqual(
            [loc["site_id"] for loc in result["data"]["configured_locations"]], [200]
        )

    async def test_all_disabled_preserves_answers_and_allows_correction(self):
        await self.flow.async_step_sites({"device_tracker": "person.test"})
        await self.flow.async_step_site(
            {"enabled": False, "label": "Edited HQ", "distance": 75}
        )
        result = await self.flow.async_step_site(
            {"enabled": False, "label": "Edited Home"}
        )
        self.assertEqual(result["errors"], {"base": "site_selection_invalid"})
        self.assertEqual(result["step_id"], "site")
        fields = {key.schema: key for key in result["data_schema"].schema}
        self.assertFalse(fields["enabled"].default())
        self.assertEqual(fields["label"].description["suggested_value"], "Edited HQ")
        self.assertEqual(fields["distance"].description["suggested_value"], 75)
        await self.flow.async_step_site(
            {"enabled": True, "label": "Edited HQ", "distance": 75}
        )
        result = await self.flow.async_step_site(
            {"enabled": False, "label": "Edited Home"}
        )
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(
            result["data"]["configured_locations"][0]["label"], "Edited HQ"
        )

    async def test_no_discovered_sites_cannot_create_empty_entry(self):
        self.flow.sites = {}
        result = await self.flow.async_step_sites({"device_tracker": "person.test"})
        self.assertEqual(result["step_id"], "sites")
        self.assertEqual(result["errors"], {"base": "no_sites_available"})

    async def test_reconfigure_preserves_missing_site_and_saved_defaults_until_finish(
        self,
    ):
        entry = SimpleNamespace(
            entry_id="entry-1",
            data={
                "access_token": "old-token",
                "device_tracker": "person.saved",
                "configured_locations": [
                    {
                        "site_id": 999,
                        "label": "Absent site",
                        "enabled": True,
                        "site_type": "office",
                        "distance": 85,
                    }
                ],
            },
        )
        entries = SimpleNamespace(
            async_get_entry=lambda _: entry,
            async_update_entry=Mock(),
            async_reload=AsyncMock(),
        )
        self.flow.hass.config_entries = entries
        self.flow.context = {"source": "reconfigure", "entry_id": "entry-1"}
        self.flow.token = None
        first = await self.flow.async_step_sites({"device_tracker": "person.saved"})
        self.assertEqual(first["description_placeholders"]["site_name"], "Absent site")
        self.assertIn(
            "not rediscovered", first["description_placeholders"]["site_status"]
        )
        fields = {key.schema: key for key in first["data_schema"].schema}
        self.assertEqual(fields["distance"].description["suggested_value"], 85)
        await self.flow.async_step_site(
            {"enabled": True, "label": "Absent renamed", "distance": 85}
        )
        await self.flow.async_step_site({"enabled": False, "label": "HQ"})
        entries.async_update_entry.assert_not_called()
        result = await self.flow.async_step_site({"enabled": False, "label": "Remote"})
        self.assertEqual(result["reason"], "reconfigure_successful")
        saved = entries.async_update_entry.call_args.kwargs["data"]
        self.assertEqual(saved["access_token"], "old-token")
        self.assertEqual(saved["device_tracker"], "person.saved")
        self.assertEqual(saved["configured_locations"][0]["site_id"], 999)
        self.assertEqual(saved["configured_locations"][0]["label"], "Absent renamed")
        entries.async_reload.assert_awaited_once_with("entry-1")

    async def test_omitted_distance_uses_backend_radius(self):
        await self.flow.async_step_sites({"device_tracker": "person.test"})
        await self.flow.async_step_site({"enabled": True, "label": "Office"})
        result = await self.flow.async_step_site({"enabled": False, "label": "Home"})
        self.assertEqual(
            result["data"]["configured_locations"][0]["distance"],
            self.flow._suggested_site_distance(self.flow._site_records[0]),
        )


if __name__ == "__main__":
    unittest.main()
