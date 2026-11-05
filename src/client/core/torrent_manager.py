"""TorrentManager: gom nhiều tác vụ tải / seed vào một ứng dụng Client.

create_and_seed, add_torrent, load_session băm file nên chậm: giao diện phải
gọi chúng ở thread nền. Manager tự mở cổng TCP ở lần gọi đầu (không cần start()).
"""

import atexit
import json
import os
import shutil
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from client.core.bus import bus
from client.core.chunker import Chunker, Metadata, DEFAULT_PIECE_SIZE
from client.core.downloader import Downloader
from client.core.peer_server import PeerServer
from client.core.piece_manager import PieceManager
from client.config import DEFAULT_UPLOAD_LIMIT, DEFAULT_DOWNLOAD_LIMIT, DEFAULT_FAULT_RATE
from client.core.tracker import Tracker
from client.utils.log import logger

# Địa chỉ gốc của tracker (Tracker tự nối /announce.php), lấy theo main.py
DEFAULT_TRACKER_URL = "https://tracker.nth.id.vn"
DEFAULT_PORT = 6881  # cổng chuẩn BitTorrent
SESSION_FILE = "session.json"
ADVERTISE_IP_ENV = "PTORRENT_ADVERTISE_IP"  # IP báo tracker thay cho IP tracker tự thấy
MAX_ANNOUNCE_INTERVAL = 30.0  # giây


@dataclass(eq=False)
class TorrentTask:
    """Trạng thái của MỘT file.

    status: "seeding" | "downloading" | "completed" | "paused".
    eq=False: so sánh theo đối tượng, nên task dùng được làm khóa dict / phần tử set.
    """

    metadata: Metadata
    piece_manager: PieceManager
    downloader: Optional[Downloader] = None  # None nếu là seeder thuần
    status: str = "downloading"

    # Ngoài hướng dẫn gốc, dùng cho các bước sau:
    meta_path: str = ""  # file .ptorrent
    source_path: Optional[str] = None  # file gốc (nếu tự tạo)
    pending_event: str = ""  # sự kiện chờ báo tracker, ví dụ "completed"

    # Giá trị ở lần đo trước, để tính tốc độ
    downloaded_bytes_last_sec: int = 0
    uploaded_bytes_last_sec: int = 0
    download_speed: float = 0.0  # bytes/giây
    upload_speed: float = 0.0  # bytes/giây

    @property
    def file_id(self) -> str:
        return self.metadata.file_id

    @property
    def progress(self) -> float:
        """Phần trăm đã tải (0.0 đến 100.0)."""
        total = self.metadata.file_size
        if total <= 0:
            return 100.0 if self.piece_manager.is_complete() else 0.0
        downloaded = self.piece_manager.get_downloaded_bytes()
        return min(100.0, downloaded * 100.0 / total)


def normalize_tracker_url(url: str) -> str:
    """Đưa địa chỉ tracker về dạng gốc (cắt /announce.php vì Tracker tự nối thêm)."""
    url = url.strip().rstrip("/")
    suffix = "/announce.php"
    if url.endswith(suffix):
        url = url[: -len(suffix)]
    return url


class TorrentManager:
    """Giữ danh sách TorrentTask và dùng chung MỘT PeerServer (một cổng TCP).

    default_port=0: hệ điều hành tự chọn cổng (dùng khi test).
    advertise_ip: IP gửi kèm mỗi lần báo tracker, để demo trong cùng mạng LAN (tracker
    chỉ thấy IP công khai). Bỏ trống thì đọc biến môi trường PTORRENT_ADVERTISE_IP;
    vẫn trống thì tracker tự lấy IP của kết nối.
    """

    def __init__(
        self,
        storage_root: str,
        default_port: int = DEFAULT_PORT,
        tracker_url: str = DEFAULT_TRACKER_URL,
        advertise_ip: Optional[str] = None,
        upload_limit: Optional[int] = None,
        download_limit: Optional[int] = None,
        fault_rate: Optional[float] = None,
    ):
        self.storage_root = os.path.abspath(storage_root)
        self.torrents_dir = os.path.join(self.storage_root, "torrents")
        os.makedirs(self.torrents_dir, exist_ok=True)

        self.tracker_url = normalize_tracker_url(tracker_url)
        self.tracker = Tracker(self.tracker_url)
        self.advertise_ip = (advertise_ip or os.environ.get(ADVERTISE_IP_ENV, "")).strip() or None

        self.upload_limit = DEFAULT_UPLOAD_LIMIT if upload_limit is None else upload_limit
        self.download_limit = DEFAULT_DOWNLOAD_LIMIT if download_limit is None else download_limit
        self.fault_rate = DEFAULT_FAULT_RATE if fault_rate is None else fault_rate

        self.peer_id = self._load_or_create_peer_id()
        self.server = PeerServer(
            self.peer_id,
            "0.0.0.0",
            default_port,
            upload_limit=self.upload_limit,
            fault_rate=self.fault_rate,
        )

        # file_id -> TorrentTask; luôn giữ self._lock khi truy cập
        self._tasks: Dict[str, TorrentTask] = {}
        self._lock = threading.RLock()
        self._running = False

        # Hai vòng nền (chu kỳ tính bằng giây, test có thể chỉnh nhỏ lại)
        self.announce_interval = 15.0  # cập nhật theo "interval" tracker trả về
        self.announce_gap = 2.0  # nghỉ tối thiểu giữa hai vòng announce
        self.speed_interval = 1.0
        self._announce_now = threading.Event()  # đánh thức vòng announce sớm
        self._stop_event = threading.Event()
        self._threads: List[threading.Thread] = []

    # --- Bật / tắt ---
    @property
    def port(self) -> int:
        """Cổng đang dùng (sau start() là cổng thật, kể cả khi truyền 0)."""
        return self.server.port

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Mở cổng TCP và bật hai vòng nền. Gọi nhiều lần không sao.

        Ném RuntimeError nếu không mở được cổng (thường do cổng đang bị chiếm).
        """
        with self._lock:
            if self._running:
                return
            try:
                self.server.start()
            except OSError as e:
                self.server.stop()  # PeerServer đã lỡ đặt _running=True, trả lại
                raise RuntimeError(f"Không mở được cổng {self.server.port}: {e}") from e
            self._running = True
            self._stop_event = threading.Event()
            self._announce_now.clear()
            bus.subscribe("file.completed", self._on_file_completed)
            announce = threading.Thread(target=self._announce_loop, args=(self._stop_event,),
                                        daemon=True, name="tm-announce")
            self._threads = [announce]
            announce.start()
            self.start_speed_calculator_loop()
        atexit.register(self.shutdown)
        logger.i(f"TorrentManager started: peer_id={self.peer_id} port={self.port}")

    def start_speed_calculator_loop(self) -> None:
        """Bật vòng tính tốc độ mỗi giây (task.speed, task.progress). Gọi nhiều lần không sao.

        start() đã tự gọi hàm này; nếu manager chưa chạy thì hàm này gọi start() luôn.
        """
        with self._lock:
            if not self._running:
                self.start()  # start() sẽ gọi lại hàm này khi đã đặt _running
                return
            if any(t.name == "tm-speed" and t.is_alive() for t in self._threads):
                return
            speed = threading.Thread(target=self._speed_loop, args=(self._stop_event,),
                                     daemon=True, name="tm-speed")
            self._threads.append(speed)
            speed.start()

    def stop(self) -> None:
        """Tắt vòng nền và đóng cổng TCP. Gọi nhiều lần không sao."""
        with self._lock:
            if not self._running:
                return
            self._running = False
            self._stop_event.set()
            self._announce_now.set()
            threads, self._threads = self._threads, []
            self.server.stop()
        bus.unsubscribe("file.completed", self._on_file_completed)
        atexit.unregister(self.shutdown)
        for t in threads:  # đợi ngoài khóa vì hai vòng nền cũng cần khóa
            if t is not threading.current_thread():
                t.join(timeout=2.0)
        logger.i("TorrentManager stopped")

    def shutdown(self) -> None:
        """Đóng ứng dụng: dừng tải, báo tracker "stopped" cho mọi task, rồi stop().

        Báo tracker chờ tối đa vài giây. Tự chạy khi thoát chương trình.
        """
        if not self._running:
            return
        tasks = self.get_all_tasks()
        for task in tasks:
            if task.downloader is not None:
                task.downloader.stop()
        self.stop()
        self._announce_stopped(tasks)

    # --- Tạo / thêm task ---
    def create_and_seed(
        self,
        file_path: str,
        piece_size: int = DEFAULT_PIECE_SIZE,
        output_meta_path: Optional[str] = None,
    ) -> TorrentTask:
        """Chia sẻ một file của mình: tạo .ptorrent, báo tracker, bắt đầu seed.

        Nếu file đã có trong danh sách thì trả về task cũ.
        Ném FileNotFoundError nếu không có file, ValueError nếu piece_size <= 0.
        """
        if piece_size <= 0:
            raise ValueError("piece_size phải lớn hơn 0")
        file_path = os.path.abspath(file_path)
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
        self._ensure_started()

        metadata = Chunker().create_metadata(
            file_path, self.tracker_url + "/announce.php", piece_size)
        existing = self.get_task(metadata.file_id)
        if existing is not None:
            if output_meta_path:
                out_p = os.path.abspath(output_meta_path)
                os.makedirs(os.path.dirname(out_p), exist_ok=True)
                with open(out_p, "w", encoding="utf-8") as f:
                    json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
                existing.saved_meta_path = out_p
            return existing

        meta_path = self._save_meta(metadata)
        if output_meta_path:
            out_p = os.path.abspath(output_meta_path)
            os.makedirs(os.path.dirname(out_p), exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
            saved_path = out_p
        else:
            saved_path = meta_path

        # Tracker lỗi thì vẫn seed được (người khác thêm bằng file .ptorrent)
        if not self.tracker.register(metadata):
            logger.w(f"cannot register {metadata.file_name} on tracker, seeding anyway")

        task = self._make_task(metadata, meta_path, source_path=file_path)
        task.saved_meta_path = saved_path
        with self._lock:
            self._tasks[task.file_id] = task
        self.save_session()
        self._announce(task, "started")
        logger.i(f"seeding {metadata.file_name} ({metadata.total_pieces} pieces)")
        return task

    def add_torrent(self, meta_path: str) -> TorrentTask:
        """Thêm file từ .ptorrent và bắt đầu tải (tự resume các chunk đã có).

        Nếu file đã có trong danh sách thì trả về task cũ.
        Ném FileNotFoundError nếu không có file, ValueError nếu .ptorrent hỏng.
        """
        self._ensure_started()
        task = self._add(meta_path)
        logger.i(f"added {task.metadata.file_name}: {task.progress:.1f}% ({task.status})")
        return task

    # --- Điều khiển ---
    def pause_torrent(self, file_id: str) -> bool:
        """Dừng TẢI (PeerServer vẫn phục vụ chunk đã có). False nếu không có task."""
        task = self.get_task(file_id)
        if task is None:
            return False
        if task.downloader is not None:
            task.downloader.stop()
        self._set_status(task, "paused")
        self.save_session()
        return True

    def resume_torrent(self, file_id: str) -> bool:
        """Tiếp tục tải các chunk còn thiếu. False nếu không có task."""
        task = self.get_task(file_id)
        if task is None:
            return False
        if task.status == "paused":
            self._set_status(task, self._status_for(task))
            self.save_session()
            self._activate(task)
        return True

    def remove_torrent(self, file_id: str, delete_files: bool = False) -> bool:
        """Dừng và gỡ task, báo tracker "stopped". False nếu không có task.

        delete_files=True xóa chunk và file đã tải về. File gốc do seeder chọn
        thì KHÔNG bao giờ bị xóa.
        """
        with self._lock:
            task = self._tasks.pop(file_id, None)
        if task is None:
            return False
        if task.downloader is not None:
            task.downloader.stop()
        self.server.unregister_torrent(file_id)
        self.save_session()
        self._announce(task, "stopped")
        if delete_files:
            self._delete_task_files(task)
        self._publish("task.removed", {"file_id": file_id})
        logger.i(f"removed {task.metadata.file_name} (delete_files={delete_files})")
        return True

    # --- Danh sách task ---
    def get_all_tasks(self) -> List[TorrentTask]:
        """Trả về bản sao danh sách task."""
        with self._lock:
            return list(self._tasks.values())

    def get_task(self, file_id: str) -> Optional[TorrentTask]:
        with self._lock:
            return self._tasks.get(file_id)

    # --- Session (nhớ danh sách file giữa các lần mở app) ---
    def save_session(self) -> None:
        """Ghi danh sách task vào storage_root/session.json (ghi nguyên tử)."""
        with self._lock:
            entries = [
                {
                    "file_id": t.file_id,
                    "meta_path": t.meta_path,
                    "source_path": t.source_path,
                    "paused": t.status == "paused",
                }
                for t in self._tasks.values()
            ]
            path = os.path.join(self.storage_root, SESSION_FILE)
            tmp = path + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump({"version": 1, "torrents": entries}, f, indent=2,
                              ensure_ascii=False)
                os.replace(tmp, path)
            except OSError as e:
                logger.w(f"cannot save session: {e}")

    def load_session(self) -> List[TorrentTask]:
        """Nạp lại các file của lần mở trước. Mục nào lỗi thì bỏ qua và ghi log.

        Việc báo tracker và nối peer để vòng nền làm, nên không chờ mạng.
        """
        self._ensure_started()
        path = os.path.join(self.storage_root, SESSION_FILE)
        try:
            with open(path, "r", encoding="utf-8") as f:
                entries = json.load(f).get("torrents", [])
        except FileNotFoundError:
            return []
        except (OSError, ValueError, AttributeError) as e:
            logger.w(f"cannot read session, starting empty: {e}")
            return []

        loaded = []
        for entry in entries:
            try:
                loaded.append(self._add(
                    entry["meta_path"], source_path=entry.get("source_path"),
                    paused=bool(entry.get("paused")), background=True, save=False))
            except Exception as e:
                logger.w(f"skip session entry {entry}: {e}")
        self.save_session()
        return loaded

    # --- Nội bộ ---
    def _ensure_started(self) -> None:
        if not self._running:
            self.start()

    def _add(self, meta_path: str, source_path: Optional[str] = None,
             paused: bool = False, background: bool = False, save: bool = True) -> TorrentTask:
        """Dùng chung cho add_torrent và load_session."""
        meta_path = os.path.abspath(meta_path)
        if not os.path.isfile(meta_path):
            raise FileNotFoundError(f"Không tìm thấy file: {meta_path}")
        try:
            metadata = Metadata.from_file(meta_path)
        except Exception as e:
            raise ValueError(f"File .ptorrent không hợp lệ: {meta_path} ({e})") from e

        existing = self.get_task(metadata.file_id)
        if existing is not None:
            return existing

        stored_path = self._store_meta_copy(meta_path, metadata)
        task = self._make_task(metadata, stored_path, source_path=source_path)
        if paused:
            task.status = "paused"
        with self._lock:
            self._tasks[task.file_id] = task
        if save:
            self.save_session()
        if not paused:
            self._activate(task, background=background)
        return task

    def _make_task(self, metadata: Metadata, meta_path: str,
                   source_path: Optional[str] = None) -> TorrentTask:
        """Dựng TorrentTask và đăng ký với PeerServer (chưa tải, chưa announce)."""
        pm = PieceManager(metadata, self.storage_root, original_file_path=source_path)
        self.server.register_torrent(pm)

        task = TorrentTask(metadata=metadata, piece_manager=pm,
                           meta_path=meta_path, source_path=source_path)
        if not pm.is_complete():
            # Mất nguồn thì đánh thức vòng announce để tìm nguồn mới
            # (không announce ngay vì callback chạy trên thread tải)
            task.downloader = Downloader(
                self.peer_id,
                pm,
                on_source_lost_callback=self._announce_now.set,
                download_limit=self.download_limit,
            )
        task.status = self._status_for(task)
        # Mốc đo tốc độ ban đầu, để phần đã tải dở không bị tính thành tốc độ
        task.downloaded_bytes_last_sec = pm.get_downloaded_bytes()
        task.uploaded_bytes_last_sec = pm.uploaded_bytes
        return task

    @staticmethod
    def _status_for(task: TorrentTask) -> str:
        """Trạng thái đúng với dữ liệu hiện có (không tính "paused")."""
        if task.piece_manager.is_complete():
            return "seeding" if task.source_path else "completed"
        return "downloading"

    def _activate(self, task: TorrentTask, background: bool = False) -> None:
        """Bắt đầu tải (nếu cần) và báo tracker "started".

        background=True: để vòng nền báo tracker và nối peer (không chờ mạng).
        """
        downloading = task.status == "downloading" and task.downloader is not None
        if downloading:
            task.downloader.start()
        if background:
            task.pending_event = "started"
            self._announce_now.set()
            return
        result = self._announce(task, "started")
        if downloading:
            task.downloader.add_peers(result.get("peers", []))

    def _set_status(self, task: TorrentTask, status: str) -> None:
        """Đổi trạng thái và báo giao diện qua bus (chỉ khi thật sự đổi)."""
        if task.status == status:
            return
        task.status = status
        self._publish("task.status", {"file_id": task.file_id, "status": status})

    @staticmethod
    def _publish(topic: str, data: dict) -> None:
        """Lỗi của người nghe không được làm hỏng Manager."""
        try:
            bus.publish(topic, data)
        except Exception as e:
            logger.e(f"bus handler for {topic} raised: {e}")

    def _on_file_completed(self, data: dict) -> None:
        """Chạy trên thread tải: chỉ đổi cờ, việc báo tracker để vòng nền làm."""
        if not isinstance(data, dict):
            return
        with self._lock:
            task = self._tasks.get(data.get("file_id"))
        # So đường dẫn để bỏ qua sự kiện của Manager khác trong cùng tiến trình
        if task is None or data.get("output_path") != task.piece_manager.completed_file_path:
            return
        task.pending_event = "completed"
        self._set_status(task, self._status_for(task))
        self._announce_now.set()

    # --- Vòng nền ---
    def _announce_loop(self, stop: threading.Event) -> None:
        """Mỗi announce_interval giây (hoặc khi bị đánh thức) báo tracker, nối peer mới."""
        while not stop.is_set():
            self._announce_now.wait(timeout=self.announce_interval)
            if stop.is_set():
                return
            self._announce_now.clear()
            try:
                self._announce_round(stop)
            except Exception as e:
                logger.e(f"announce loop error: {e}")
            stop.wait(self.announce_gap)  # tránh gọi tracker dồn dập

    def _announce_round(self, stop: Optional[threading.Event] = None) -> None:
        for task in self.get_all_tasks():
            if stop is not None and stop.is_set():
                return
            if task.status == "paused":
                continue
            event = task.pending_event
            result = self._announce(task, event)
            if event and task.pending_event == event:
                task.pending_event = ""
            try:
                interval = float(result.get("interval", 0))
                if interval > 0:
                    self.announce_interval = min(interval, MAX_ANNOUNCE_INTERVAL)
            except (TypeError, ValueError):
                pass
            if task.status == "downloading" and task.downloader is not None:
                task.downloader.add_peers(result.get("peers", []))

    def _speed_loop(self, stop: threading.Event) -> None:
        last = time.monotonic()
        while not stop.wait(self.speed_interval):
            now = time.monotonic()
            try:
                self._update_speeds(now - last)
            except Exception as e:
                logger.e(f"speed loop error: {e}")
            last = now

    def _update_speeds(self, elapsed: float) -> None:
        """Tính tốc độ (bytes/giây) từng task, rồi bắn task.speed và task.progress."""
        for task in self.get_all_tasks():
            pm = task.piece_manager
            done = pm.get_downloaded_bytes()
            sent = pm.uploaded_bytes
            if elapsed > 0:
                task.download_speed = max(0, done - task.downloaded_bytes_last_sec) / elapsed
                task.upload_speed = max(0, sent - task.uploaded_bytes_last_sec) / elapsed
            task.downloaded_bytes_last_sec = done
            task.uploaded_bytes_last_sec = sent
            self._publish("task.progress", {
                "file_id": task.file_id, "downloaded": done, "total": task.metadata.file_size})
            self._publish("task.speed", {
                "file_id": task.file_id,
                "download_speed": task.download_speed,
                "upload_speed": task.upload_speed})

    # --- Tracker ---
    def _announce(self, task: TorrentTask, event: str = "") -> Dict[str, Any]:
        """Báo tracker; trả về dict kết quả (có "peers"). Lỗi mạng thì "peers" rỗng."""
        pm = task.piece_manager
        try:
            result = self.tracker.announce(
                file_id=task.file_id,
                peer_id=self.peer_id,
                port=self.server.port,
                uploaded=pm.uploaded_bytes,
                downloaded=pm.get_downloaded_bytes(),
                bytes_left=pm.get_bytes_left(),
                event=event,
                bitfield=pm.get_bitfield(),
                ip=self.advertise_ip,
            )
        except Exception as e:
            logger.e(f"announce failed for {task.metadata.file_name}: {e}")
            return {"interval": 15, "complete": 0, "incomplete": 0, "peers": []}
        return result if isinstance(result, dict) else {"peers": []}

    def _announce_stopped(self, tasks: List[TorrentTask], timeout: float = 3.0) -> None:
        """Báo "stopped" song song để một tracker chậm không làm treo việc thoát."""
        threads = [threading.Thread(target=self._announce, args=(t, "stopped"), daemon=True)
                   for t in tasks]
        for t in threads:
            t.start()
        deadline = time.monotonic() + timeout
        for t in threads:
            t.join(timeout=max(0.0, deadline - time.monotonic()))

    # --- File ---
    def _meta_path_for(self, metadata: Metadata) -> str:
        """Đường dẫn .ptorrent trong storage_root/torrents (tránh trùng tên)."""
        path = os.path.join(self.torrents_dir, metadata.file_name + ".ptorrent")
        if os.path.exists(path):
            try:
                if Metadata.from_file(path).file_id == metadata.file_id:
                    return path
            except Exception:
                pass
            # Cùng tên nhưng khác nội dung: thêm một đoạn của file_id
            return os.path.join(
                self.torrents_dir, f"{metadata.file_name}.{metadata.file_id[:8]}.ptorrent")
        return path

    def _save_meta(self, metadata: Metadata) -> str:
        path = self._meta_path_for(metadata)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return path

    def _store_meta_copy(self, src_path: str, metadata: Metadata) -> str:
        """Chép .ptorrent vào storage_root/torrents để không phụ thuộc đường dẫn gốc."""
        dest = self._meta_path_for(metadata)
        if os.path.abspath(src_path) != os.path.abspath(dest):
            shutil.copyfile(src_path, dest)
        return dest

    @staticmethod
    def _delete_task_files(task: TorrentTask) -> None:
        pm = task.piece_manager
        shutil.rmtree(pm.chunks_dir, ignore_errors=True)
        if task.source_path is None:  # file tải về; file gốc của seeder thì giữ nguyên
            try:
                os.remove(pm.completed_file_path)
            except OSError:
                pass

    def _load_or_create_peer_id(self) -> str:
        """Lưu peer_id vào đĩa để mỗi lần mở app vẫn là cùng một peer."""
        path = os.path.join(self.storage_root, "peer_id.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                peer_id = f.read().strip()
            if peer_id:
                return peer_id
        except OSError:
            pass

        peer_id = "PT-" + uuid.uuid4().hex[:12]
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(peer_id)
        except OSError as e:
            logger.w(f"cannot save peer_id: {e}")
        return peer_id
