"""Credential encryption round-trips and rejects tampered data."""
from __future__ import annotations

import pytest

from app.core.crypto import CryptoError, decrypt, encrypt


def test_round_trip() -> None:
    secret = "postgresql://user:pass@host:5432/db?sslmode=require"
    token = encrypt(secret)
    assert token != secret.encode()          # actually encrypted
    assert secret.encode() not in token       # plaintext not embedded
    assert decrypt(token) == secret


def test_tampered_token_rejected() -> None:
    with pytest.raises(CryptoError):
        decrypt(b"not-a-valid-fernet-token")
