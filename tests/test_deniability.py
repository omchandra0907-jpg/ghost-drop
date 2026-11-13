"""Unit tests verifying dual-payload plausible deniability, auth failure, and zero pixel drift > 1."""

import os
import tempfile
import numpy as np
import pytest
from PIL import Image

from ghost_drop.stego import embed_payloads, extract_payload
from ghost_drop.audit import calculate_psnr

@pytest.fixture
def sample_cover_image(tmp_path):
    img_path = str(tmp_path / "cover.png")
    # 250x250 RGB image gives ~187 KB raw capacity
    arr = np.random.randint(40, 215, size=(250, 250, 3), dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    img.save(img_path, format="PNG")
    return img_path

def test_dual_embedding_and_plausible_deniability(sample_cover_image, tmp_path):
    stego_path = str(tmp_path / "stego.png")
    decoy_payload = b"Shopping list: milk, eggs, bread, coffee."
    real_payload = b"CRITICAL_PRIVATE_KEY=b3BlbnNzaC1rZXktdjEAAAAABG5vbmU..."

    decoy_pass = "InnocentPass123"
    real_pass = "HighSecurityOpSec999!"

    # Embed both payloads
    total_bytes = embed_payloads(
        sample_cover_image,
        stego_path,
        decoy_data=decoy_payload,
        decoy_password=decoy_pass,
        real_data=real_payload,
        real_password=real_pass,
    )
    assert total_bytes > 0

    # 1. Extract with decoy password recovers decoy cleanly
    rec_decoy = extract_payload(stego_path, decoy_pass)
    assert rec_decoy == decoy_payload

    # 2. Extract with real password recovers secret cleanly
    rec_real = extract_payload(stego_path, real_pass)
    assert rec_real == real_payload

    # 3. Extract with wrong password fails cryptographic authentication
    with pytest.raises(ValueError):
        extract_payload(stego_path, "WrongPasswordTotallyBogus")

def test_zero_pixel_drift_and_psnr(sample_cover_image, tmp_path):
    stego_path = str(tmp_path / "stego.png")
    embed_payloads(
        sample_cover_image,
        stego_path,
        decoy_data=b"Routine decoy data.",
        decoy_password="pass",
    )

    mse, psnr, max_drift = calculate_psnr(sample_cover_image, stego_path)

    # Max pixel change must strictly be <= 1 (LSB alteration only)
    assert max_drift <= 1
    # PSNR must exceed 51.0 dB
    assert psnr > 51.0
