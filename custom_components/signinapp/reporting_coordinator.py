"""Shared bounded history polling and minute-by-minute reporting projections."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SignInAppAuthError, SignInAppHistoryPermissionError
from .quotas import ReportingOptions
from .reporting import build_report, history_window

_LOGGER = logging.getLogger(__name__)


class ReportingCoordinator(DataUpdateCoordinator):
    """One cache per companion account, shared by every reporting entity."""

    def __init__(self, hass, entry, api, status_coordinator, options=None):
        super().__init__(
            hass,
            _LOGGER,
            name="signinapp_reporting",
            config_entry=entry,
            update_interval=timedelta(minutes=1),
        )
        self.entry = entry
        self.api = api
        self.status_coordinator = status_coordinator
        self.options = (
            options
            if options is not None
            else ReportingOptions.from_mapping(dict(entry.options))
        )
        self._rows = None
        self._window = None
        self._fetched_at = None
        self._status_key = None
        self.error_reason = None

    async def _async_update_data(self):
        now = dt_util.utcnow()
        status = self.status_coordinator.data
        if not self.status_coordinator.last_update_success or not status:
            self.error_reason = "current_status_unavailable"
            raise UpdateFailed("Current attendance is unavailable.")
        visitor = status.get("returningVisitor") or {}
        if visitor.get("canViewSignInHistory") is False:
            self.error_reason = "history_permission_denied"
            raise UpdateFailed("This companion account cannot view attendance history.")
        window = history_window(now, self.hass.config.time_zone, self.options)
        status_key = (
            visitor.get("status"),
            visitor.get("lastIn"),
            visitor.get("lastOut"),
        )
        refresh = (
            self._rows is None
            or window != self._window
            or status_key != self._status_key
            or now - self._fetched_at >= timedelta(minutes=5)
        )
        try:
            if refresh:
                start, finish = window
                rows = []
                while start < finish:
                    end = min(start + timedelta(days=45), finish)
                    rows.extend(await self.api.get_history(start, end))
                    if len(rows) > 10000:
                        raise ValueError("History window contains too many sessions.")
                    start = end
                self._rows, self._window, self._fetched_at = rows, window, now
                self._status_key = status_key
            report = await self.hass.async_add_executor_job(
                build_report,
                self._rows,
                status,
                now,
                self.hass.config.time_zone,
                self.options,
            )
        except SignInAppAuthError as err:
            self.error_reason = "authentication_failed"
            self.entry.async_start_reauth(self.hass)
            raise UpdateFailed(
                "Reconnect this companion account to retrieve history."
            ) from err
        except SignInAppHistoryPermissionError as err:
            self.error_reason = "history_permission_denied"
            raise UpdateFailed(
                "History permission was denied; current attendance remains separate."
            ) from err
        except Exception as err:
            self.error_reason = "history_unavailable"
            # Do not retain a partial failed fetch, or project malformed history as zeros.
            self._rows = None
            raise UpdateFailed("Attendance history could not be calculated.") from err
        self.error_reason = None
        report["history_fetched_at"] = self._fetched_at.isoformat()
        report["quota_options"] = {
            "hours": self.options.quota_hours,
            "unit": self.options.quota_unit,
            "length": self.options.quota_length,
            "anchor": self.options.quota_anchor.isoformat(),
            "rollups": self.options.quota_rollups,
            "basis": self.options.quota_basis,
            "holiday_adjustment": self.options.holiday_adjustment,
            "country": self.options.country,
            "subdivision": self.options.subdivision,
        }
        return report

    def invalidate_history(self):
        """Used after an explicit refresh or an attendance mutation."""
        self._rows = None
