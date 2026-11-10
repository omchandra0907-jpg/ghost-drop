"""CLI Entry Point for ghost-drop."""

import argparse
import os
import sys

from .stego import embed_payloads, extract_payload
from .audit import calculate_psnr, export_bitplane_visual, inspect_carrier

def main():
    parser = argparse.ArgumentParser(
        prog="ghost-drop",
        description="Deniable Encryption & Steganographic Dead-Drop CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # hide
    hide_p = subparsers.add_parser("hide", help="Embed decoy and optional real secret into carrier image")
    hide_p.add_argument("--cover", required=True, help="Input carrier PNG image")
    hide_p.add_argument("--output", required=True, help="Output steganographic PNG image")
    hide_p.add_argument("--decoy", required=True, help="Path to decoy payload file")
    hide_p.add_argument("--decoy-pass", required=True, help="Password to unlock decoy payload")
    hide_p.add_argument("--real", help="Path to high-security real payload file (optional)")
    hide_p.add_argument("--real-pass", help="Password to unlock real payload (optional)")

    # extract
    ext_p = subparsers.add_parser("extract", help="Extract and authenticate embedded payload")
    ext_p.add_argument("--carrier", required=True, help="Input steganographic PNG image")
    ext_p.add_argument("--password", required=True, help="Password for decryption")
    ext_p.add_argument("--output", help="Path to write recovered payload (prints to stdout if omitted)")

    # audit
    aud_p = subparsers.add_parser("audit", help="Audit carrier capacity, PSNR, and LSB bit-plane visual")
    aud_p.add_argument("--carrier", required=True, help="Target PNG image")
    aud_p.add_argument("--original", help="Original cover PNG image (for PSNR calculation)")
    aud_p.add_argument("--bitplane", help="Output path to export LSB bit-plane image")

    args = parser.parse_args()

    if args.subcommand == "hide":
        if not os.path.exists(args.cover):
            print(f"[-] Error: Cover image not found: {args.cover}", file=sys.stderr)
            sys.exit(1)
        if not os.path.exists(args.decoy):
            print(f"[-] Error: Decoy file not found: {args.decoy}", file=sys.stderr)
            sys.exit(1)

        with open(args.decoy, "rb") as f:
            decoy_bytes = f.read()

        real_bytes = None
        if args.real:
            if not os.path.exists(args.real):
                print(f"[-] Error: Real payload file not found: {args.real}", file=sys.stderr)
                sys.exit(1)
            if not args.real_pass:
                print("[-] Error: --real-pass is required when --real is specified", file=sys.stderr)
                sys.exit(1)
            with open(args.real, "rb") as f:
                real_bytes = f.read()

        try:
            total_embedded = embed_payloads(
                args.cover,
                args.output,
                decoy_data=decoy_bytes,
                decoy_password=args.decoy_pass,
                real_data=real_bytes,
                real_password=args.real_pass,
            )
            print(f"[+] Successfully embedded payload(s) ({total_embedded} bytes total framed)")
            print(f"[+] Steganographic carrier generated: {args.output}")
        except Exception as e:
            print(f"[-] Steganographic embedding failed: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.subcommand == "extract":
        if not os.path.exists(args.carrier):
            print(f"[-] Error: Carrier image not found: {args.carrier}", file=sys.stderr)
            sys.exit(1)

        try:
            data = extract_payload(args.carrier, args.password)
            if args.output:
                with open(args.output, "wb") as f:
                    f.write(data)
                print(f"[+] Recovered {len(data)} bytes to: {args.output}")
            else:
                try:
                    sys.stdout.write(data.decode("utf-8"))
                except UnicodeDecodeError:
                    sys.stdout.buffer.write(data)
        except Exception as e:
            print(f"[-] Extraction failed: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.subcommand == "audit":
        if not os.path.exists(args.carrier):
            print(f"[-] Error: Carrier image not found: {args.carrier}", file=sys.stderr)
            sys.exit(1)

        info = inspect_carrier(args.carrier)
        print("=== Carrier Capacity Audit ===")
        print(f" Dimensions:       {info['width']} x {info['height']} ({info['channels']} channels)")
        print(f" Total Pixels:     {info['total_pixels']:,}")
        print(f" Raw Bit Capacity: {info['total_carrier_bits']:,} bits")
        print(f" Usable Capacity:  {info['usable_capacity_bytes']:,} bytes ({info['usable_capacity_kb']} KiB)")

        if args.original:
            if not os.path.exists(args.original):
                print(f"[-] Warning: Original cover image not found: {args.original}")
            else:
                mse, psnr, max_drift = calculate_psnr(args.original, args.carrier)
                print("\n=== Steganographic Fidelity Metrics ===")
                print(f" Mean Squared Error (MSE):  {mse:.6f}")
                print(f" Peak Signal-to-Noise Ratio: {psnr:.2f} dB (Imperceptible: >51 dB)")
                print(f" Maximum Pixel Drift:       {max_drift} (Max allowable LSB drift: 1)")

        if args.bitplane:
            export_bitplane_visual(args.carrier, args.bitplane)
            print(f"\n[+] LSB bit-plane visual exported to: {args.bitplane}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
