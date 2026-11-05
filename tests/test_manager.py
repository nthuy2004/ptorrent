"""Test cho torrent_manager.py (chạy được khi không có mạng).

Chạy (tại thư mục gốc của dự án):

    python -m pytest tests/test_manager.py -q
"""

import json
import os
import socket
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.core.bus import bus
from client.core.chunker import Chunker
from client.core.piece_manager import PieceManager
from client.core.torrent_manager import TorrentManager, TorrentTask, normalize_tracker_url

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


# --- TorrentManager ---
class FakeTracker:
    """Tracker giả: ghi lại các lần gọi, trả về danh sách peer cho trước."""

    def __init__(self, peers=None, register_ok=True):
        self.peers = peers or []
        self.register_ok = register_ok
        self.registered = []
        self.announces = []

    def register(self, metadata):
        self.registered.append(metadata.file_id)
        return self.register_ok

    def announce(self, file_id, peer_id, port, uploaded, downloaded, bytes_left,
                 event="", bitfield=None, ip=None):
        self.announces.append({"file_id": file_id, "port": port, "uploaded": uploaded,
                               "downloaded": downloaded, "bytes_left": bytes_left,
                               "event": event, "ip": ip})
        return {"interval": 1, "complete": 0, "incomplete": 0, "peers": list(self.peers)}

    def events(self):
        return [a["event"] for a in self.announces]


@pytest.fixture
def managers():
    """Tạo manager và tự tắt hết khi test xong."""
    created = []
    yield created
    for m in created:
        m.stop()


def make_manager(tmp_path, name="storage", tracker=None, register=None):
    """Manager dùng cổng 0 (hệ điều hành tự chọn) và tracker giả, vòng nền chạy nhanh."""
    m = TorrentManager(str(tmp_path / name), default_port=0, tracker_url="http://x")
    m.tracker = tracker if tracker is not None else FakeTracker()
    m.announce_gap = 0.05
    m.speed_interval = 0.1
    if register is not None:
        register.append(m)
    return m


def write_source(tmp_path, name="movie.bin", size=10 * PIECE + 100):
    path = tmp_path / name
    path.write_bytes(os.urandom(size))
    return str(path)


def wait_for(condition, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return condition()


def test_manager_creates_its_folders(tmp_path):
    m = make_manager(tmp_path)
    assert os.path.isdir(m.storage_root)
    assert os.path.isdir(os.path.join(m.storage_root, "torrents"))


def test_peer_id_is_saved_and_reused(tmp_path):
    first = make_manager(tmp_path)
    second = make_manager(tmp_path)  # cùng thư mục lưu trữ = "mở lại app"
    assert first.peer_id.startswith("PT-")
    assert first.peer_id == second.peer_id


def test_different_storage_gets_different_peer_id(tmp_path):
    a = make_manager(tmp_path, "a")
    b = make_manager(tmp_path, "b")
    assert a.peer_id != b.peer_id


def test_start_opens_a_port_and_stop_marks_it_stopped(tmp_path):
    m = make_manager(tmp_path)
    assert not m.is_running
    m.start()
    try:
        assert m.is_running
        assert m.port > 0
        # kết nối được vào cổng vừa mở
        with socket.create_connection(("127.0.0.1", m.port), timeout=2):
            pass
        m.start()  # gọi lần hai không gây lỗi
    finally:
        m.stop()
    assert not m.is_running
    m.stop()  # tắt lần hai không gây lỗi


def test_two_managers_run_at_the_same_time_on_different_ports(tmp_path):
    a = make_manager(tmp_path, "a")
    b = make_manager(tmp_path, "b")
    a.start()
    b.start()
    try:
        assert a.port != b.port
    finally:
        a.stop()
        b.stop()


def test_no_tasks_at_first(tmp_path):
    m = make_manager(tmp_path)
    assert m.get_all_tasks() == []
    assert m.get_task("khong-ton-tai") is None


def test_get_all_tasks_returns_a_copy(tmp_path):
    m = make_manager(tmp_path)
    task = make_task(subdir(tmp_path, "t"), 1024)
    m._tasks[task.file_id] = task  # tạm thêm thẳng; sau này dùng create_and_seed / add_torrent

    tasks = m.get_all_tasks()
    assert tasks == [task]
    assert m.get_task(task.file_id) is task

    tasks.clear()  # sửa bản sao không ảnh hưởng manager
    assert m.get_all_tasks() == [task]


@pytest.mark.parametrize("given", [
    "http://x",
    "http://x/",
    "http://x/announce.php",
    "  http://x/announce.php/  ",
])
def test_tracker_url_is_normalized(given):
    assert normalize_tracker_url(given) == "http://x"


# --- create_and_seed ---
def test_create_and_seed_starts_seeding(tmp_path, managers):
    m = make_manager(tmp_path, register=managers)
    src = write_source(tmp_path)
    task = m.create_and_seed(src, piece_size=PIECE)  # không cần start() trước

    assert m.is_running  # tự mở cổng
    assert task.status == "seeding"
    assert task.progress == 100.0
    assert task.source_path == src
    assert task.downloader is None
    assert m.get_all_tasks() == [task]
    assert os.path.isfile(task.meta_path)
    assert m.tracker.registered == [task.file_id]
    first = m.tracker.announces[0]
    assert (first["event"], first["bytes_left"], first["port"]) == ("started", 0, m.port)
    assert task.file_id in m.server._piece_managers


def test_create_and_seed_same_file_twice_returns_same_task(tmp_path, managers):
    m = make_manager(tmp_path, register=managers)
    src = write_source(tmp_path)
    a = m.create_and_seed(src, piece_size=PIECE)
    assert m.create_and_seed(src, piece_size=PIECE) is a
    assert len(m.get_all_tasks()) == 1


def test_create_and_seed_still_works_when_tracker_refuses(tmp_path, managers):
    m = make_manager(tmp_path, tracker=FakeTracker(register_ok=False), register=managers)
    assert m.create_and_seed(write_source(tmp_path), piece_size=PIECE).status == "seeding"


def test_create_and_seed_errors(tmp_path, managers):
    m = make_manager(tmp_path, register=managers)
    with pytest.raises(FileNotFoundError):
        m.create_and_seed(str(tmp_path / "khong-co.bin"))
    with pytest.raises(FileNotFoundError):
        m.create_and_seed(str(tmp_path))  # thư mục, không phải file
    with pytest.raises(ValueError):
        m.create_and_seed(write_source(tmp_path), piece_size=0)
    assert m.get_all_tasks() == []


# --- add_torrent ---
def seed_and_get_meta(tmp_path, managers, name="seeder"):
    seeder = make_manager(tmp_path, name, register=managers)
    src = write_source(tmp_path)
    return seeder, src, seeder.create_and_seed(src, piece_size=PIECE)


def test_add_torrent_errors(tmp_path, managers):
    m = make_manager(tmp_path, register=managers)
    with pytest.raises(FileNotFoundError):
        m.add_torrent(str(tmp_path / "khong-co.ptorrent"))
    bad = tmp_path / "bad.ptorrent"
    bad.write_text("day khong phai json", encoding="utf-8")
    with pytest.raises(ValueError):
        m.add_torrent(str(bad))
    incomplete = tmp_path / "incomplete.ptorrent"
    incomplete.write_text(json.dumps({"file_id": "x"}), encoding="utf-8")
    with pytest.raises(ValueError):
        m.add_torrent(str(incomplete))
    assert m.get_all_tasks() == []


def test_add_torrent_starts_downloading_and_announces(tmp_path, managers):
    _, _, seed = seed_and_get_meta(tmp_path, managers)
    leecher = make_manager(tmp_path, "leecher", register=managers)
    task = leecher.add_torrent(seed.meta_path)

    assert task.status == "downloading"
    assert task.progress == 0.0
    assert task.downloader is not None
    assert os.path.dirname(task.meta_path) == leecher.torrents_dir  # đã chép vào storage
    assert leecher.tracker.events()[0] == "started"
    assert leecher.tracker.announces[0]["bytes_left"] == seed.metadata.file_size
    assert leecher.add_torrent(seed.meta_path) is task  # thêm lần hai: trả task cũ


def test_add_torrent_resumes_existing_chunks(tmp_path, managers):
    seeder, src, seed = seed_and_get_meta(tmp_path, managers)
    leecher = make_manager(tmp_path, "leecher", register=managers)
    chunks_dir = os.path.join(leecher.storage_root, "chunks", seed.file_id)
    os.makedirs(chunks_dir)
    for i in range(4):
        with open(os.path.join(chunks_dir, f"chunk_{i}.dat"), "wb") as f:
            f.write(Chunker.read_piece_by_index(src, i, PIECE))

    task = leecher.add_torrent(seed.meta_path)
    assert task.piece_manager.get_bitfield()[:5] == [1, 1, 1, 1, 0]
    assert leecher.tracker.announces[0]["downloaded"] == 4 * PIECE


def test_two_managers_transfer_a_file(tmp_path, managers):
    """Seeder và leecher thật trong cùng một máy, qua socket thật."""
    seeder, src, seed = seed_and_get_meta(tmp_path, managers)
    peers = [{"ip": "127.0.0.1", "port": seeder.port, "peer_id": seeder.peer_id}]
    leecher = make_manager(tmp_path, "leecher", tracker=FakeTracker(peers), register=managers)

    task = leecher.add_torrent(seed.meta_path)
    assert wait_for(lambda: task.status == "completed")

    with open(task.piece_manager.completed_file_path, "rb") as a, open(src, "rb") as b:
        assert a.read() == b.read()
    assert task.progress == 100.0
    # Vòng nền báo tracker "completed"
    assert wait_for(lambda: "completed" in leecher.tracker.events())
    assert task.pending_event == ""
    # Seeder đã phục vụ đủ số byte
    assert wait_for(lambda: seed.piece_manager.uploaded_bytes >= seed.metadata.file_size)


def test_two_files_download_at_the_same_time(tmp_path, managers):
    """Một leecher tải 2 file cùng lúc từ một seeder; hai task không lẫn nhau."""
    seeder = make_manager(tmp_path, "seeder", register=managers)
    src_a = write_source(tmp_path, "a.bin", size=12 * PIECE + 5)
    src_b = write_source(tmp_path, "b.bin", size=9 * PIECE + 77)
    seed_a = seeder.create_and_seed(src_a, piece_size=PIECE)
    seed_b = seeder.create_and_seed(src_b, piece_size=PIECE)
    peers = [{"ip": "127.0.0.1", "port": seeder.port, "peer_id": seeder.peer_id}]
    leecher = make_manager(tmp_path, "leecher", tracker=FakeTracker(peers), register=managers)

    task_a = leecher.add_torrent(seed_a.meta_path)
    task_b = leecher.add_torrent(seed_b.meta_path)
    assert wait_for(lambda: task_a.status == "completed" and task_b.status == "completed")

    for task, src in ((task_a, src_a), (task_b, src_b)):
        with open(task.piece_manager.completed_file_path, "rb") as got, open(src, "rb") as want:
            assert got.read() == want.read()
    assert len(leecher.get_all_tasks()) == 2
    assert leecher.server is not None and leecher.port == leecher.server.port  # chỉ một cổng


# --- pause / resume / remove ---
def add_idle_leecher(tmp_path, managers):
    """Leecher không có peer nào để tải: dừng ở trạng thái downloading."""
    _, _, seed = seed_and_get_meta(tmp_path, managers)
    leecher = make_manager(tmp_path, "leecher", register=managers)
    return leecher, leecher.add_torrent(seed.meta_path)


def test_pause_and_resume(tmp_path, managers):
    leecher, task = add_idle_leecher(tmp_path, managers)
    assert leecher.pause_torrent(task.file_id) is True
    assert task.status == "paused"
    assert not task.downloader._running

    before = len(leecher.tracker.announces)
    leecher._announce_round()  # task đang tạm dừng thì không báo tracker
    assert len(leecher.tracker.announces) == before

    assert leecher.resume_torrent(task.file_id) is True
    assert task.status == "downloading"
    assert task.downloader._running
    assert leecher.tracker.events()[-1] == "started"


def test_pause_resume_remove_unknown_id_returns_false(tmp_path, managers):
    m = make_manager(tmp_path, register=managers)
    assert m.pause_torrent("khong-co") is False
    assert m.resume_torrent("khong-co") is False
    assert m.remove_torrent("khong-co") is False


def test_remove_seeder_never_deletes_source_file(tmp_path, managers):
    seeder, src, seed = seed_and_get_meta(tmp_path, managers)
    assert seeder.remove_torrent(seed.file_id, delete_files=True) is True

    assert seeder.get_all_tasks() == []
    assert os.path.isfile(src)  # file gốc còn nguyên
    assert seeder.tracker.events()[-1] == "stopped"
    assert seed.file_id not in seeder.server._piece_managers
    assert json.load(open(os.path.join(seeder.storage_root, "session.json")))["torrents"] == []


def test_remove_downloaded_file(tmp_path, managers):
    seeder, src, seed = seed_and_get_meta(tmp_path, managers)
    peers = [{"ip": "127.0.0.1", "port": seeder.port, "peer_id": seeder.peer_id}]
    keep = make_manager(tmp_path, "keep", tracker=FakeTracker(peers), register=managers)
    drop = make_manager(tmp_path, "drop", tracker=FakeTracker(peers), register=managers)
    t_keep = keep.add_torrent(seed.meta_path)
    t_drop = drop.add_torrent(seed.meta_path)
    assert wait_for(lambda: t_keep.status == "completed" and t_drop.status == "completed")

    assert keep.remove_torrent(t_keep.file_id) is True  # giữ file
    assert os.path.isfile(t_keep.piece_manager.completed_file_path)

    assert drop.remove_torrent(t_drop.file_id, delete_files=True) is True  # xóa file
    assert not os.path.exists(t_drop.piece_manager.completed_file_path)
    assert not os.path.exists(t_drop.piece_manager.chunks_dir)


# --- session ---
def test_session_round_trip(tmp_path, managers):
    first = make_manager(tmp_path, register=managers)
    src = write_source(tmp_path)
    seed = first.create_and_seed(src, piece_size=PIECE)

    other = make_manager(tmp_path, "other", register=managers)
    other_src = write_source(tmp_path, "other.bin", 5 * PIECE)
    other_seed = other.create_and_seed(other_src, piece_size=PIECE)
    paused = first.add_torrent(other_seed.meta_path)
    first.pause_torrent(paused.file_id)
    first.stop()

    again = make_manager(tmp_path, register=managers)  # "mở lại app"
    loaded = again.load_session()
    assert {t.file_id for t in loaded} == {seed.file_id, paused.file_id}
    assert again.get_task(seed.file_id).status == "seeding"
    assert again.get_task(paused.file_id).status == "paused"
    assert again.get_task(paused.file_id).downloader is not None
    assert again.is_running


def test_load_session_resumes_download_in_background(tmp_path, managers):
    _, _, seed = seed_and_get_meta(tmp_path, managers)
    first = make_manager(tmp_path, "leecher", register=managers)
    first.add_torrent(seed.meta_path)
    first.stop()

    again = make_manager(tmp_path, "leecher", register=managers)
    task = again.load_session()[0]
    assert task.status == "downloading"
    assert wait_for(lambda: "started" in again.tracker.events())  # vòng nền báo tracker


def test_load_session_without_file_or_with_garbage(tmp_path, managers):
    m = make_manager(tmp_path, register=managers)
    assert m.load_session() == []
    with open(os.path.join(m.storage_root, "session.json"), "w", encoding="utf-8") as f:
        f.write("{khong phai json")
    assert m.load_session() == []


def test_load_session_skips_entries_it_cannot_load(tmp_path, managers):
    m = make_manager(tmp_path, register=managers)
    seed = m.create_and_seed(write_source(tmp_path), piece_size=PIECE)
    m.stop()
    path = os.path.join(m.storage_root, "session.json")
    data = json.load(open(path))
    data["torrents"].append({"file_id": "x", "meta_path": str(tmp_path / "mat-roi.ptorrent")})
    data["torrents"].append({"thieu": "meta_path"})
    json.dump(data, open(path, "w"))

    again = make_manager(tmp_path, register=managers)
    assert [t.file_id for t in again.load_session()] == [seed.file_id]


# --- vòng nền: tốc độ, announce, hoàn tất ---
def test_update_speeds_and_events(tmp_path, managers):
    seeder, src, seed = seed_and_get_meta(tmp_path, managers)
    leecher = make_manager(tmp_path, "leecher", register=managers)
    task = leecher.add_torrent(seed.meta_path)
    got = {}

    def on_speed(d):
        if d.get("file_id") == task.file_id:
            got["speed"] = d

    def on_progress(d):
        if d.get("file_id") == task.file_id:
            got["progress"] = d

    bus.subscribe("task.speed", on_speed)
    bus.subscribe("task.progress", on_progress)
    try:
        data = Chunker.read_piece_by_index(src, 0, PIECE)
        assert task.piece_manager.save_and_verify_piece(0, data)
        task.piece_manager.record_uploaded(500)
        leecher._update_speeds(2.0)
    finally:
        bus.unsubscribe("task.speed", on_speed)
        bus.unsubscribe("task.progress", on_progress)

    assert task.download_speed == PIECE / 2.0
    assert task.upload_speed == 250.0
    assert got["speed"]["download_speed"] == PIECE / 2.0
    assert got["progress"] == {"file_id": task.file_id, "downloaded": PIECE,
                               "total": seed.metadata.file_size}
    leecher._update_speeds(1.0)  # không có gì mới: tốc độ về 0
    assert task.download_speed == 0.0


def test_speed_loop_publishes_by_itself(tmp_path, managers):
    m = make_manager(tmp_path, register=managers)
    task = m.create_and_seed(write_source(tmp_path), piece_size=PIECE)
    got = []

    def on_progress(d):
        if d.get("file_id") == task.file_id:
            got.append(d)

    bus.subscribe("task.progress", on_progress)
    try:
        assert wait_for(lambda: len(got) >= 2, timeout=5)
    finally:
        bus.unsubscribe("task.progress", on_progress)


# --- advertise_ip ---
def test_advertise_ip_is_sent_to_tracker(tmp_path, managers, monkeypatch):
    monkeypatch.delenv("PTORRENT_ADVERTISE_IP", raising=False)
    m = make_manager(tmp_path, register=managers)
    m.advertise_ip = "192.168.1.50"
    m.create_and_seed(write_source(tmp_path), piece_size=PIECE)
    assert m.tracker.announces and all(a["ip"] == "192.168.1.50" for a in m.tracker.announces)


def test_no_advertise_ip_by_default(tmp_path, managers, monkeypatch):
    monkeypatch.delenv("PTORRENT_ADVERTISE_IP", raising=False)
    m = TorrentManager(str(tmp_path / "s"), default_port=0, tracker_url="http://x")
    assert m.advertise_ip is None
    m = make_manager(tmp_path, register=managers)
    m.create_and_seed(write_source(tmp_path), piece_size=PIECE)
    assert m.tracker.announces and all(a["ip"] is None for a in m.tracker.announces)


def test_advertise_ip_from_argument_or_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("PTORRENT_ADVERTISE_IP", "  10.0.0.7 ")
    m = TorrentManager(str(tmp_path / "a"), default_port=0, tracker_url="http://x")
    assert m.advertise_ip == "10.0.0.7"
    m = TorrentManager(str(tmp_path / "b"), default_port=0, tracker_url="http://x",
                       advertise_ip="192.168.1.9")
    assert m.advertise_ip == "192.168.1.9"  # tham số thắng biến môi trường
    monkeypatch.setenv("PTORRENT_ADVERTISE_IP", "   ")
    m = TorrentManager(str(tmp_path / "c"), default_port=0, tracker_url="http://x")
    assert m.advertise_ip is None


def test_advertise_ip_is_also_sent_when_stopping(tmp_path, managers, monkeypatch):
    monkeypatch.delenv("PTORRENT_ADVERTISE_IP", raising=False)
    m = make_manager(tmp_path, register=managers)
    m.advertise_ip = "192.168.1.50"
    m.create_and_seed(write_source(tmp_path), piece_size=PIECE)
    m.shutdown()
    stopped = [a for a in m.tracker.announces if a["event"] == "stopped"]
    assert stopped and stopped[-1]["ip"] == "192.168.1.50"


def test_start_speed_calculator_loop_is_idempotent(tmp_path, managers):
    m = make_manager(tmp_path, register=managers)
    m.start()
    m.start_speed_calculator_loop()
    m.start_speed_calculator_loop()
    assert [t.name for t in m._threads].count("tm-speed") == 1


def test_start_speed_calculator_loop_starts_a_stopped_manager(tmp_path, managers):
    m = make_manager(tmp_path, register=managers)
    assert not m.is_running
    m.start_speed_calculator_loop()
    assert m.is_running
    assert [t.name for t in m._threads].count("tm-speed") == 1
    assert all(t.is_alive() for t in m._threads)


def test_announce_round_sends_pending_event_once(tmp_path, managers):
    leecher, task = add_idle_leecher(tmp_path, managers)
    task.pending_event = "completed"
    leecher._announce_round()
    leecher._announce_round()
    assert leecher.tracker.events()[-2:] == ["completed", ""]
    assert task.pending_event == ""


def test_announce_interval_follows_tracker_but_is_capped(tmp_path, managers):
    leecher, task = add_idle_leecher(tmp_path, managers)
    leecher.tracker.announce = lambda **kw: {"interval": 999, "peers": []}
    leecher._announce_round()
    assert leecher.announce_interval == 30.0
    leecher.tracker.announce = lambda **kw: {"interval": 7, "peers": []}
    leecher._announce_round()
    assert leecher.announce_interval == 7.0


def test_tracker_error_does_not_break_the_manager(tmp_path, managers):
    leecher, task = add_idle_leecher(tmp_path, managers)

    def boom(**kw):
        raise RuntimeError("tracker sap")

    leecher.tracker.announce = boom
    leecher._announce_round()  # không ném lỗi
    assert leecher._announce(task, "") == {"interval": 15, "complete": 0,
                                           "incomplete": 0, "peers": []}


def test_file_completed_event_marks_only_the_right_task(tmp_path, managers):
    leecher, task = add_idle_leecher(tmp_path, managers)
    leecher.start()
    leecher._on_file_completed({"file_id": task.file_id, "output_path": "/o/mot/noi/khac"})
    assert task.status == "downloading"  # sự kiện của Manager khác: bỏ qua
    assert task.pending_event == ""

    for i in range(task.metadata.total_pieces):
        data = Chunker.read_piece_by_index(
            os.path.join(str(tmp_path), "movie.bin"), i, PIECE)
        task.piece_manager.save_and_verify_piece(i, data)  # đủ chunk -> gộp file -> file.completed
    assert wait_for(lambda: task.status == "completed", timeout=5)
    assert wait_for(lambda: "completed" in leecher.tracker.events(), timeout=5)


# --- start / shutdown ---
def test_start_raises_when_port_is_taken_and_recovers(tmp_path):
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("0.0.0.0", 0))
    blocker.listen(1)
    port = blocker.getsockname()[1]
    m = TorrentManager(str(tmp_path / "s"), default_port=port, tracker_url="http://x")
    try:
        with pytest.raises(RuntimeError, match=str(port)):
            m.start()
        assert not m.is_running
    finally:
        blocker.close()
    m.start()  # cổng đã trống: mở lại được
    try:
        assert m.is_running
    finally:
        m.stop()


def test_shutdown_tells_tracker_stopped_for_every_task(tmp_path, managers):
    m = make_manager(tmp_path, register=managers)
    a = m.create_and_seed(write_source(tmp_path, "a.bin"), piece_size=PIECE)
    b = m.create_and_seed(write_source(tmp_path, "b.bin"), piece_size=PIECE)
    m.shutdown()

    assert not m.is_running
    stopped = {x["file_id"] for x in m.tracker.announces if x["event"] == "stopped"}
    assert stopped == {a.file_id, b.file_id}
    m.shutdown()  # gọi lần hai không sao


def test_loops_stop_after_stop(tmp_path, managers):
    m = make_manager(tmp_path, register=managers)
    m.start()
    threads = list(m._threads)
    assert all(t.is_alive() for t in threads)
    m.stop()
    assert not any(t.is_alive() for t in threads)
