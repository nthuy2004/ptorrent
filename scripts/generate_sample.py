#!/usr/bin/env python3
"""Script to generate arbitrary sample binary files for pTorrent benchmarks and demos.

Usage:
    python scripts/generate_sample.py --size 20 --output sample_data.bin
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate sample binary files for pTorrent demo")
    parser.add_argument(
        "--size",
        type=int,
        default=20,
        help="File size in megabytes (MiB), default: 20",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="sample_data.bin",
        help="Destination path for generated file, default: sample_data.bin",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for deterministic generation",
    )
    return parser.parse_args()


def generate_file(output_path: str, size_mib: int, seed: int | None = None) -> str:
    if size_mib <= 0:
        raise ValueError("size_mib must be greater than 0")

    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    hasher = hashlib.sha256()
    total_bytes = size_mib * 1024 * 1024
    block_size = 1024 * 1024  # 1 MiB chunks

    import random
    if seed is not None:
        random.seed(seed)

    bytes_written = 0
    with open(output_path, "wb") as f:
        while bytes_written < total_bytes:
            current_block = min(block_size, total_bytes - bytes_written)
            if seed is not None:
                data = bytes(random.getrandbits(8) for _ in range(current_block))
            else:
                data = os.urandom(current_block)
            f.write(data)
            hasher.update(data)
            bytes_written += current_block

    sha256 = hasher.hexdigest()
    print(f"Generated sample file successfully:")
    print(f"  Path:   {output_path}")
    print(f"  Size:   {bytes_written} bytes ({size_mib} MiB)")
    print(f"  SHA256: {sha256}")
    return sha256


def main() -> int:
    args = parse_args()
    try:
        generate_file(args.output, args.size, args.seed)
        return 0
    except Exception as exc:
        print(f"Error generating sample file: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
