"""Security helper tests."""

from uuid import uuid4

from eaw.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    h = hash_password("Secret123")
    assert verify_password("Secret123", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip() -> None:
    uid = uuid4()
    token = create_access_token(subject=uid, extra={"email": "a@b.com"})
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid)
    assert payload["type"] == "access"


def test_token_hash_stable() -> None:
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abd")
