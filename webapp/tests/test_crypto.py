"""Tests for webapp/services/crypto.py"""

import pytest


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET_KEY", "test-secret-key-at-least-32-characters-long")
    from webapp.services.crypto import decrypt_key, encrypt_key

    plaintext = "sk-abc123xyz"
    ciphertext = encrypt_key(plaintext)
    assert ciphertext != plaintext
    assert decrypt_key(ciphertext) == plaintext


def test_different_plaintexts_different_ciphertexts(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET_KEY", "test-secret-key-at-least-32-characters-long")
    from webapp.services.crypto import encrypt_key

    c1 = encrypt_key("key-one")
    c2 = encrypt_key("key-two")
    assert c1 != c2


def test_tampered_ciphertext_raises(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET_KEY", "test-secret-key-at-least-32-characters-long")
    from webapp.services.crypto import decrypt_key, encrypt_key

    ciphertext = encrypt_key("secret")
    tampered = ciphertext[:-5] + "XXXXX"
    with pytest.raises(Exception):
        decrypt_key(tampered)


def test_empty_string_roundtrip(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET_KEY", "test-secret-key-at-least-32-characters-long")
    from webapp.services.crypto import decrypt_key, encrypt_key

    ciphertext = encrypt_key("")
    assert decrypt_key(ciphertext) == ""


def test_different_secret_cannot_decrypt(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET_KEY", "first-secret-key-at-least-32-characters-long!")
    from webapp.services.crypto import encrypt_key

    ciphertext = encrypt_key("my-api-key")

    monkeypatch.setenv("SESSION_SECRET_KEY", "second-secret-key-totally-different-32-chars!")
    from webapp.services.crypto import decrypt_key

    with pytest.raises(Exception):
        decrypt_key(ciphertext)
