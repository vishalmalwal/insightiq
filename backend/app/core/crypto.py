"""Encrypt/decrypt client DB credentials at rest (Fernet / AES-128-CBC + HMAC).

The key comes from CREDENTIALS_ENCRYPTION_KEY (never hard-coded, never logged).
Plaintext connection strings never touch the database or the logs.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.errors import AppError


class CryptoError(AppError):
    code = "crypto_error"


def _fernet() -> Fernet:
    key = get_settings().credentials_encryption_key
    if not key:
        raise CryptoError(
            "CREDENTIALS_ENCRYPTION_KEY is not set — cannot store client credentials"
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:  # malformed key
        raise CryptoError("CREDENTIALS_ENCRYPTION_KEY is malformed") from exc


def encrypt(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt(token: bytes) -> str:
    try:
        return _fernet().decrypt(token).decode()
    except InvalidToken as exc:
        raise CryptoError("Could not decrypt stored credentials") from exc


def generate_key() -> str:
    """Convenience for setup docs: prints a fresh urlsafe key."""
    return Fernet.generate_key().decode()
