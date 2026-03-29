"""Token manager for the Nexus Metro RTI API.

The API requires a Bearer JWT token, which is obtained by scraping
the public web app at metro-rti-app.nexus.org.uk. Tokens expire
in ~30 minutes and are refreshed automatically.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time

import aiohttp

from .api import NexusMetroAuthError

_LOGGER = logging.getLogger(__name__)

TOKEN_URL = "https://metro-rti-app.nexus.org.uk/"
TOKEN_EXPIRY_MARGIN = 300  # refresh 5 min before expiry
USER_AGENT = "okhttp/3.12.1"

# Matches "token":"<jwt>" inside the window.form_data JSON object
_TOKEN_PATTERN = re.compile(r'"token"\s*:\s*"([^"]+)"')


def _decode_jwt_exp(token: str) -> float:
    """Extract the exp claim from a JWT without verifying the signature."""
    parts = token.split(".")
    if len(parts) != 3:
        raise NexusMetroAuthError(f"Invalid JWT format: expected 3 parts, got {len(parts)}")

    # Add padding for base64 decoding
    payload_b64 = parts[1]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding

    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes)
    except (ValueError, json.JSONDecodeError) as err:
        raise NexusMetroAuthError(f"Failed to decode JWT payload: {err}") from err

    exp = payload.get("exp")
    if exp is None:
        raise NexusMetroAuthError("JWT payload missing 'exp' claim")

    return float(exp)


class NexusMetroTokenManager:
    """Manages JWT token acquisition and caching for the Nexus Metro API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialise with an aiohttp session."""
        self._session = session
        self._token: str | None = None
        self._token_expiry: float = 0.0

    async def async_get_token(self) -> str:
        """Return a valid token, fetching a new one if needed."""
        if self._token is not None and time.time() < (self._token_expiry - TOKEN_EXPIRY_MARGIN):
            return self._token
        return await self._async_fetch_token()

    async def _async_fetch_token(self) -> str:
        """Fetch a fresh JWT from the Nexus Metro web app."""
        headers = {"User-Agent": USER_AGENT}
        try:
            async with self._session.get(TOKEN_URL, headers=headers) as resp:
                if resp.status != 200:
                    raise NexusMetroAuthError(f"Token page returned HTTP {resp.status}")
                html = await resp.text()
        except aiohttp.ClientError as err:
            raise NexusMetroAuthError(f"Failed to fetch token page: {err}") from err

        match = _TOKEN_PATTERN.search(html)
        if not match:
            raise NexusMetroAuthError("Could not find token in web app HTML")

        token = match.group(1)
        expiry = _decode_jwt_exp(token)

        self._token = token
        self._token_expiry = expiry

        _LOGGER.debug("Acquired new API token, expires at %s", expiry)
        return token

    def invalidate(self) -> None:
        """Clear the cached token, forcing a refetch on next use."""
        self._token = None
        self._token_expiry = 0.0
