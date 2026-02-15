"""
Encryption utilities for storing user API keys.

Uses Fernet symmetric encryption with a key derived from SESSION_SECRET_KEY.
"""

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _get_fernet() -> Fernet:
    """Derive a Fernet key from SESSION_SECRET_KEY."""
    secret = os.getenv("SESSION_SECRET_KEY", "change-me-to-a-random-secret-at-least-32-chars")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"lingolou-api-keys",
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return Fernet(key)


def encrypt_key(plaintext: str) -> str:
    """Encrypt an API key for storage."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    """Decrypt a stored API key."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
