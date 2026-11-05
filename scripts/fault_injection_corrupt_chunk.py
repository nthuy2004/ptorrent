#!/usr/bin/env python3
"""Fault injection script for pTorrent.

Demonstrates Section 6.4 of DS02: 'Detect an invalid chunk' and fault recovery.
Supports two modes:
1. Direct file corruption: Inverts bytes of an on-disk chunk file.
2. Rogue peer simulation: Starts a faulty TCP peer that intentionally returns
   corrupted piece payloads, proving the pTorrent client detects hash mismatch,
   rejects the piece, marks it CORRUPTED, and re-requests from a valid peer.

Usage:
    # Mode 1: Corrupt a chunk file on disk
    python scripts/fault_injection_corrupt_chunk.py --file demo/peer2/downloads/<file_id>/chunk_0.dat

    # Mode 2: Run rogue peer server to test live network rejection
    python scripts/fault_injection_corrupt_chunk.py --rogue-port 6889 --corrupt-piece 0
"""

from __future__ import annotations

import argparse
import os
import socket
import struct
import sys
import threading


def corrupt_file_on_disk(file_path: str) -> None:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Chunk file not found: {file_path}")

    with open(file_path, "rb") as f:
        data = bytearray(f.read())

    if not data:
        raise ValueError(f"Chunk file is empty: {file_path}")

    # Flip the first 16 bytes
    for i in range(min(16, len(data))):
        data[i] ^= 0xFF

    with open(file_path, "wb") as f:
        f.write(data)

    print(f"Successfully injected fault into: {file_path}")
    print("Corrupted first 16 bytes. When client verifies chunk hash, it will fail and re-fetch.")


def run_rogue_peer(port: int, corrupt_index: int) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen(5)
    print(f"[Rogue Peer] Running on port {port}...")
    print(f"[Rogue Peer] Will respond with CORRUPTED data for piece index {corrupt_index}")

    def handle_client(conn: socket.socket, addr: tuple[str, int]) -> None:
        try:
            # Receive handshake (68 bytes standard)
            handshake = conn.recv(68)
            if len(handshake) >= 68 and handshake[0] == 19:
                file_id = handshake[28:48].decode("utf-8", errors="ignore").strip()
                # Send back handshake
                conn.sendall(handshake)
                print(f"[Rogue Peer] Handshake completed with {addr}")

                while True:
                    hdr = conn.recv(4)
                    if not hdr or len(hdr) < 4:
                        break
                    length = struct.unpack("!I", hdr)[0]
                    if length == 0:
                        continue
                    payload = conn.recv(length)
                    msg_id = payload[0]
                    if msg_id == 6:  # REQUEST message
                        idx = struct.unpack("!I", payload[1:5])[0]
                        print(f"[Rogue Peer] Client requested piece {idx}")
                        # Send PIECE message (id=7) with corrupted data
                        corrupted_data = b"CORRUPTED_FAULT_INJECTION_DATA_" * 32
                        piece_msg = struct.pack("!IBI", len(corrupted_data) + 5, 7, idx) + corrupted_data
                        conn.sendall(piece_msg)
                        print(f"[Rogue Peer] Sent CORRUPTED payload for piece {idx} to {addr}")
        except Exception as e:
            print(f"[Rogue Peer] Connection closed with {addr}: {e}")
        finally:
            conn.close()

    try:
        while True:
            client, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(client, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[Rogue Peer] Stopped.")
    finally:
        server.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="pTorrent Fault Injection & Recovery Tool")
    parser.add_argument(
        "--file",
        type=str,
        help="Path to chunk file on disk to corrupt (e.g. chunk_0.dat)",
    )
    parser.add_argument(
        "--rogue-port",
        type=int,
        help="Run rogue peer server on this port to inject bad pieces over TCP",
    )
    parser.add_argument(
        "--corrupt-piece",
        type=int,
        default=0,
        help="Piece index to corrupt when running rogue peer (default: 0)",
    )

    args = parser.parse_args()

    if args.file:
        try:
            corrupt_file_on_disk(args.file)
            return 0
        except Exception as err:
            print(f"Error: {err}", file=sys.stderr)
            return 1
    elif args.rogue-port:
        run_rogue_peer(args.rogue-port, args.corrupt-piece)
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
