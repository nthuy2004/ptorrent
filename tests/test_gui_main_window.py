import os
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.gui.main_window import MainWindow


class _PieceManager:
    def __init__(self, file_id):
        self.file_id = file_id
        self.file_name = "sample.bin"
        self.file_size = 100
        self.total_pieces = 4
        self.bitfield = [1, 0, 0, 0]
        self.piece_states = ["COMPLETED", "PENDING", "PENDING", "PENDING"]

    def get_downloaded_bytes(self):
        return 25

    def get_bitfield(self):
        return list(self.bitfield)


class _FakeManager:
    def __init__(self):
        self.task = SimpleNamespace(
            metadata=SimpleNamespace(
                file_id="file-a",
                file_name="sample.bin",
                file_size=100,
                total_pieces=4,
            ),
            piece_manager=_PieceManager("file-a"),
            status="downloading",
            download_speed=128.0,
            upload_speed=32.0,
        )
        self.create_args = None

    def get_all_tasks(self):
        return [self.task]

    def pause_torrent(self, file_id):
        assert file_id == "file-a"
        self.task.status = "paused"

    def create_and_seed(self, file_path, piece_size):
        self.create_args = (file_path, piece_size)
        return self.task


def _wait_for(qapp, predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.005)
    qapp.processEvents()
    assert predicate()


def test_window_populates_table_and_piece_grid(qapp):
    manager = _FakeManager()
    window = MainWindow(manager)
    try:
        assert window.torrent_table.rowCount() == 1
        assert window.torrent_table.item(0, 0).text() == "sample.bin"
        assert window.torrent_table.item(0, 2).text() == "25.0%"
        assert window.torrent_table.item(0, 5).text() == "Downloading"
        assert window.piece_grid.file_id == "file-a"
        assert window.piece_grid.piece_statuses == (
            "completed",
            "pending",
            "pending",
            "pending",
        )
        assert window.pieces_title_label.text() == "Pieces: 1 / 4 (25.0%)"
        bar = window.torrent_table.cellWidget(0, 2)
        assert bar is not None
        assert bar.value() == 25
        assert bar.text() == "25.0%"
        assert "Torrents: 1 (DL: 1, Seeding: 0)" in window.status_label_torrents.text()
        assert "DL: 128 B/s | UL: 32 B/s" in window.status_label_speeds.text()
        assert "Port:" in window.status_label_port.text()
    finally:
        window.close()


def test_manager_actions_run_in_background_with_arguments(qapp):
    manager = _FakeManager()
    window = MainWindow(manager)
    try:
        window._run_operation("pause_torrent", manager.pause_torrent, "file-a")
        _wait_for(qapp, lambda: not window._workers)
        assert manager.task.status == "paused"
        assert window.torrent_table.item(0, 5).text() == "Paused"

        window._run_operation(
            "create_and_seed",
            manager.create_and_seed,
            "source.bin",
            piece_size=256 * 1024,
        )
        _wait_for(qapp, lambda: not window._workers)
        assert manager.create_args == ("source.bin", 256 * 1024)
    finally:
        window.close()
