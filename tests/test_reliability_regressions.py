"""Offline regressions for target boundaries, protocol failures and reauthentication."""
import io
import logging
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError

import custom_components.signinapp as integration
from custom_components.signinapp import config_flow, sensor
from custom_components.signinapp.api import SignInAppApi, SignInAppAuthError, SignInAppError
from custom_components.signinapp.logic import resolve_sensor_attributes


class Response:
    def __init__(self, data, status=200):
        self.data, self.status = data, status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def json(self):
        return self.data


class Session:
    def __init__(self, data, status=200):
        self.response = Response(data, status)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response

    get = post


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_auth_failures_are_classified_without_response_body(self):
        for status in (401, 403):
            with self.assertRaises(SignInAppAuthError):
                await SignInAppApi(Session({"private": "not for logs"}, status)).get_config()

    async def test_negative_success_flag_is_rejected_for_both_mutations(self):
        api = SignInAppApi(Session({"success": False, "message": "private backend details"}))
        for action in (api.sign_in, api.sign_out):
            with self.assertRaises(SignInAppError):
                await action(100, 0, 0, 0)

    async def test_unexpected_json_shape_is_rejected(self):
        with self.assertRaises(SignInAppError):
            await SignInAppApi(Session([])).get_config()

    async def test_debug_logs_never_contain_auth_or_personal_payload(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("custom_components.signinapp.api")
        old = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        session = Session({"success": True, "token": "synthetic-secret", "private": "synthetic-person"})
        try:
            api = SignInAppApi(session)
            api.set_token("old-secret")
            self.assertEqual(await api.connect("test-code"), "synthetic-secret")
            await api.get_config()
        finally:
            logger.removeHandler(handler)
            logger.setLevel(old)
        for value in ("synthetic-secret", "TESTCODE", "old-secret", "synthetic-person"):
            self.assertNotIn(value, stream.getvalue())
        self.assertNotIn("authorization", session.calls[0][1]["headers"])


def build_hass(*, enabled=True, cached=True, api=None):
    config = {"device_tracker": "person.test", "configured_locations": [
        {"site_id": 100, "label": "Office", "enabled": enabled, "site_type": "office",
         "coordinate_behavior": "device_tracker", "distance": 50}
    ]}
    cache = {"site_id": 100, "site_type": "office", "coordinate_behavior": "device_tracker",
             "location": {"lat": 51., "lng": 0., "accuracy": 50.}}
    entry = {"config": config, "api": api, "current_session": cache if cached else None,
             "last_session": None, "coordinator": None}
    hass = SimpleNamespace(data={"signinapp": {"test": entry}}, states=SimpleNamespace(
        get=lambda eid: SimpleNamespace(state="home", attributes={"latitude": 51., "longitude": 0.})
    ))
    return hass, entry


class ActionTests(unittest.IsolatedAsyncioTestCase):
    async def test_bad_explicit_target_never_falls_back_to_cached_site(self):
        api = SimpleNamespace(sign_out=AsyncMock())
        hass, entry = build_hass(api=api)
        with self.assertRaises(HomeAssistantError):
            await integration.get_handle_sign_out(hass)(SimpleNamespace(data={"site_id": 999}))
        api.sign_out.assert_not_awaited()
        self.assertEqual(entry["current_session"]["site_id"], 100)

    async def test_disabled_or_removed_cached_target_is_never_sent(self):
        for removed in (True, False):
            api = SimpleNamespace(sign_out=AsyncMock(), get_config=AsyncMock(return_value={
                "returningVisitor": {"status": "signed_in"}}))
            hass, entry = build_hass(enabled=False, api=api)
            if removed:
                entry["config"]["configured_locations"] = []
            with self.assertRaises(HomeAssistantError):
                await integration.get_handle_sign_out(hass)(SimpleNamespace(data={}))
            api.sign_out.assert_not_awaited()

    async def test_unconfirmed_mutation_does_not_commit_or_retry_mutation(self):
        api = SimpleNamespace(sign_in=AsyncMock(return_value={"success": True}),
                              get_config=AsyncMock(return_value={"returningVisitor": {"status": "signed_out"}}))
        hass, entry = build_hass(cached=False, api=api)
        with patch.object(integration.asyncio, "sleep", AsyncMock()):
            with self.assertRaises(HomeAssistantError):
                await integration.get_handle_sign_in(hass)(SimpleNamespace(data={"site_id": 100}))
        self.assertIsNone(entry["current_session"])
        self.assertIsNone(entry["last_session"])
        api.sign_in.assert_awaited_once()
        self.assertEqual(api.get_config.await_count, 3)

    async def test_eventually_confirmed_mutation_commits_once(self):
        api = SimpleNamespace(sign_in=AsyncMock(return_value={"success": True}), get_config=AsyncMock(side_effect=[
            {"returningVisitor": {"status": "signed_out"}},
            {"returningVisitor": {"status": "signed_in"}, "currentVisit": {"siteId": 100}},
        ]))
        hass, entry = build_hass(cached=False, api=api)
        with patch.object(integration.asyncio, "sleep", AsyncMock()):
            await integration.get_handle_sign_in(hass)(SimpleNamespace(data={"site_id": 100}))
        api.sign_in.assert_awaited_once()
        self.assertEqual(entry["current_session"]["site_id"], 100)

    async def test_auth_failure_starts_reauthentication_instead_of_mutating(self):
        api = SimpleNamespace(sign_out=AsyncMock(), get_config=AsyncMock(side_effect=SignInAppAuthError()))
        hass, entry = build_hass(api=api)
        entry["entry"] = SimpleNamespace(async_start_reauth=Mock())
        with self.assertRaises(HomeAssistantError):
            await integration.get_handle_sign_out(hass)(SimpleNamespace(data={}))
        entry["entry"].async_start_reauth.assert_called_once_with(hass)
        api.sign_out.assert_not_awaited()

    async def test_coordinator_auth_failure_uses_ha_reauthentication_exception(self):
        class Coordinator:
            def __init__(self, *args, **kwargs):
                self.update = kwargs["update_method"]

            async def async_config_entry_first_refresh(self):
                return await self.update()
        api = SimpleNamespace(get_config=AsyncMock(side_effect=SignInAppAuthError()))
        hass, _ = build_hass(api=api)
        with patch.object(sensor, "DataUpdateCoordinator", Coordinator):
            with self.assertRaises(ConfigEntryAuthFailed):
                await sensor.async_setup_entry(hass, SimpleNamespace(entry_id="test"), Mock())


class ReauthTests(unittest.IsolatedAsyncioTestCase):
    async def run_flow(self, visitor_id):
        entry = SimpleNamespace(entry_id="test", unique_id="visitor-1", title="Synthetic account", data={
            "access_token": "old-synthetic-token", "device_tracker": "person.test",
            "configured_locations": [{"site_id": 100, "label": "Keep this label"}],
        })
        flow = config_flow.SignInAppConfigFlow()
        flow.context = {"source": "reauth", "entry_id": "test"}
        flow.hass = SimpleNamespace(config=SimpleNamespace(time_zone="Europe/London"), config_entries=SimpleNamespace(
            flow=SimpleNamespace(async_progress_by_handler=lambda *args, **kwargs: []), async_get_entry=lambda eid: entry, async_get_known_entry=lambda eid: entry, async_update_entry=Mock(), async_reload=AsyncMock()))
        form = await flow.async_step_reauth(entry.data)
        self.assertEqual(form["step_id"], "reauth_confirm")
        with patch.object(config_flow, "SignInAppApi") as api_cls, patch.object(
            config_flow.aiohttp_client, "async_get_clientsession", return_value=object()
        ):
            api = api_cls.return_value
            api.connect = AsyncMock(return_value="new-synthetic-token")
            api.get_config = AsyncMock(return_value={"returningVisitor": {"id": visitor_id}})
            with patch("homeassistant.components.persistent_notification.async_dismiss"):
                result = await flow.async_step_reauth_confirm({"companion_code": "synthetic-code"})
        return flow, entry, result

    async def test_reauthentication_preserves_entry_identity_and_routing(self):
        flow, entry, result = await self.run_flow("visitor-1")
        self.assertEqual(result["reason"], "reauth_successful")
        flow.hass.config_entries.async_update_entry.assert_called_once_with(
            entry, data={**entry.data, "access_token": "new-synthetic-token"})
        flow.hass.config_entries.async_reload.assert_awaited_once_with(entry.entry_id)

    async def test_different_account_cannot_replace_existing_entry(self):
        flow, _, result = await self.run_flow("different-visitor")
        self.assertEqual(result["errors"], {"base": "wrong_account"})
        flow.hass.config_entries.async_update_entry.assert_not_called()
        flow.hass.config_entries.async_reload.assert_not_awaited()


class ProjectionTests(unittest.TestCase):
    def test_unknown_or_invalid_status_is_a_canonical_unknown(self):
        for status in ("unexpected_status", 123, None):
            attrs = resolve_sensor_attributes({"returningVisitor": {"status": status}}, {}, None, None)
            self.assertEqual(attrs["status_class"], "unknown")
            self.assertEqual(attrs["status_reason"], "backend_contract_mismatch")

    def test_disabled_cached_site_does_not_project_signed_in(self):
        _, entry = build_hass(enabled=False)
        attrs = resolve_sensor_attributes({"returningVisitor": {"status": "signed_in"}},
                                          entry["config"], entry["current_session"], None)
        self.assertEqual(attrs["status_class"], "unknown")
        self.assertEqual(attrs["status_reason"], "target_not_configured")
