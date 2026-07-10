"""Secret encryption tests."""

from eaw.infrastructure.security.crypto import decrypt_secret, encrypt_secret


def test_encrypt_roundtrip() -> None:
    raw = "ghp_test_token_12345"
    enc = encrypt_secret(raw)
    assert enc != raw
    assert decrypt_secret(enc) == raw
