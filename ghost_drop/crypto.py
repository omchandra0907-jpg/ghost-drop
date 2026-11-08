"""Argon2id KDF & AES-256-GCM Authenticated Framing."""

import os
import struct
from typing import Tuple
from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SALT_SIZE = 16
NONCE_SIZE = 12
TAG_SIZE = 16
HEADER_SIZE = 4  # 4-byte big-endian payload length

def derive_key_and_seed(password: str, salt: bytes) -> Tuple[bytes, int]:
    """Derives a 32-byte AES key and a 64-bit PRNG seed via Argon2id."""
    raw = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=2,
        memory_cost=65536,  # 64 MiB
        parallelism=2,
        hash_len=40,  # 32 bytes AES key + 8 bytes PRNG seed
        type=Type.ID,
    )
    key = raw[:32]
    seed = struct.unpack(">Q", raw[32:40])[0]
    return key, seed

def encrypt_frame(key: bytes, plaintext: bytes) -> bytes:
    """Packs and encrypts payload into a self-delimiting authenticated frame:
    [4-byte length][12-byte nonce][ciphertext][16-byte GCM tag]
    """
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    # Associated data binds the payload length to prevent frame truncations
    length_prefix = struct.pack(">I", len(plaintext))
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, associated_data=length_prefix)
    return length_prefix + nonce + ct_with_tag

def decrypt_frame(key: bytes, frame_data: bytes) -> bytes:
    """Verifies and decrypts an authenticated frame.
    Raises ValueError on incorrect password or corrupted ciphertext.
    """
    min_size = HEADER_SIZE + NONCE_SIZE + TAG_SIZE
    if len(frame_data) < min_size:
        raise ValueError("Invalid frame: data is smaller than minimum authenticated header")

    payload_len = struct.unpack(">I", frame_data[:HEADER_SIZE])[0]
    nonce = frame_data[HEADER_SIZE : HEADER_SIZE + NONCE_SIZE]
    expected_frame_size = HEADER_SIZE + NONCE_SIZE + payload_len + TAG_SIZE
    
    if len(frame_data) < expected_frame_size:
        raise ValueError("Frame truncation detected: incomplete ciphertext stream")

    ct_with_tag = frame_data[HEADER_SIZE + NONCE_SIZE : expected_frame_size]
    length_prefix = frame_data[:HEADER_SIZE]

    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ct_with_tag, associated_data=length_prefix)
        return plaintext
    except Exception as e:
        raise ValueError("Cryptographic verification failed: invalid password or corrupted frame") from e

# 16-byte random salt header generator

# [4-byte len][12-byte nonce][ciphertext][16-byte tag] framing

# Authenticated decryption and GCM tag validation
