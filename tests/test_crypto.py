"""Unit tests for Argon2id KDF and AES-256-GCM authenticated framing."""

import pytest
from ghost_drop.crypto import derive_key_and_seed, encrypt_frame, decrypt_frame

def test_kdf_consistency():
    salt = b"0123456789abcdef"
    k1, s1 = derive_key_and_seed("strong_passphrase", salt)
    k2, s2 = derive_key_and_seed("strong_passphrase", salt)
    assert k1 == k2
    assert s1 == s2
    assert len(k1) == 32

def test_frame_encrypt_decrypt():
    key = b"\xaa" * 32
    plaintext = b"Top secret operational intelligence."
    frame = encrypt_frame(key, plaintext)

    decrypted = decrypt_frame(key, frame)
    assert decrypted == plaintext

def test_wrong_key_fails_auth():
    key1 = b"\xaa" * 32
    key2 = b"\xbb" * 32
    frame = encrypt_frame(key1, b"classified document")

    with pytest.raises(ValueError):
        decrypt_frame(key2, frame)

def test_tampered_frame_fails_auth():
    key = b"\xaa" * 32
    frame = bytearray(encrypt_frame(key, b"unaltered message"))
    # Flip one byte in the ciphertext
    frame[25] ^= 0x01

    with pytest.raises(ValueError):
        decrypt_frame(key, bytes(frame))
