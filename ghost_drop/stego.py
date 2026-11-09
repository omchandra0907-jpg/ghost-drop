"""NumPy Vectorized LSB Bit-Packing and Collision-Free Steganography."""

import os
import struct
from typing import Optional, Tuple
import numpy as np
from PIL import Image

from .crypto import (
    SALT_SIZE,
    derive_key_and_seed,
    encrypt_frame,
    decrypt_frame,
    HEADER_SIZE,
    NONCE_SIZE,
    TAG_SIZE,
)

SALT_BITS = SALT_SIZE * 8  # 128 bits

def get_carrier_capacity(img_shape: Tuple[int, ...]) -> int:
    """Returns usable payload capacity in bytes for a given image shape (H, W, 3)."""
    h, w, c = img_shape
    total_bits = h * w * c
    if total_bits <= SALT_BITS:
        return 0
    return (total_bits - SALT_BITS) // 8

def embed_payloads(
    cover_image_path: str,
    output_image_path: str,
    decoy_data: bytes,
    decoy_password: str,
    real_data: Optional[bytes] = None,
    real_password: Optional[str] = None,
) -> int:
    """Embeds decoy and optional real payload into cover image with plausible deniability.
    Overwrites unused LSBs with uniform random noise to maintain flat entropy.
    """
    img = Image.open(cover_image_path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)
    h, w, c = arr.shape
    total_channels = h * w * c

    capacity = get_carrier_capacity(arr.shape)
    salt = os.urandom(SALT_SIZE)

    # 1. Derive keys and frames
    key_decoy, seed_decoy = derive_key_and_seed(decoy_password, salt)
    frame_decoy = encrypt_frame(key_decoy, decoy_data)

    frame_real = None
    key_real, seed_real = None, None
    has_dual = (real_data is not None and real_password is not None)
    if has_dual:
        key_real, seed_real = derive_key_and_seed(real_password, salt)
        frame_real = encrypt_frame(key_real, real_data)

    # Capacity validation (enforce < 85% threshold)
    total_needed = len(frame_decoy) + (len(frame_real) if frame_real else 0)
    if total_needed > int(capacity * 0.85):
        raise ValueError(
            f"Payloads exceed safe capacity limit: needed {total_needed} bytes, "
            f"carrier capacity is {capacity} bytes (85% max threshold is {int(capacity * 0.85)} bytes)"
        )

    # 2. Overwrite all LSBs with uniform random noise floor
    flat = arr.reshape(-1)
    random_lsbs = np.random.randint(0, 2, size=total_channels, dtype=np.uint8)
    flat[:] = (flat & 0xFE) | random_lsbs

    # 3. Embed 128-bit salt at fixed channel indices 0..127
    salt_bits = np.unpackbits(np.frombuffer(salt, dtype=np.uint8))
    flat[:SALT_BITS] = (flat[:SALT_BITS] & 0xFE) | salt_bits

    avail_indices = np.arange(SALT_BITS, total_channels, dtype=np.int64)

    # 4. Collision-free domain allocation
    if not has_dual:
        # Single payload uses all channels
        rng = np.random.default_rng(seed_decoy)
        shuffled = rng.permutation(avail_indices)
        bits = np.unpackbits(np.frombuffer(frame_decoy, dtype=np.uint8))
        flat[shuffled[: len(bits)]] = (flat[shuffled[: len(bits)]] & 0xFE) | bits
    else:
        # Dual embedding: even channels for decoy, odd channels for real payload
        even_channels = avail_indices[0::2]
        odd_channels = avail_indices[1::2]

        # Embed Decoy
        rng_decoy = np.random.default_rng(seed_decoy)
        shuffled_decoy = rng_decoy.permutation(even_channels)
        decoy_bits = np.unpackbits(np.frombuffer(frame_decoy, dtype=np.uint8))
        if len(decoy_bits) > len(shuffled_decoy):
            raise ValueError("Decoy payload exceeds partition capacity")
        flat[shuffled_decoy[: len(decoy_bits)]] = (
            flat[shuffled_decoy[: len(decoy_bits)]] & 0xFE
        ) | decoy_bits

        # Embed Real Payload into disjoint partition
        assert frame_real is not None
        assert seed_real is not None
        rng_real = np.random.default_rng(seed_real)
        shuffled_real = rng_real.permutation(odd_channels)
        real_bits = np.unpackbits(np.frombuffer(frame_real, dtype=np.uint8))
        if len(real_bits) > len(shuffled_real):
            raise ValueError("Real payload exceeds partition capacity")
        flat[shuffled_real[: len(real_bits)]] = (
            flat[shuffled_real[: len(real_bits)]] & 0xFE
        ) | real_bits

    # Save output lossless PNG
    out_img = Image.fromarray(arr, mode="RGB")
    out_img.save(output_image_path, format="PNG")
    return total_needed

def extract_payload(carrier_image_path: str, password: str) -> bytes:
    """Extracts and decrypts payload matching the provided password.
    Raises ValueError if password is wrong or no authenticated frame matches.
    """
    img = Image.open(carrier_image_path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)
    flat = arr.reshape(-1)
    total_channels = flat.shape[0]

    # 1. Read salt
    salt_bits = flat[:SALT_BITS] & 0x01
    salt = np.packbits(salt_bits).tobytes()

    # 2. Derive key and PRNG seed
    key, seed = derive_key_and_seed(password, salt)

    avail_indices = np.arange(SALT_BITS, total_channels, dtype=np.int64)

    # Candidate partitions: full domain, even partition, odd partition
    candidate_domains = [
        avail_indices,
        avail_indices[0::2],
        avail_indices[1::2],
    ]

    for domain in candidate_domains:
        if len(domain) < (HEADER_SIZE + NONCE_SIZE + TAG_SIZE) * 8:
            continue

        rng = np.random.default_rng(seed)
        shuffled = rng.permutation(domain)

        # Read 32-bit length prefix
        len_bits = flat[shuffled[:32]] & 0x01
        len_bytes = np.packbits(len_bits).tobytes()
        payload_len = struct.unpack(">I", len_bytes)[0]

        max_possible = len(domain) // 8
        if payload_len <= 0 or payload_len > max_possible:
            continue

        frame_size = HEADER_SIZE + NONCE_SIZE + payload_len + TAG_SIZE
        frame_bits_count = frame_size * 8
        if frame_bits_count > len(shuffled):
            continue

        frame_bits = flat[shuffled[:frame_bits_count]] & 0x01
        frame_bytes = np.packbits(frame_bits).tobytes()

        try:
            plaintext = decrypt_frame(key, frame_bytes)
            return plaintext
        except ValueError:
            continue

    raise ValueError("Authentication failed: invalid password or no payload found")

# Carrier capacity: floor(H * W * 3 / 8) bytes

# Fast vectorized bit manipulation

# 64-bit Argon2 PRNG coordinate permutation

# Disjoint even/odd channel partition domains

# Independent payload extraction

# Statistical entropy noise floor equalization

# Absolute pixel channel drift <= 1 guarantee
