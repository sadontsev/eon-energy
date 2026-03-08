"""E.ON Energy API client."""

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
)

_LOGGER = logging.getLogger(__name__)

# Trigger re-auth 5 min before the token expires
TOKEN_EXPIRY_BUFFER_SECONDS = 300


class EonEnergyAuthError(Exception):
    """Raised when authentication fails (triggers HA re-auth flow)."""


class EonEnergyApiError(Exception):
    """Raised for non-auth API errors."""


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode a JWT payload without verifying the signature."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:  # pylint: disable=broad-except
        return {}


def _is_jwt(token: str) -> bool:
    """Return True if token is a plain JWT (3 dot-separated parts)."""
    return len(token.split(".")) == 3


def _extract_account_number(payload: dict[str, Any]) -> str | None:
    """Extract account number from a decoded JWT payload."""
    for key in ("accountNumber", "account_number", "accountId", "customerId"):
        val = payload.get(key)
        if val:
            return str(val)
    for _k, v in payload.items():
        if isinstance(v, dict):
            for inner in ("accountNumber", "account_number"):
                if inner in v:
                    return str(v[inner])
    return None


class EonEnergyApi:
    """Client for the E.ON Energy API."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._bearer_token: str | None = None   # id_token used as Bearer
        self._token_expiry: float = 0.0         # absolute Unix timestamp
        self._account_number: str | None = None

    def restore_tokens(
        self,
        bearer_token: str,
        token_expiry: float,
        account_number: str,
    ) -> None:
        """Restore tokens from a config entry on HA startup."""
        self._bearer_token = bearer_token
        self._token_expiry = token_expiry
        self._account_number = account_number

    @property
    def account_number(self) -> str | None:
        return self._account_number

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def async_close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def load_token_data(self, token_data: dict[str, Any]) -> str:
        """Load tokens from a parsed Auth0 token JSON object.

        Expects keys: id_token (JWT), expires (Unix timestamp seconds).
        Returns the account_number extracted from the id_token.
        Raises ValueError if the data is unusable.
        """
        id_token = token_data.get("id_token", "")
        if not id_token or not _is_jwt(id_token):
            raise ValueError("id_token missing or not a valid JWT")

        expires_at = float(token_data.get("expires", 0))
        if expires_at == 0:
            # Fall back to exp claim inside the JWT
            payload = _decode_jwt_payload(id_token)
            expires_at = float(payload.get("exp", 0))
        if expires_at == 0:
            raise ValueError("Cannot determine token expiry")

        payload = _decode_jwt_payload(id_token)
        _LOGGER.debug("id_token payload keys: %s", list(payload.keys()))

        self._bearer_token = id_token
        self._token_expiry = expires_at
        self._account_number = _extract_account_number(payload) or "eon_energy"
        return self._account_number

    async def async_validate_token_data(self, raw: str) -> str:
        """Parse raw input (JSON blob or bare id_token) and return account_number.

        Raises EonEnergyAuthError on invalid/expired token.
        """
        raw = raw.strip()

        # Accept either a full JSON blob or a bare id_token JWT
        if raw.startswith("{"):
            try:
                token_data = json.loads(raw)
            except json.JSONDecodeError as err:
                raise EonEnergyAuthError(f"Invalid JSON: {err}") from err
        elif _is_jwt(raw):
            # Bare id_token — synthesise a minimal token_data dict
            token_data = {"id_token": raw}
        else:
            raise EonEnergyAuthError(
                "Input is neither a valid JSON object nor a JWT"
            )

        try:
            account_number = self.load_token_data(token_data)
        except ValueError as err:
            raise EonEnergyAuthError(str(err)) from err

        # Reject tokens that are already expired
        if time.time() >= self._token_expiry:
            raise EonEnergyAuthError(
                "Token is already expired — log in again and copy fresh token data"
            )

        return account_number

    async def async_get_token(self) -> str:
        """Return the stored Bearer token, raising EonEnergyAuthError if expired."""
        if not self._bearer_token:
            raise EonEnergyAuthError("Not authenticated — please re-authenticate")
        if time.time() >= (self._token_expiry - TOKEN_EXPIRY_BUFFER_SECONDS):
            raise EonEnergyAuthError(
                "Token expired — please re-authenticate via HA"
            )
        return self._bearer_token

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
                body = await resp.text()
                _LOGGER.debug("Consumption API: HTTP %s — %s", resp.status, body)
                if resp.status in (401, 403):
                    raise EonEnergyAuthError(
                        f"Consumption API auth failed: HTTP {resp.status}"
                    )
                if resp.status != 200:
                    raise EonEnergyApiError(
                        f"Consumption API error: HTTP {resp.status} — {body}"
                    )
                return json.loads(body)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EonEnergyApiError(f"Network error: {err}") from err
