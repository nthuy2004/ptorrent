#!/usr/bin/env python3
"""Interactive Fault Injection & Recovery Demo Helper for pTorrent.

Use this script during project demonstration / presentation to showcase
distributed system fault tolerance (Section 4.4, Section 6.4 of DS02).

Usage:
    python scripts/demo_fault_scenarios.py
"""

from __future__ import annotations

import hashlib
import os
import sys
import time


def print_banner() -> None:
    print("=" * 65)
    print("  pTorrent - Distributed Fault Tolerance & Recovery Scenarios")
    print("=" * 65)
    print("1. [Fault 1] Inject corrupted piece into on-disk storage (Tampering)")
    print("2. [Fault 2] Launch Rogue Peer (Intentional bad payload over TCP)")
    print("3. [Fault 3] Verify File Integrity (Compare SHA-256 after recovery)")
    print("4. [Info]    View failure model and recovery mechanisms (BTL Guide)")
    print("0. Exit")
    print("=" * 65)


def scenario_corrupt_disk_chunk() -> None:
    print("\n--- Scenario 1: Corrupt a chunk on disk ---")
    chunk_path = input("Enter path to chunk file (e.g. demo/peer2_leecher1/downloads/<file_id>/chunk_0.dat): ").strip()
    if not os.path.isfile(chunk_path):
        print(f"File not found: '{chunk_path}'")
        return

    with open(chunk_path, "rb") as f:
        data = bytearray(f.read())

    if not data:
        print("Chunk file is empty.")
        return

    # Invert first 16 bytes
    for i in range(min(16, len(data))):
        data[i] ^= 0xFF

    with open(chunk_path, "wb") as f:
        f.write(data)

    print(f"Injected fault: inverted bytes in '{chunk_path}'")
    print("Client will detect SHA-256 mismatch, discard it, and re-fetch from seeder.")


def scenario_rogue_peer() -> None:
    print("\n--- Scenario 2: Launch Rogue Peer Server ---")
    port = input("Enter port for rogue peer (default: 6889): ").strip()
    port_num = int(port) if port.isdigit() else 6889
    piece = input("Enter piece index to corrupt (default: 0): ").strip()
    piece_idx = int(piece) if piece.isdigit() else 0

    from fault_injection_corrupt_chunk import run_rogue_peer
    run_rogue_peer(port_num, piece_idx)


def scenario_verify_hashes() -> None:
    print("\n--- Scenario 3: Verify File Integrity (SHA-256) ---")
    file1 = input("Path to original source file: ").strip()
    file2 = input("Path to downloaded file: ").strip()

    if not os.path.isfile(file1) or not os.path.isfile(file2):
        print("One or both file paths are invalid.")
        return

    def get_hash(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        return h.hexdigest()

    h1 = get_hash(file1)
    h2 = get_hash(file2)

    print(f"\nOriginal file:   {h1}")
    print(f"Downloaded file: {h2}")
    if h1 == h2:
        print("[RESULT] MATCH! 100% Data Integrity Verified despite faults.")
    else:
        print("[RESULT] MISMATCH! File data differs.")


def scenario_view_guide() -> None:
    print("\n--- DS02 Fault Tolerance & Recovery Architecture Guide ---")
    print("1. Failure Model:")
    print("   - Peer Crash / Network Drop: Peer process dies or drops TCP connection.")
    print("   - Data Tampering: Peer sends wrong payload or bit rot on storage.")
    print("   - Tracker Outage: Tracker returns 500 or goes offline.")
    print("\n2. Recovery Mechanisms:")
    print("   - Timeout & Bounded Retries: Downloader resets in-flight piece to PENDING.")
    print("   - Failover: Downloader dynamically requests pending piece from another healthy peer.")
    print("   - Integrity Verification: Every chunk is verified against metadata SHA-256.")
    print("   - Checkpointing & Resume: Restarted client re-scans valid chunks on disk, avoiding re-download.")
    print("   - Tracker Independence: Established P2P swarms continue transferring even if tracker fails.")


def main() -> None:
    while True:
        print_banner()
        choice = input("Select an option (0-4): ").strip()
        if choice == "1":
            scenario_corrupt_disk_chunk()
        elif choice == "2":
            scenario_rogue_peer()
        elif choice == "3":
            scenario_verify_hashes()
        elif choice == "4":
            scenario_view_guide()
        elif choice == "0":
            print("Exiting.")
            break
        else:
            print("Invalid option.")
        print()


if __name__ == "__main__":
    main()
