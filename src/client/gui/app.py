from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtWidgets import QApplication

from client.gui.main_window import MainWindow


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="pTorrent desktop client")
    parser.add_argument(
        "--storage-root",
        default=os.environ.get("PTORRENT_STORAGE_ROOT", str(Path.home() / ".ptorrent")),
        help="Directory for session data and downloaded pieces",
    )
    parser.add_argument(
        "--tracker-url",
        default=os.environ.get("PTORRENT_TRACKER_URL", "https://nth.io.vn"),
        help="Tracker base URL, for example https://tracker.example.com",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PTORRENT_PORT", "6881")),
        help="TCP port used to serve pieces to peers",
    )
    return parser


def build_manager(args: argparse.Namespace, manager_class: Callable[..., Any] | None = None) -> Any:
    if manager_class is None:
        try:
            from client.core.torrent_manager import TorrentManager
        except ImportError as exc:
            raise RuntimeError(
                "TorrentManager is not available. Merge or add "
                "src/client/core/torrent_manager.py before launching the real client."
            ) from exc
        manager_class = TorrentManager

    manager = manager_class(
        storage_root=args.storage_root,
        default_port=args.port,
        tracker_url=args.tracker_url,
    )
    manager.load_session()
    return manager


def run_gui(manager: Any, argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication([sys.argv[0]])
    app.setApplicationName("pTorrent")
    app.setOrganizationName("DS02")
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
