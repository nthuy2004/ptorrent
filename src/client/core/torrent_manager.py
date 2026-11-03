"""TorrentManager: gom nhiều tác vụ tải / seed vào một ứng dụng Client."""

import os
import threading
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from client.core.chunker import Metadata
from client.core.downloader import Downloader
from client.core.peer_server import PeerServer
from client.core.piece_manager import PieceManager
from client.core.tracker import Tracker
from client.utils.log import logger

# Địa chỉ gốc của tracker (Tracker tự nối /announce.php), lấy theo main.py
DEFAULT_TRACKER_URL = "https://nth.io.vn"
DEFAULT_PORT = 6881  # cổng chuẩn BitTorrent


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
    """

    def __init__(
        self,
        storage_root: str,
        default_port: int = DEFAULT_PORT,
        tracker_url: str = DEFAULT_TRACKER_URL,
    ):
        self.storage_root = os.path.abspath(storage_root)
        self.torrents_dir = os.path.join(self.storage_root, "torrents")
        os.makedirs(self.torrents_dir, exist_ok=True)

        self.tracker_url = normalize_tracker_url(tracker_url)
        self.tracker = Tracker(self.tracker_url)

        self.peer_id = self._load_or_create_peer_id()
        self.server = PeerServer(self.peer_id, "0.0.0.0", default_port)

        # file_id -> TorrentTask; luôn giữ self._lock khi truy cập
        self._tasks: Dict[str, TorrentTask] = {}
        self._lock = threading.RLock()
        self._running = False

    # --- Bật / tắt ---
    @property
    def port(self) -> int:
        """Cổng đang dùng (sau start() là cổng thật, kể cả khi truyền 0)."""
        return self.server.port

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Mở cổng TCP. Gọi nhiều lần không sao."""
        with self._lock:
            if self._running:
                return
            self.server.start()
            self._running = True
        logger.i(f"TorrentManager started: peer_id={self.peer_id} port={self.port}")

    def stop(self) -> None:
        """Đóng cổng TCP. Gọi nhiều lần không sao."""
        with self._lock:
            if not self._running:
                return
            self.server.stop()
            self._running = False
        logger.i("TorrentManager stopped")

    # --- Danh sách task ---
    def get_all_tasks(self) -> List[TorrentTask]:
        """Trả về bản sao danh sách task."""
        with self._lock:
            return list(self._tasks.values())

    def get_task(self, file_id: str) -> Optional[TorrentTask]:
        with self._lock:
            return self._tasks.get(file_id)

    # --- Nội bộ ---
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
