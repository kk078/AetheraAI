"""Tests for the optional API auth gate (orchestrator/auth.py)."""

import pytest

from orchestrator import auth


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("API_AUTH_ENABLED", raising=False)
    assert auth.is_auth_enabled() is False
    # Everything is allowed when disabled.
    assert auth.request_authorized("/api/chat", "POST", None) is True


def test_extract_bearer():
    assert auth._extract_bearer("Bearer abc123") == "abc123"
    assert auth._extract_bearer("bearer abc123") == "abc123"
    assert auth._extract_bearer("Basic abc") is None
    assert auth._extract_bearer(None) is None
    assert auth._extract_bearer("") is None


def test_check_api_key():
    keys = {"key-one", "key-two"}
    assert auth.check_api_key("Bearer key-one", keys) is True
    assert auth.check_api_key("Bearer key-two", keys) is True
    assert auth.check_api_key("Bearer wrong", keys) is False
    assert auth.check_api_key(None, keys) is False
    assert auth.check_api_key("Bearer ", keys) is False


def test_enabled_requires_valid_key(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "secret-a, secret-b")
    assert auth.is_auth_enabled() is True
    assert auth.allowed_keys() == {"secret-a", "secret-b"}

    # Protected path without/with key
    assert auth.request_authorized("/api/chat", "POST", None) is False
    assert auth.request_authorized("/api/chat", "POST", "Bearer secret-a") is True
    assert auth.request_authorized("/api/chat", "POST", "Bearer nope") is False


def test_ws_authorized(monkeypatch):
    # Disabled → any (or no) token is accepted.
    monkeypatch.setenv("API_AUTH_ENABLED", "false")
    assert auth.ws_authorized(None) is True

    # Enabled → token must match a configured key.
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "ws-key")
    assert auth.ws_authorized("ws-key") is True
    assert auth.ws_authorized("nope") is False
    assert auth.ws_authorized(None) is False
    assert auth.ws_authorized("") is False


def test_enabled_allows_public_and_non_api(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "k")
    assert auth.request_authorized("/api/health", "GET", None) is True
    assert auth.request_authorized("/docs", "GET", None) is True
    assert auth.request_authorized("/", "GET", None) is True            # non-/api
    assert auth.request_authorized("/api/chat", "OPTIONS", None) is True  # CORS preflight
