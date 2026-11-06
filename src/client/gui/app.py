from __future__ import annotations

import argparse
import os
import socket
import sys
from typing import Any, Callable

from PyQt6.QtWidgets import QApplication

from client.config import (
    DEFAULT_STORAGE_ROOT,
    DEFAULT_TRACKER_URL,
    DEFAULT_PORT,
    DEFAULT_ADVERTISE_IP,
    DEFAULT_UPLOAD_LIMIT,
    DEFAULT_DOWNLOAD_LIMIT,
    DEFAULT_FAULT_RATE,
)
from client.gui.main_window import MainWindow


def get_local_ip() -> str:
    """Auto-detect the machine's local LAN IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="pTorrent desktop client")
    parser.add_argument(
        "--storage-root",
        default=os.environ.get("PTORRENT_STORAGE_ROOT", DEFAULT_STORAGE_ROOT),
        help="Directory for session data and downloaded pieces",
    )
    parser.add_argument(
        "--tracker-url",
        default=os.environ.get("PTORRENT_TRACKER_URL", DEFAULT_TRACKER_URL),
        help="Tracker base URL, for example https://tracker.example.com",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PTORRENT_PORT", str(DEFAULT_PORT))),
        help="TCP port used to serve pieces to peers",
    )
    parser.add_argument(
        "--advertise-ip",
        default=os.environ.get("PTORRENT_ADVERTISE_IP", DEFAULT_ADVERTISE_IP),
        help="IP address announced to the tracker (pass 'auto' to auto-detect LAN IP, e.g. 172.10.10.2)",
    )
    parser.add_argument(
        "--upload-limit",
        type=int,
        default=int(os.environ.get("PTORRENT_UPLOAD_LIMIT", str(DEFAULT_UPLOAD_LIMIT))),
        help="Maximum upload rate in KiB/s (0 = unlimited)",
    )
    parser.add_argument(
        "--download-limit",
        type=int,
        default=int(os.environ.get("PTORRENT_DOWNLOAD_LIMIT", str(DEFAULT_DOWNLOAD_LIMIT))),
        help="Maximum download rate in KiB/s (0 = unlimited)",
    )
    parser.add_argument(
        "--fault-rate",
        type=float,
        default=float(os.environ.get("PTORRENT_FAULT_RATE", str(DEFAULT_FAULT_RATE))),
        help="Simulated chunk corruption rate (0.0 to 1.0, e.g. 0.1 for 10 percent)",
    )
    return parser


def build_manager(args: argparse.Namespace, manager_class: Callable[..., Any] | None = None) -> Any:
    if manager_class is None:
        try:
            from client.core.torrent_manager import TorrentManager
        except ImportError as exc:
            raise RuntimeError(
                "TorrentManager is not available."
            ) from exc
        manager_class = TorrentManager

    kwargs: dict[str, Any] = {
        "storage_root": args.storage_root,
        "default_port": args.port,
        "tracker_url": args.tracker_url,
    }
    adv_ip = getattr(args, "advertise_ip", None)
    if adv_ip:
        val = str(adv_ip).strip()
        if val.lower() == "auto":
            kwargs["advertise_ip"] = get_local_ip()
        elif val:
            kwargs["advertise_ip"] = val

    if hasattr(args, "upload_limit"):
        kwargs["upload_limit"] = args.upload_limit
    if hasattr(args, "download_limit"):
        kwargs["download_limit"] = args.download_limit
    if hasattr(args, "fault_rate"):
        kwargs["fault_rate"] = args.fault_rate

    manager = manager_class(**kwargs)
    manager.load_session()
    return manager


def run_gui(manager: Any, argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication([sys.argv[0]])
    app.setApplicationName("pTorrent")
    window = MainWindow(manager)
    window.show()
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    args = create_argument_parser().parse_args(argv)
    try:
        manager = build_manager(args)
    except Exception as exc:
        print(f"Could not start pTorrent: {exc}", file=sys.stderr)
        return 2
    return run_gui(manager, argv)
