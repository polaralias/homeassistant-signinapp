"""Regression tests for Sign In App pure logic helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


LOGIC_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "signinapp"
    / "logic.py"
)

SPEC = importlib.util.spec_from_file_location("signinapp_logic", LOGIC_PATH)
logic = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(logic)


class NormalizeCompanionCodeTests(unittest.TestCase):
    def test_normalizes_hyphenated_code(self):
        self.assertEqual(logic.normalize_companion_code("dxpk-2qr2-bb8n"), "DXPK2QR2BB8N")


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
            status_data={"returningVisitor": {"status": "signed_in"}},
            current_session=current_session,
        )

        self.assertEqual(result["site_id"], 200)
        self.assertEqual(result["site_type"], logic.SITE_TYPE_REMOTE)
        self.assertTrue(result["use_cached_location"])

    def test_uses_api_current_site_id_when_available(self):
        result = logic.resolve_sign_out_context(
            self.config,
            explicit_site_type=None,
            status_data={"currentSiteId": 100, "returningVisitor": {"status": "signed_in"}},
            current_session=None,
        )

        self.assertEqual(result["site_id"], 100)
        self.assertEqual(result["site_type"], logic.SITE_TYPE_OFFICE)
        self.assertFalse(result["use_cached_location"])


class ResolveSensorStateTests(unittest.TestCase):
    def setUp(self):
        self.config = {"office_site_id": 100, "remote_site_id": 200}

    def test_uses_cached_current_session_for_signed_in_state(self):
        current_session = logic.build_session_context(
            100,
            logic.SITE_TYPE_OFFICE,
            {"lat": 51.5, "lng": -0.1, "accuracy": 20.0},
        )

        state = logic.resolve_sensor_state(
            {"returningVisitor": {"status": "signed_in"}},
            self.config,
            current_session=current_session,
            last_session=None,
        )

        self.assertEqual(state, "signed_in_office")

    def test_uses_last_session_for_signed_out_state(self):
        last_session = logic.build_session_context(
            200,
            logic.SITE_TYPE_REMOTE,
            {"lat": 0.0, "lng": 0.0, "accuracy": 0.0},
        )

        state = logic.resolve_sensor_state(
            {"returningVisitor": {"status": "signed_out"}},
            self.config,
            current_session=None,
            last_session=last_session,
        )

        self.assertEqual(state, "signed_out_remote")


if __name__ == "__main__":
    unittest.main()
