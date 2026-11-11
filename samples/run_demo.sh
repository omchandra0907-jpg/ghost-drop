#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "=== Ghost-Drop Steganographic & Plausible Deniability Demo ==="
echo "[1] Auditing sample cover carrier..."
ghost-drop audit --carrier samples/sample_cover.png

echo ""
echo "[2] Embedding Decoy ('InnocentPass') and Real Secret ('classified999')..."
ghost-drop hide \
  --cover samples/sample_cover.png \
  --output samples/stego_output.png \
  --decoy samples/decoy_notes.txt \
  --decoy-pass "InnocentPass" \
  --real samples/secret_payload.txt \
  --real-pass "classified999"

echo ""
echo "[3] Verifying PSNR & LSB fidelity..."
ghost-drop audit --carrier samples/stego_output.png --original samples/sample_cover.png --bitplane samples/lsb_plane.png

echo ""
echo "[4] Extracting under coercion (Decoy password):"
ghost-drop extract --carrier samples/stego_output.png --password "InnocentPass"

echo ""
echo "[5] Extracting true secret (Real password):"
ghost-drop extract --carrier samples/stego_output.png --password "classified999"

echo ""
echo "[6] Extracting with invalid password (Simulating adversary trial):"
ghost-drop extract --carrier samples/stego_output.png --password "adversary_guess" || true

echo ""
echo "=== Showcase Complete ==="
