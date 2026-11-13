# ghost-drop

> Deniable encryption and steganographic dead-drop CLI with collision-free dual payload embedding and statistical noise floor equalization.

![ghost-drop Showcase](assets/demo.gif)

[![CI](https://github.com/omchandra0907-jpg/ghost-drop/actions/workflows/ci.yml/badge.svg)](https://github.com/omchandra0907-jpg/ghost-drop/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

> **🌐 Live Interactive Web Demo:** [https://omchandra0907-jpg.github.io/ghost-drop/](https://omchandra0907-jpg.github.io/ghost-drop/)

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Web_Stego_&_Crypto_Lab-00E5FF?style=for-the-badge&labelColor=0d1117)](https://omchandra0907-jpg.github.io/ghost-drop/)

---

## Architectural Highlights

- **Plausible Deniability via Dual Embedding**: Embeds both an innocent decoy payload and a mission-critical secret into a single cover image. Under coercion, revealing the decoy passphrase cleanly extracts the decoy while leaving zero cryptographic trace or mathematical proof that a second payload exists.
- **Argon2id Key Derivation**: Derives a 32-byte AES-256-GCM key and a 64-bit PRNG permutation seed from passphrases and a 16-byte random salt stored in the initial 128 channel LSBs (43 pixels).
- **Collision-Free Coordinate Scattering**: Uses NumPy-vectorized pseudorandom permutation of bit coordinates. The decoy occupies the first $N_{\text{decoy}}$ coordinates; the real payload draws from non-overlapping coordinates guaranteed by set-difference masking.
- **Entropy Noise Equalization**: Untouched LSB channels across the entire image are overwritten with uniform pseudorandom noise (`os.urandom`), preventing chi-square statistical attacks from distinguishing untouched pixel blocks from encrypted ciphertext.
- **Imperceptible Pixel Drift**: Maximum pixel channel drift $\le 1$, resulting in a Peak Signal-to-Noise Ratio (PSNR) consistently exceeding **51 dB**.
- **Vectorized High-Throughput Processing**: Vectorized bit insertion using `np.unpackbits` / `np.packbits`, embedding half-megabyte payloads in sub-150 ms intervals.

---

## Authenticated Framing Specification

Each embedded payload is self-delimited and authenticated against tampering:

```
+---------------------------+-------------------+----------------------------+-----------------------+
| Payload Length (4 Bytes)  |  Nonce (12 Bytes) | Ciphertext (Length Bytes)  |  AES-GCM Tag (16 B)   |
| Big-Endian uint32         | Cryptographic IV  | AES-256-GCM Encrypted Data | Poly1305 MAC          |
+---------------------------+-------------------+----------------------------+-----------------------+
```

---

## Quickstart

### Installation
```bash
git clone https://github.com/omchandra0907-jpg/ghost-drop.git
cd ghost-drop
pip install -e .
```

### Zero-Setup Showcase
Run the end-to-end embedding, audit, and dual extraction workflow in 5 seconds:
```bash
./samples/run_demo.sh
```

### Embedding Decoy & Hidden Real Secret
```bash
ghost-drop hide \
  --cover landscape.png \
  --output stego.png \
  --decoy decoy.txt \
  --decoy-pass "InnocentPassphrase" \
  --real secret.pdf \
  --real-pass "UltraSecretPassphrase999!"
```

### Extracting Payloads
```bash
# Decrypting decoy under duress:
ghost-drop extract --carrier stego.png --password "InnocentPassphrase" --output recovered_decoy.txt

# Decrypting true secret payload:
ghost-drop extract --carrier stego.png --password "UltraSecretPassphrase999!" --output recovered_secret.pdf
```

### Auditing Carrier Fidelity & PSNR
```bash
ghost-drop audit --carrier stego.png --original landscape.png --bitplane lsb_view.png
```

---

## Running Tests

```bash
pytest
```

---

## License

Distributed under the MIT License. Developed by [omchandra0907-jpg](https://github.com/omchandra0907-jpg).
