"""Sign In App transport with explicit authentication and response boundaries."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL
from .logic import normalize_companion_code

_LOGGER = logging.getLogger(__name__)
HEADERS = {
    "accept": "application/json",
    "accept-language": "en-GB-oxendict,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://companion.signin.app",
    "referer": "https://companion.signin.app/",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
    "x-app-version": "Web companion app/3.18.2+302148",
}


class SignInAppError(Exception):
    """A safe-to-display protocol or attendance failure."""


class SignInAppAuthError(SignInAppError):
    """The backend rejected credentials; the config entry needs reauthentication."""


class SignInAppApi:
    """Transport client; never log credentials or personal response bodies."""

    def __init__(self, session: aiohttp.ClientSession, timezone: str = "Europe/London"):
        self._session = session
        self._timezone = timezone
        self._token: str | None = None

    def set_token(self, token: str):
        self._token = token

    def _get_headers(self) -> dict[str, str]:
        headers = dict(HEADERS, **{"x-timezone": self._timezone})
        if self._token:
            headers["authorization"] = f"Bearer {self._token}"
        return headers

    async def _request(self, method: str, endpoint: str, payload=None, *, authenticated=True) -> dict[str, Any]:
        headers = self._get_headers()
        if not authenticated:
            headers.pop("authorization", None)
        request = self._session.get if method == "GET" else self._session.post
        kwargs = {"headers": headers, "timeout": aiohttp.ClientTimeout(total=30)}
        if payload is not None:
            kwargs["json"] = payload
        async with request(f"{API_BASE_URL}/{endpoint}", **kwargs) as response:
            _LOGGER.debug("Sign In App %s %s returned HTTP %s", method, endpoint, response.status)
            if response.status in (401, 403):
                raise SignInAppAuthError("Sign In App authentication was rejected. Reconnect your account.")
            if response.status >= 400:
                raise SignInAppError(f"Sign In App returned HTTP {response.status}.")
            try:
                data = await response.json()
            except (ValueError, aiohttp.ContentTypeError) as err:
                raise SignInAppError("Sign In App returned an invalid JSON response.") from err
        if not isinstance(data, dict):
            raise SignInAppError("Sign In App returned an unexpected response format.")
        if data.get("success") is False:
            raise SignInAppError("Sign In App did not accept the request.")
        return data

    async def connect(self, code: str) -> str:
        normalized = normalize_companion_code(code)
        if not normalized:
            raise ValueError("Companion code is empty after normalization.")
        data = await self._request("POST", "connect", {"code": normalized}, authenticated=False)
        token = data.get("token")
        if data.get("success") is not True or not isinstance(token, str) or not token.strip():
            raise SignInAppAuthError("The companion code was not accepted.")
        return token

    @staticmethod
    def _attendance_payload(site_id, lat, lng, accuracy):
        return {
            "automated": False,
            "location": {"accuracy": accuracy, "lat": lat, "lng": lng},
            "siteId": site_id, "additional": [], "personalFields": {}, "notifyId": None, "messages": [],
        }

    async def sign_in(self, site_id: int, lat: float, lng: float, accuracy: float) -> dict[str, Any]:
        payload = self._attendance_payload(site_id, lat, lng, accuracy)
        payload["method"] = "sign-in"
        return await self._request("POST", "sign-in", payload)

    async def sign_out(self, site_id: int, lat: float, lng: float, accuracy: float) -> dict[str, Any]:
        return await self._request("POST", "sign-out", self._attendance_payload(site_id, lat, lng, accuracy))

    async def get_config(self) -> dict[str, Any]:
        return await self._request("GET", "config-v2")
