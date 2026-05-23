"""Fixture-backed regression tests for Sign In App pure logic helpers."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "config_v2"
logic = importlib.import_module("custom_components.signinapp.logic")


def load_fixture(name: str) -> dict:
    """Load a sanitized config-v2 fixture."""
    with (FIXTURES_DIR / name).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


class NormalizeCompanionCodeTests(unittest.TestCase):
    def test_normalizes_hyphenated_code(self):
        self.assertEqual(logic.normalize_companion_code("dxpk-2qr2-bb8n"), "DXPK2QR2BB8N")


class ResolveCurrentSiteIdTests(unittest.TestCase):
    def test_uses_current_visit_site_id_when_present(self):
        status_data = load_fixture("signed_in_current_visit_authoritative.json")

        self.assertEqual(logic.resolve_current_site_id(status_data), 100)


class ConfiguredLocationNormalizationTests(unittest.TestCase):
    def test_iter_configured_locations_infers_coordinate_behavior_from_site_type(self):
        locations = logic.iter_configured_locations(
            {
                "configured_locations": [
                    {"site_id": 100, "label": "HQ", "enabled": True, "site_type": "office", "distance": 60},
                    {"site_id": 200, "label": "WFH", "enabled": True, "site_type": "remote", "distance": 0.0},
                ]
            }
        )

        self.assertEqual(locations[0]["coordinate_behavior"], "device_tracker")
        self.assertEqual(locations[1]["coordinate_behavior"], "remote_zero")


class ResolveSignOutContextTests(unittest.TestCase):
    def setUp(self):
        self.config = {"office_site_id": 100, "remote_site_id": 200}

    def test_prefers_cached_location_for_matching_explicit_site(self):
        current_session = logic.build_session_context(
            100,
            logic.SITE_TYPE_OFFICE,
            {"lat": 51.5, "lng": -0.1, "accuracy": 20.0},
        )

        result = logic.resolve_sign_out_context(
            self.config,
            logic.SITE_TYPE_OFFICE,
            status_data=None,
            current_session=current_session,
        )

        self.assertEqual(result["site_id"], 100)
        self.assertTrue(result["use_cached_location"])

    def test_uses_cached_session_when_api_has_no_current_site(self):
        current_session = logic.build_session_context(
            200,
            logic.SITE_TYPE_REMOTE,
            {"lat": 0.0, "lng": 0.0, "accuracy": 0.0},
        )

        result = logic.resolve_sign_out_context(
            self.config,
            explicit_site_type=None,
            status_data=load_fixture("signed_in_missing_current_site.json"),
            current_session=current_session,
        )

        self.assertEqual(result["site_id"], 200)
        self.assertEqual(result["site_type"], logic.SITE_TYPE_REMOTE)
        self.assertTrue(result["use_cached_location"])

    def test_uses_authoritative_backend_site_when_available(self):
        result = logic.resolve_sign_out_context(
            self.config,
            explicit_site_type=None,
            status_data=load_fixture("signed_in_current_visit_authoritative.json"),
            current_session=None,
        )

        self.assertEqual(result["site_id"], 100)
        self.assertEqual(result["site_type"], logic.SITE_TYPE_OFFICE)
        self.assertFalse(result["use_cached_location"])

    def test_backend_site_beats_conflicting_cached_session(self):
        current_session = logic.build_session_context(
            200,
            logic.SITE_TYPE_REMOTE,
            {"lat": 0.0, "lng": 0.0, "accuracy": 0.0},
        )

        result = logic.resolve_sign_out_context(
            self.config,
            explicit_site_type=None,
            status_data=load_fixture("signed_in_backend_cache_conflict.json"),
            current_session=current_session,
        )

        self.assertEqual(result["site_id"], 100)
        self.assertEqual(result["site_type"], logic.SITE_TYPE_OFFICE)
        self.assertFalse(result["use_cached_location"])

    def test_explicit_remote_hint_does_not_fall_back_to_conflicting_office_cache(self):
        current_session = logic.build_session_context(
            100,
            logic.SITE_TYPE_OFFICE,
            {"lat": 51.5, "lng": -0.1, "accuracy": 20.0},
        )

        result = logic.resolve_sign_out_context(
            self.config,
            explicit_site_type=logic.SITE_TYPE_REMOTE,
            status_data=None,
            current_session=current_session,
        )

        self.assertEqual(result["site_id"], 200)
        self.assertEqual(result["site_type"], logic.SITE_TYPE_REMOTE)
        self.assertFalse(result["use_cached_location"])

    def test_explicit_office_hint_does_not_fall_back_to_conflicting_remote_cache(self):
        current_session = logic.build_session_context(
            200,
            logic.SITE_TYPE_REMOTE,
            {"lat": 0.0, "lng": 0.0, "accuracy": 0.0},
        )

        result = logic.resolve_sign_out_context(
            self.config,
            explicit_site_type=logic.SITE_TYPE_OFFICE,
            status_data=None,
            current_session=current_session,
        )

        self.assertEqual(result["site_id"], 100)
        self.assertEqual(result["site_type"], logic.SITE_TYPE_OFFICE)
        self.assertFalse(result["use_cached_location"])

    def test_explicit_office_hint_is_ambiguous_when_multiple_office_targets_exist(self):
        config = {
            "configured_locations": [
                {
                    "site_id": 100,
                    "label": "HQ",
                    "enabled": True,
                    "site_type": "office",
                    "coordinate_behavior": "device_tracker",
                    "distance": 50,
                },
                {
                    "site_id": 300,
                    "label": "Site B",
                    "enabled": True,
                    "site_type": "office",
                    "coordinate_behavior": "device_tracker",
                    "distance": 90,
                },
            ]
        }

        result = logic.resolve_sign_out_context(
            config,
            explicit_site_type=logic.SITE_TYPE_OFFICE,
            status_data=None,
            current_session=None,
        )

        self.assertIsNone(result)

    def test_explicit_office_hint_uses_matching_cached_session_to_disambiguate(self):
        config = {
            "configured_locations": [
                {
                    "site_id": 100,
                    "label": "HQ",
                    "enabled": True,
                    "site_type": "office",
                    "coordinate_behavior": "device_tracker",
                    "distance": 50,
                },
                {
                    "site_id": 300,
                    "label": "Site B",
                    "enabled": True,
                    "site_type": "office",
                    "coordinate_behavior": "device_tracker",
                    "distance": 90,
                },
            ]
        }
        current_session = logic.build_session_context(
            300,
            logic.SITE_TYPE_OFFICE,
            {"lat": 51.5, "lng": -0.1, "accuracy": 90.0},
        )

        result = logic.resolve_sign_out_context(
            config,
            explicit_site_type=logic.SITE_TYPE_OFFICE,
            status_data=None,
            current_session=current_session,
        )

        self.assertEqual(result["site_id"], 300)
        self.assertTrue(result["use_cached_location"])


class ResolveSensorStateTests(unittest.TestCase):
    def setUp(self):
        self.config = {"office_site_id": 100, "remote_site_id": 200}

    def test_uses_current_visit_for_signed_in_state(self):
        state = logic.resolve_sensor_state(
            load_fixture("signed_in_current_visit_authoritative.json"),
            self.config,
            current_session=None,
            last_session=None,
        )

        self.assertEqual(state, "signed_in")

    def test_uses_cached_current_session_for_signed_in_state_when_backend_is_ambiguous(self):
        current_session = logic.build_session_context(
            100,
            logic.SITE_TYPE_OFFICE,
            {"lat": 51.5, "lng": -0.1, "accuracy": 20.0},
        )

        state = logic.resolve_sensor_state(
            load_fixture("signed_in_missing_current_site.json"),
            self.config,
            current_session=current_session,
            last_session=None,
        )

        self.assertEqual(state, "signed_in")

    def test_returns_unknown_when_signed_in_backend_has_no_current_site_and_cache_cannot_recover(self):
        state = logic.resolve_sensor_state(
            load_fixture("signed_in_missing_current_site.json"),
            self.config,
            current_session=None,
            last_session=None,
        )

        self.assertEqual(state, "unknown")

    def test_returns_unknown_when_backend_site_is_not_configured(self):
        state = logic.resolve_sensor_state(
            load_fixture("signed_in_unconfigured_site.json"),
            self.config,
            current_session=None,
            last_session=None,
        )

        self.assertEqual(state, "unknown")

    def test_uses_last_session_for_signed_out_state(self):
        last_session = logic.build_session_context(
            200,
            logic.SITE_TYPE_REMOTE,
            {"lat": 0.0, "lng": 0.0, "accuracy": 0.0},
        )

        state = logic.resolve_sensor_state(
            load_fixture("signed_out_last_active_context.json"),
            self.config,
            current_session=None,
            last_session=last_session,
        )

        self.assertEqual(state, "signed_out")

    def test_returns_unknown_when_backend_payload_is_unavailable(self):
        state = logic.resolve_sensor_state(
            None,
            self.config,
            current_session=None,
            last_session=None,
        )

        self.assertEqual(state, "unknown")

    def test_returns_unknown_when_backend_contract_omits_status(self):
        state = logic.resolve_sensor_state(
            load_fixture("backend_contract_missing_status.json"),
            self.config,
            current_session=None,
            last_session=None,
        )

        self.assertEqual(state, "unknown")


class ResolveSensorSiteIdTests(unittest.TestCase):
    def test_uses_authoritative_backend_site_for_attributes(self):
        site_id = logic.resolve_sensor_site_id(
            load_fixture("signed_in_current_visit_authoritative.json"),
            current_session=None,
            last_session=None,
        )

        self.assertEqual(site_id, 100)


class ResolveSensorAttributesTests(unittest.TestCase):
    def setUp(self):
        self.config = {"office_site_id": 100, "remote_site_id": 200}

    def test_projects_canonical_signed_in_attributes(self):
        attrs = logic.resolve_sensor_attributes(
            load_fixture("signed_in_current_visit_authoritative.json"),
            self.config,
            current_session=None,
            last_session=None,
        )

        self.assertEqual(
            attrs,
            {
                "status_class": "signed_in",
                "active_work_location_id": 100,
                "active_work_location_label": "HQ",
                "last_active_work_location_id": 100,
                "last_active_work_location_label": "HQ",
                "status_reason": None,
            },
        )

    def test_projects_canonical_signed_out_attributes(self):
        last_session = logic.build_session_context(
            200,
            logic.SITE_TYPE_REMOTE,
            {"lat": 0.0, "lng": 0.0, "accuracy": 0.0},
        )

        attrs = logic.resolve_sensor_attributes(
            load_fixture("signed_out_last_active_context.json"),
            self.config,
            current_session=None,
            last_session=last_session,
        )

        self.assertEqual(
            attrs,
            {
                "status_class": "signed_out",
                "active_work_location_id": None,
                "active_work_location_label": None,
                "last_active_work_location_id": 200,
                "last_active_work_location_label": "Remote",
                "status_reason": None,
            },
        )

    def test_projects_unknown_reason_when_backend_payload_is_unavailable(self):
        attrs = logic.resolve_sensor_attributes(
            None,
            self.config,
            current_session=None,
            last_session=None,
        )

        self.assertEqual(
            attrs,
            {
                "status_class": "unknown",
                "active_work_location_id": None,
                "active_work_location_label": None,
                "last_active_work_location_id": None,
                "last_active_work_location_label": None,
                "status_reason": "backend_unavailable",
            },
        )

    def test_projects_unknown_reason_when_signed_in_backend_is_ambiguous(self):
        attrs = logic.resolve_sensor_attributes(
            load_fixture("signed_in_missing_current_site.json"),
            self.config,
            current_session=None,
            last_session=None,
        )

        self.assertEqual(
            attrs,
            {
                "status_class": "unknown",
                "active_work_location_id": None,
                "active_work_location_label": None,
                "last_active_work_location_id": None,
                "last_active_work_location_label": None,
                "status_reason": "routing_ambiguous",
            },
        )

    def test_projects_unknown_reason_when_backend_site_is_not_configured(self):
        attrs = logic.resolve_sensor_attributes(
            load_fixture("signed_in_unconfigured_site.json"),
            self.config,
            current_session=None,
            last_session=None,
        )

        self.assertEqual(
            attrs,
            {
                "status_class": "unknown",
                "active_work_location_id": None,
                "active_work_location_label": None,
                "last_active_work_location_id": None,
                "last_active_work_location_label": None,
                "status_reason": "target_not_configured",
            },
        )

    def test_projects_unknown_reason_when_backend_contract_omits_status(self):
        attrs = logic.resolve_sensor_attributes(
            load_fixture("backend_contract_missing_status.json"),
            self.config,
            current_session=None,
            last_session=None,
        )

        self.assertEqual(
            attrs,
            {
                "status_class": "unknown",
                "active_work_location_id": None,
                "active_work_location_label": None,
                "last_active_work_location_id": None,
                "last_active_work_location_label": None,
                "status_reason": "backend_contract_mismatch",
            },
        )


if __name__ == "__main__":
    unittest.main()
