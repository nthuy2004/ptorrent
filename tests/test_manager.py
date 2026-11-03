"""Test cho torrent_manager.py (chạy được khi không có mạng).

Chạy (tại thư mục gốc của dự án):

    python -m pytest tests/test_manager.py -q
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.core.chunker import Chunker
from client.core.piece_manager import PieceManager
from client.core.torrent_manager import TorrentTask

PIECE = 1024


def make_task(tmp_path, size, have=None, **task_kwargs):
    """Tạo một TorrentTask thật.

    have = None      -> chưa có chunk nào
    have = "all"     -> có file gốc, đủ 100%
    have = [0, 1, 2] -> chỉ có các chunk với chỉ số này (đã chép sẵn vào đĩa)
    """
    src = tmp_path / "source.bin"
    src.write_bytes(os.urandom(size))
    meta = Chunker().create_metadata(str(src), "http://x/announce.php", PIECE)
    storage = str(tmp_path / "storage")

    if isinstance(have, list):
        chunks_dir = os.path.join(storage, "chunks", meta.file_id)
        os.makedirs(chunks_dir)
        for i in have:
            data = Chunker.read_piece_by_index(str(src), i, PIECE)
            with open(os.path.join(chunks_dir, f"chunk_{i}.dat"), "wb") as f:
                f.write(data)

    original = str(src) if have == "all" else None
    pm = PieceManager(meta, storage, original_file_path=original)
    return TorrentTask(metadata=meta, piece_manager=pm, **task_kwargs)


def subdir(tmp_path, name):
    """Thư mục con riêng, để tạo nhiều task trong cùng một test."""
    path = tmp_path / name
    path.mkdir()
    return path


def test_default_values(tmp_path):
    task = make_task(tmp_path, 4 * PIECE)
    assert task.status == "downloading"
    assert task.downloader is None
    assert task.meta_path == ""
    assert task.source_path is None
    assert task.pending_event == ""
    assert task.downloaded_bytes_last_sec == 0
    assert task.uploaded_bytes_last_sec == 0
    assert task.download_speed == 0.0
    assert task.upload_speed == 0.0


def test_file_id_comes_from_metadata(tmp_path):
    task = make_task(tmp_path, 4 * PIECE)
    assert task.file_id == task.metadata.file_id


def test_progress_is_zero_when_nothing_downloaded(tmp_path):
    assert make_task(tmp_path, 10 * PIECE).progress == 0.0


def test_progress_is_100_when_the_whole_file_is_there(tmp_path):
    assert make_task(tmp_path, 10 * PIECE, have="all").progress == 100.0


def test_progress_in_the_middle(tmp_path):
    task = make_task(tmp_path, 10 * PIECE, have=[0, 1, 2, 3, 4])
    assert task.progress == pytest.approx(50.0)


def test_progress_counts_a_short_last_piece_by_its_real_size(tmp_path):
    size = 3 * PIECE + 100  # 4 chunk, chunk cuối chỉ có 100 byte
    task = make_task(tmp_path, size, have=[0, 1, 2])
    assert task.progress == pytest.approx(3 * PIECE * 100 / size)


def test_progress_is_100_when_a_file_with_a_short_last_piece_is_complete(tmp_path):
    assert make_task(tmp_path, 3 * PIECE + 100, have="all").progress == 100.0


def test_progress_follows_newly_downloaded_chunks(tmp_path):
    task = make_task(tmp_path, 10 * PIECE, have=[0, 1, 2, 3, 4])
    data = Chunker.read_piece_by_index(str(tmp_path / "source.bin"), 5, PIECE)
    assert task.piece_manager.save_and_verify_piece(5, data)
    assert task.progress == pytest.approx(60.0)


def test_progress_of_an_empty_file(tmp_path):
    assert make_task(subdir(tmp_path, "full"), 0, have="all").progress == 100.0
    assert make_task(subdir(tmp_path, "none"), 0).progress == 0.0


def test_tasks_compare_by_identity_and_can_go_in_a_set(tmp_path):
    a = make_task(subdir(tmp_path, "a"), 4 * PIECE)
    b = make_task(subdir(tmp_path, "b"), 4 * PIECE)
    assert a == a
    assert a != b
    assert len({a, b, a}) == 2
