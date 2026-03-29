"""Tests for the Nexus Metro token manager."""

from __future__ import annotations

import base64
import json
import time
from unittest.mock import AsyncMock

import aiohttp
import pytest

from custom_components.nexus_metro.auth import NexusMetroAuthError, NexusMetroTokenManager, _decode_jwt_exp


def _make_jwt(exp: float = 0.0) -> str:
    """Build a minimal JWT with the given exp claim."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "WebAPIKey", "exp": exp}).encode()).rstrip(b"=").decode()
    signature = base64.urlsafe_b64encode(b"fakesig").rstrip(b"=").decode()
    return f"{header}.{payload}.{signature}"


def _html_with_token(token: str) -> str:
    """Build a minimal HTML page embedding a token in window.form_data."""
    return f'<html><script>window.form_data = {{"token":"{token}","stations":{{}}}}</script></html>'


def _mock_response(status: int = 200, text: str = "") -> AsyncMock:
    """Create a mock aiohttp response as an async context manager."""
    resp = AsyncMock()
    resp.status = status
    resp.text = AsyncMock(return_value=text)

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestDecodeJwtExp:
    def test_valid_jwt(self):
        token = _make_jwt(exp=1234567890.0)
        assert _decode_jwt_exp(token) == 1234567890.0

    def test_invalid_format(self):
        with pytest.raises(NexusMetroAuthError, match="Invalid JWT format"):
            _decode_jwt_exp("not.a.valid.jwt.too.many.parts")

    def test_too_few_parts(self):
        with pytest.raises(NexusMetroAuthError, match="Invalid JWT format"):
            _decode_jwt_exp("onlyonepart")

    def test_bad_base64(self):
        with pytest.raises(NexusMetroAuthError, match="Failed to decode"):
            _decode_jwt_exp("header.!!!invalid!!!.signature")

    def test_missing_exp_claim(self):
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(b'{"sub":"test"}').rstrip(b"=").decode()
        sig = base64.urlsafe_b64encode(b"sig").rstrip(b"=").decode()
        with pytest.raises(NexusMetroAuthError, match="missing 'exp'"):
            _decode_jwt_exp(f"{header}.{payload}.{sig}")


class TestTokenManager:
    async def test_fetch_token_success(self):
        future_exp = time.time() + 1800
        token = _make_jwt(exp=future_exp)
        html = _html_with_token(token)

        session = AsyncMock(spec=["get"])
        session.get.return_value = _mock_response(text=html)

        manager = NexusMetroTokenManager(session=session)
        result = await manager.async_get_token()

        assert result == token
        session.get.assert_called_once()

    async def test_token_caching(self):
        future_exp = time.time() + 1800
        token = _make_jwt(exp=future_exp)
        html = _html_with_token(token)

        session = AsyncMock(spec=["get"])
        session.get.return_value = _mock_response(text=html)

        manager = NexusMetroTokenManager(session=session)
        await manager.async_get_token()
        await manager.async_get_token()

        # Only one HTTP request despite two calls
        session.get.assert_called_once()

    async def test_token_refresh_after_expiry(self):
        expired_token = _make_jwt(exp=time.time() - 100)
        fresh_token = _make_jwt(exp=time.time() + 1800)

        session = AsyncMock(spec=["get"])
        session.get.side_effect = [
            _mock_response(text=_html_with_token(expired_token)),
            _mock_response(text=_html_with_token(fresh_token)),
        ]

        manager = NexusMetroTokenManager(session=session)

        # First call fetches the expired token
        result1 = await manager.async_get_token()
        assert result1 == expired_token

        # Second call should refetch because the token is expired
        result2 = await manager.async_get_token()
        assert result2 == fresh_token
        assert session.get.call_count == 2

    async def test_invalidate_forces_refetch(self):
        future_exp = time.time() + 1800
        token = _make_jwt(exp=future_exp)
        html = _html_with_token(token)

        session = AsyncMock(spec=["get"])
        session.get.return_value = _mock_response(text=html)

        manager = NexusMetroTokenManager(session=session)
        await manager.async_get_token()
        manager.invalidate()
        await manager.async_get_token()

        assert session.get.call_count == 2

    async def test_fetch_token_connection_error(self):
        session = AsyncMock(spec=["get"])
        session.get.side_effect = aiohttp.ClientError("Connection refused")

        manager = NexusMetroTokenManager(session=session)

        with pytest.raises(NexusMetroAuthError, match="Failed to fetch token page"):
            await manager.async_get_token()

    async def test_fetch_token_http_error(self):
        session = AsyncMock(spec=["get"])
        session.get.return_value = _mock_response(status=500)

        manager = NexusMetroTokenManager(session=session)

        with pytest.raises(NexusMetroAuthError, match="HTTP 500"):
            await manager.async_get_token()

    async def test_fetch_token_bad_html(self):
        session = AsyncMock(spec=["get"])
        session.get.return_value = _mock_response(text="<html>no form data here</html>")

        manager = NexusMetroTokenManager(session=session)

        with pytest.raises(NexusMetroAuthError, match="Could not find token"):
            await manager.async_get_token()

    async def test_fetch_token_malformed_jwt(self):
        session = AsyncMock(spec=["get"])
        session.get.return_value = _mock_response(text=_html_with_token("not-a-jwt"))

        manager = NexusMetroTokenManager(session=session)

        with pytest.raises(NexusMetroAuthError, match="Invalid JWT format"):
            await manager.async_get_token()
