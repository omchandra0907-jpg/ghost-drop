"""Carrier Audit, Bit-Plane Exporter, and PSNR Calculation Engine."""

import math
from typing import Dict, Tuple
import numpy as np
from PIL import Image

from .stego import get_carrier_capacity

def calculate_psnr(orig_path: str, stego_path: str) -> Tuple[float, float, int]:
    """Calculates Mean Squared Error (MSE), Peak Signal-to-Noise Ratio (PSNR dB),
    and maximum absolute pixel drift between original and stego images.
    """
    img1 = Image.open(orig_path).convert("RGB")
    img2 = Image.open(stego_path).convert("RGB")

    arr1 = np.array(img1, dtype=np.float64)
    arr2 = np.array(img2, dtype=np.float64)

    if arr1.shape != arr2.shape:
        raise ValueError("Images have different resolutions")

    diff = np.abs(arr1 - arr2)
    max_drift = int(np.max(diff))
    mse = np.mean(diff ** 2)

    if mse == 0.0:
        return 0.0, float("inf"), max_drift

    psnr = 10.0 * math.log10((255.0 ** 2) / mse)
    return float(mse), float(psnr), max_drift

def export_bitplane_visual(image_path: str, output_path: str):
    """Exports the LSB bit-plane as a high-contrast visual image."""
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)

    # Extract least significant bit and amplify to 255 for visualization
    lsb_plane = (arr & 0x01) * 255
    out_img = Image.fromarray(lsb_plane, mode="RGB")
    out_img.save(output_path, format="PNG")

def inspect_carrier(image_path: str) -> Dict[str, any]:
    """Returns metadata and capacity analytics for carrier image."""
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)
    h, w, c = arr.shape
    capacity = get_carrier_capacity(arr.shape)

    return {
        "width": w,
        "height": h,
        "channels": c,
        "total_pixels": w * h,
        "total_carrier_bits": w * h * c,
        "usable_capacity_bytes": capacity,
        "usable_capacity_kb": round(capacity / 1024, 2),
    }
