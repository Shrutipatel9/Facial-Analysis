"""Unit tests for CSRF origin / header checks."""

from unittest.mock import MagicMock

import pytest

from app.core.csrf import assert_cookie_request_allowed
from app.exceptions import CsrfRejectedError


def _request(*, origin: str | None = None, referer: str | None = None, requested_with: str | None = "XMLHttpRequest"):
    headers: dict[str, str] = {}
    if origin is not None:
        headers["origin"] = origin
    if referer is not None:
        headers["referer"] = referer
    if requested_with is not None:
        headers["x-requested-with"] = requested_with
    req = MagicMock()
    req.headers = headers
    return req


def test_allows_matching_origin_and_header(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    from app.core.config import get_settings

    get_settings.cache_clear()
    assert_cookie_request_allowed(_request(origin="http://localhost:3000"))
    get_settings.cache_clear()


def test_rejects_missing_requested_with(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    from app.core.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(CsrfRejectedError):
        assert_cookie_request_allowed(_request(origin="http://localhost:3000", requested_with=None))
    get_settings.cache_clear()


def test_rejects_foreign_origin(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    from app.core.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(CsrfRejectedError):
        assert_cookie_request_allowed(_request(origin="https://evil.example"))
    get_settings.cache_clear()


def test_allows_matching_referer_when_origin_absent(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    from app.core.config import get_settings

    get_settings.cache_clear()
    assert_cookie_request_allowed(_request(referer="http://localhost:3000/dashboard"))
    get_settings.cache_clear()
