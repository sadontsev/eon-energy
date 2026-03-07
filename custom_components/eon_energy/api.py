"""E.ON Energy API client — Auth0 authentication + consumption REST API."""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any

import aiohttp

from .const import (
    API_BASE,
    API_CLIENT_ID,
    API_CLIENT_SECRET,
    AUTH0_AUDIENCE,
    AUTH0_CLIENT_ID,
    AUTH0_DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

TOKEN_EXPIRY_BUFFER_SECONDS = 300  # refresh 5 min before expiry


class EonEnergyAuthError(Exception):
    """Raised when authentication fails (triggers HA re-auth flow)."""


class EonEnergyApiError(Exception):
    """Raised for non-auth API errors."""


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode the JWT payload without verifying the signature."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1]
        # Pad to a multiple of 4
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:  # pylint: disable=broad-except
        return {}


class EonEnergyApi:
    """Client for the E.ON Energy API."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry: float = 0.0
        self._account_number: str | None = None
        self._token_update_callback: Any = None

    def restore_tokens(
        self,
        access_token: str,
        refresh_token: str,
        token_expiry: float,
        account_number: str,
    ) -> None:
        """Restore tokens from config entry (avoids login on startup)."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expiry = token_expiry
        self._account_number = account_number

    def set_token_update_callback(self, callback: Any) -> None:
        """Register callback invoked whenever tokens are refreshed."""
        self._token_update_callback = callback

    @property
    def account_number(self) -> str | None:
        return self._account_number

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def async_close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def async_login(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate via Auth0 ROPC grant.

        Returns token dict with access_token, refresh_token, expires_in.
        Raises EonEnergyAuthError on 401/403.
        Raises EonEnergyApiError on other failures.
        """
        url = f"https://{AUTH0_DOMAIN}/oauth/token"
        payload = {
            "grant_type": "password",
            "username": email,
            "password": password,
            "client_id": AUTH0_CLIENT_ID,
            "scope": "openid profile email offline_access",
            "audience": AUTH0_AUDIENCE,
        }
        session = self._get_session()
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status in (401, 403):
                    body = await resp.text()
                    _LOGGER.debug("Auth0 rejected credentials: %s %s", resp.status, body)
                    raise EonEnergyAuthError(
                        f"Auth0 rejected credentials (HTTP {resp.status})"
                    )
                if resp.status != 200:
                    body = await resp.text()
                    raise EonEnergyApiError(
                        f"Auth0 token request failed: HTTP {resp.status} — {body}"
                    )
                data = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EonEnergyApiError(f"Network error during login: {err}") from err

        self._store_tokens(data)
        return data

    async def async_refresh_token(self) -> dict[str, Any]:
        """Refresh the access token using the stored refresh token.

        Raises EonEnergyAuthError if the refresh token is invalid/expired.
        """
        if not self._refresh_token:
            raise EonEnergyAuthError("No refresh token available")

        url = f"https://{AUTH0_DOMAIN}/oauth/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": AUTH0_CLIENT_ID,
            "refresh_token": self._refresh_token,
        }
        session = self._get_session()
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status in (401, 403):
                    body = await resp.text()
                    _LOGGER.debug("Refresh token rejected: %s %s", resp.status, body)
                    raise EonEnergyAuthError("Refresh token expired or revoked")
                if resp.status != 200:
                    body = await resp.text()
                    raise EonEnergyApiError(
                        f"Token refresh failed: HTTP {resp.status} — {body}"
                    )
                data = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EonEnergyApiError(f"Network error during token refresh: {err}") from err

        self._store_tokens(data)
        return data

    def _store_tokens(self, data: dict[str, Any]) -> None:
        """Store tokens from an Auth0 response dict."""
        self._access_token = data.get("access_token")
        # Auth0 may return a new refresh token (rotation) or omit it
        new_rt = data.get("refresh_token")
        if new_rt:
            self._refresh_token = new_rt
        expires_in = data.get("expires_in", 36000)
        self._token_expiry = time.monotonic() + float(expires_in)

        # Extract account number from JWT payload
        if self._access_token:
            payload = _decode_jwt_payload(self._access_token)
            for key in ("account_number", "accountNumber", "accountId", "customerId"):
                val = payload.get(key)
                if val:
                    self._account_number = str(val)
                    break
            if not self._account_number:
                # Look in nested "https://eon.com/..." namespace claims
                for k, v in payload.items():
                    if isinstance(v, dict):
                        for inner_key in ("account_number", "accountNumber"):
                            if inner_key in v:
                                self._account_number = str(v[inner_key])
                                break
                    if self._account_number:
                        break
            _LOGGER.debug(
                "Tokens stored; account_number=%s expiry_in=%.0fs",
                self._account_number,
                float(data.get("expires_in", 0)),
            )

        if self._token_update_callback:
            self._token_update_callback(
                self._access_token,
                self._refresh_token,
                self._token_expiry,
                self._account_number,
            )

    async def async_get_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        if not self._access_token:
            raise EonEnergyAuthError("Not authenticated — call async_login first")

        needs_refresh = time.monotonic() >= (self._token_expiry - TOKEN_EXPIRY_BUFFER_SECONDS)
        if needs_refresh:
            _LOGGER.debug("Access token near expiry, refreshing")
            await self.async_refresh_token()

        if not self._access_token:
            raise EonEnergyAuthError("No access token after refresh")
        return self._access_token

    # ------------------------------------------------------------------
    # Validation (used by config flow)
    # ------------------------------------------------------------------

    async def async_validate_credentials(self, email: str, password: str) -> str:
        """Login and return account_number, or raise on failure."""
        await self.async_login(email, password)
        if not self._account_number:
            _LOGGER.warning(
                "Login succeeded but account_number not found in JWT — "
                "using email as fallback unique_id"
            )
            self._account_number = email
        return self._account_number

    # ------------------------------------------------------------------
    # Data API
    # ------------------------------------------------------------------

    def _api_headers(self, token: str) -> dict[str, str]:
        headers: dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "client_id": API_CLIENT_ID,
            "client_secret": API_CLIENT_SECRET,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._account_number:
            headers["account_number"] = self._account_number
        return headers

    async def async_get_consumption(self) -> dict[str, Any]:
        """GET /accounts/meters/consumption."""
        token = await self.async_get_token()
        url = f"{API_BASE}/accounts/meters/consumption"
        session = self._get_session()
        try:
            async with session.get(
                url,
                headers=self._api_headers(token),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status in (401, 403):
                    raise EonEnergyAuthError(
                        f"Consumption API auth failed: HTTP {resp.status}"
                    )
                if resp.status != 200:
                    body = await resp.text()
                    raise EonEnergyApiError(
                        f"Consumption API error: HTTP {resp.status} — {body}"
                    )
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EonEnergyApiError(f"Network error fetching consumption: {err}") from err
