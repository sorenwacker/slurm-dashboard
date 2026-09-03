"""Admin tokens must not be forgeable with a key that ships in the repository."""

import logging
from datetime import datetime, timedelta

import jwt
import pytest
from backend.app.core import admin_auth
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

PLACEHOLDER = "change-this-to-a-random-secret-key-in-production"


def bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def forged(sub: str, key: str) -> str:
    return jwt.encode({"sub": sub, "exp": datetime.utcnow() + timedelta(hours=1)}, key, algorithm="HS256")


@pytest.fixture
def admin_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # keep the checkout's data/clusters.json out of the admin email lookup
    monkeypatch.setattr(admin_auth.settings, "admin_users", "alice:$2b$12$notahashbutnotneededhere")
    monkeypatch.setattr(admin_auth.settings, "admin_emails", "")
    monkeypatch.setattr(admin_auth.settings, "superadmin_emails", "boss@example.com")
    # A deployment that left the placeholder in place must not sign with it
    monkeypatch.setattr(admin_auth, "SECRET_KEY", admin_auth.resolve_signing_key(PLACEHOLDER))


def test_unset_key_is_replaced_by_a_random_one(caplog):
    with caplog.at_level(logging.WARNING):
        first = admin_auth.resolve_signing_key("")
        second = admin_auth.resolve_signing_key(None)
    assert first != second
    assert len(first) >= 32
    assert "ADMIN_SECRET_KEY" in caplog.text


def test_placeholder_key_is_not_used_for_signing():
    assert admin_auth.resolve_signing_key(PLACEHOLDER) != PLACEHOLDER


def test_configured_key_is_used_verbatim():
    assert admin_auth.resolve_signing_key("configured-secret") == "configured-secret"


def test_token_signed_with_placeholder_is_rejected(admin_config):
    with pytest.raises(HTTPException) as exc:
        admin_auth.verify_token(bearer(forged("alice", PLACEHOLDER)))
    assert exc.value.status_code == 401


def test_token_for_unknown_subject_is_rejected(admin_config):
    with pytest.raises(HTTPException) as exc:
        admin_auth.verify_token(bearer(forged("mallory", admin_auth.SECRET_KEY)))
    assert exc.value.status_code == 401


def test_tokens_for_configured_admins_are_accepted(admin_config):
    assert admin_auth.verify_token(bearer(admin_auth.create_access_token({"sub": "alice"}))) == "alice"
    assert (
        admin_auth.verify_token(bearer(admin_auth.create_access_token({"sub": "Boss@example.com"})))
        == "Boss@example.com"
    )
