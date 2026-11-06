from argparse import Namespace

import pytest

from client.gui.app import build_manager, create_argument_parser


class _FakeManager:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.session_loaded = False

    def load_session(self):
        self.session_loaded = True


def test_cli_defaults_and_environment(monkeypatch):
    monkeypatch.setenv("PTORRENT_STORAGE_ROOT", "C:/torrent-data")
    monkeypatch.setenv("PTORRENT_TRACKER_URL", "https://tracker.test")
    monkeypatch.setenv("PTORRENT_PORT", "7000")

    args = create_argument_parser().parse_args([])

    assert args.storage_root == "C:/torrent-data"
    assert args.tracker_url == "https://tracker.test"
    assert args.port == 7000


def test_build_manager_uses_contract_and_loads_session(tmp_path):
    args = Namespace(storage_root=str(tmp_path), tracker_url="https://tracker.test", port=6882)

    manager = build_manager(args, _FakeManager)

    assert manager.kwargs == {
        "storage_root": str(tmp_path),
        "default_port": 6882,
        "tracker_url": "https://tracker.test",
    }
    assert manager.session_loaded is True


def test_build_manager_reports_missing_manager(monkeypatch):
    from client.gui import app

    def fail_import(name, *args, **kwargs):
        if name == "client.core.torrent_manager":
            raise ImportError("module missing")
        return original_import(name, *args, **kwargs)

    original_import = __import__
    monkeypatch.setattr("builtins.__import__", fail_import)
    args = Namespace(storage_root="data", tracker_url="https://tracker.test", port=6881)

    with pytest.raises(RuntimeError, match="TorrentManager is not available"):
        app.build_manager(args)


def test_build_manager_passes_advertise_ip(tmp_path):
    args = Namespace(
        storage_root=str(tmp_path),
        tracker_url="https://tracker.test",
        port=6882,
        advertise_ip="172.10.10.2",
    )
    manager = build_manager(args, _FakeManager)
    assert manager.kwargs["advertise_ip"] == "172.10.10.2"


def test_build_manager_auto_detects_advertise_ip(tmp_path):
    args = Namespace(
        storage_root=str(tmp_path),
        tracker_url="https://tracker.test",
        port=6882,
        advertise_ip="auto",
    )
    manager = build_manager(args, _FakeManager)
    assert "advertise_ip" in manager.kwargs
    assert manager.kwargs["advertise_ip"] != ""
