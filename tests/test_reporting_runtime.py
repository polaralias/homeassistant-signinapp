"""Transport, caching, permission isolation and reporting options tests."""

from datetime import date
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

from homeassistant import loader
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.signinapp.api import (
    SignInAppApi,
    SignInAppAuthError,
    SignInAppError,
    SignInAppHistoryPermissionError,
)
from custom_components.signinapp.config_flow import SignInAppReportingOptionsFlow
from custom_components.signinapp.reporting_coordinator import ReportingCoordinator
from custom_components.signinapp.reporting_sensor import (
    ReportingSensor,
    async_setup_reporting_sensors,
)
from tests.test_reliability_regressions import Session
from tests.test_reporting import session, clock


class HistoryTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_history_list_and_date_parameters(self):
        transport = Session([{"id": 1}])
        api = SignInAppApi(transport)
        api.set_token("synthetic-token")
        self.assertEqual(
            await api.get_history(date(2026, 11, 1), date(2026, 11, 5)), [{"id": 1}]
        )
        self.assertTrue(transport.calls[0][0].endswith("/history"))
        self.assertEqual(
            transport.calls[0][1]["params"],
            {"dateFrom": "2026-11-01", "dateTo": "2026-11-05"},
        )

    async def test_history_permission_and_credentials_are_different(self):
        for code, error in [
            (403, SignInAppHistoryPermissionError),
            (401, SignInAppAuthError),
        ]:
            with self.assertRaises(error):
                await SignInAppApi(Session({}, code)).get_history(
                    date(2026, 11, 1), date(2026, 11, 5)
                )

    async def test_shape_and_boundaries(self):
        for response in [{}, ["invalid"], [None]]:
            with self.assertRaises(SignInAppError):
                await SignInAppApi(Session(response)).get_history(
                    date(2026, 11, 1), date(2026, 11, 5)
                )
        for start, end in [
            (date(2026, 11, 1), date(2026, 11, 1)),
            (date(2026, 1, 1), date(2026, 12, 1)),
        ]:
            with self.assertRaises(ValueError):
                await SignInAppApi(Session([])).get_history(start, end)


class ReportingRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.tmp.name)
        loader.async_setup(self.hass)
        await self.hass.config.async_set_time_zone("Europe/London")
        self.entry = SimpleNamespace(
            entry_id="report-test",
            unique_id="visitor-test",
            options={},
            pref_disable_polling=True,
            async_start_reauth=Mock(),
            async_on_unload=Mock(),
        )
        self.api = SimpleNamespace(
            get_history=AsyncMock(
                return_value=[session("2026-11-04T09:00:00Z", "2026-11-04T11:00:00Z")]
            )
        )
        self.status = SimpleNamespace(
            last_update_success=True,
            data={
                "returningVisitor": {
                    "status": "signed_out",
                    "canViewSignInHistory": True,
                }
            },
        )
        self.c = ReportingCoordinator(self.hass, self.entry, self.api, self.status)
        self.time = patch(
            "custom_components.signinapp.reporting_coordinator.dt_util.utcnow",
            return_value=clock("2026-11-04T12:00:00Z"),
        )
        self.time.start()

    async def asyncTearDown(self):
        self.time.stop()
        await self.hass.async_stop(force=True)
        self.tmp.cleanup()

    async def test_cache_and_explicit_invalidation(self):
        data = await self.c._async_update_data()
        self.assertEqual(data["periods"]["today"]["values"]["signed_in"], 2)
        await self.c._async_update_data()
        self.assertEqual(self.api.get_history.await_count, 1)
        self.c.invalidate_history()
        await self.c._async_update_data()
        self.assertEqual(self.api.get_history.await_count, 2)

    async def test_permission_does_not_start_reauth_or_fetch(self):
        self.status.data["returningVisitor"]["canViewSignInHistory"] = False
        with self.assertRaises(UpdateFailed):
            await self.c._async_update_data()
        self.api.get_history.assert_not_awaited()
        self.entry.async_start_reauth.assert_not_called()

    async def test_403_keeps_primary_status_intact(self):
        self.api.get_history.side_effect = SignInAppHistoryPermissionError()
        with self.assertRaises(UpdateFailed):
            await self.c._async_update_data()
        self.assertTrue(self.status.last_update_success)
        self.entry.async_start_reauth.assert_not_called()

    async def test_authentication_starts_existing_reauth(self):
        self.api.get_history.side_effect = SignInAppAuthError()
        with self.assertRaises(UpdateFailed):
            await self.c._async_update_data()
        self.entry.async_start_reauth.assert_called_once_with(self.hass)

    async def test_six_month_window_is_chunked(self):
        self.entry.options = {"quota_unit": "months", "quota_length": 6}
        self.c = ReportingCoordinator(self.hass, self.entry, self.api, self.status)
        await self.c._async_update_data()
        self.assertGreater(self.api.get_history.await_count, 1)
        for call in self.api.get_history.call_args_list:
            self.assertLessEqual((call.args[1] - call.args[0]).days, 45)

    async def test_malformed_history_unavailable_not_zero(self):
        self.api.get_history.return_value = [{"id": 1}]
        with self.assertRaises(UpdateFailed):
            await self.c._async_update_data()
        self.assertIsNone(self.c._rows)

    async def test_new_activity_discovery_and_unique_ids(self):
        self.c.async_set_updated_data(await self.c._async_update_data())
        added = []
        await async_setup_reporting_sensors(
            self.hass, self.entry, self.c, lambda es: added.extend(es)
        )
        identities = [e.unique_id for e in added]
        self.assertEqual(len(identities), len(set(identities)))
        weekly = next(
            e for e in added if e.period == "week" and e.metric == "signed_in"
        )
        self.assertEqual(weekly.native_value, 2)
        activity = next(e for e in added if e.activity == "1" and e.period == "today")
        old = activity.unique_id
        data = self.c.data.copy()
        data["activities"] = {
            "1": {"name": "Renamed", "is_working": True},
            "2": {"name": "New", "is_working": False},
        }
        old_count = len(added)
        self.c.async_set_updated_data(data)
        self.assertEqual(len(added), old_count + 52)
        self.assertEqual(activity.unique_id, old)
        self.assertIn("Renamed", activity.name)

    async def test_activity_shares_and_working_quota_contributions(self):
        from custom_components.signinapp.quotas import ReportingOptions
        from tests.test_reporting import change

        self.c.options = ReportingOptions(quota_rollups=True)
        self.api.get_history.return_value = [
            session(
                "2026-11-04T09:00:00Z",
                "2026-11-04T11:00:00Z",
                changes=[
                    change("2026-11-04T09:00:00Z", 1, True),
                    change("2026-11-04T10:30:00Z", 2, False),
                ],
            )
        ]
        self.c.async_set_updated_data(await self.c._async_update_data())

        def sensor(metric, activity):
            return ReportingSensor(self.c, self.entry, "today", metric, activity)

        self.assertEqual(sensor("activity_percentage", "1").native_value, 75)
        self.assertEqual(sensor("activity_working_percentage", "1").native_value, 100)
        self.assertEqual(sensor("activity_quota_percentage", "1").native_value, 20)
        self.assertEqual(sensor("activity_quota_percentage", "2").native_value, 0)
        self.assertIsNone(sensor("activity_working_percentage", "2").native_value)
        self.assertFalse(
            sensor("activity_percentage", "1").entity_registry_enabled_default
        )

    async def test_options_flow_labels_and_calendar(self):
        flow = SignInAppReportingOptionsFlow(self.entry)
        flow.hass = self.hass
        init = await flow.async_step_init()
        self.assertEqual(init["step_id"], "init")
        value = {
            "quota_hours": 37.5,
            "quota_unit": "weeks",
            "quota_length": 1,
            "quota_anchor": "2026-01-05",
            "workdays": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "quota_basis": "working",
            "quota_rollups": True,
            "holiday_adjustment": True,
        }
        country = await flow.async_step_init(value)
        self.assertEqual(country["step_id"], "holidays")
        region = await flow.async_step_holidays({"holiday_country": "GB"})
        self.assertEqual(region["step_id"], "calendar")
        done = await flow.async_step_calendar(
            {"holiday_subdivision": "WLS", "custom_holidays": "2026-12-24"}
        )
        self.assertEqual(done["type"], "create_entry")
        self.assertEqual(done["data"]["holiday_subdivision"], "WLS")

    async def test_options_invalid_dates_are_rejected(self):
        flow = SignInAppReportingOptionsFlow(self.entry)
        flow.hass = self.hass
        form = await flow.async_step_init(
            {"quota_unit": "months", "quota_anchor": "2026-01-03"}
        )
        self.assertEqual(form["errors"]["base"], "invalid_reporting_options")


if __name__ == "__main__":
    unittest.main()
