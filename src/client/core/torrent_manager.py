"""TorrentManager: gom nhiều tác vụ tải / seed vào một ứng dụng Client.

Mỗi file đang được chia sẻ hoặc đang tải là một ``TorrentTask``. Module này
cũng sẽ chứa ``TorrentManager``: giữ danh sách task, dùng chung MỘT PeerServer
(một cổng TCP) cho mọi file và nhớ trạng thái vào ``session.json``.
"""

from dataclasses import dataclass
from typing import Optional

from client.core.chunker import Metadata
from client.core.downloader import Downloader
from client.core.piece_manager import PieceManager


@dataclass(eq=False)
class TorrentTask:
    """Trạng thái của MỘT file trong ứng dụng.

    ``status`` là một trong bốn chuỗi:
      "seeding"     file do mình tạo, đang chia sẻ cho người khác
      "downloading" đang tải
      "completed"   đã tải xong (vẫn tiếp tục upload cho người khác)
      "paused"      đang tạm dừng

    ``eq=False``: hai task so sánh bằng nhau chỉ khi là cùng một đối tượng,
    nên task dùng được làm khóa dict hoặc phần tử của set.
    """

    metadata: Metadata
    piece_manager: PieceManager
    downloader: Optional[Downloader] = None  # None nếu là seeder thuần
    status: str = "downloading"

    # Ba trường dưới đây không có trong hướng dẫn gốc, thêm cho các bước sau:
    meta_path: str = ""  # đường dẫn file .ptorrent (để lưu vào session.json)
    source_path: Optional[str] = None  # file gốc; chỉ có nếu là file mình tạo
    pending_event: str = ""  # sự kiện còn chờ báo tracker, ví dụ "completed"

    # Giá trị tích lũy ở lần đo trước, dùng để tính tốc độ tức thời
    downloaded_bytes_last_sec: int = 0
    uploaded_bytes_last_sec: int = 0
    download_speed: float = 0.0  # bytes/giây
    upload_speed: float = 0.0  # bytes/giây

    @property
    def file_id(self) -> str:
        return self.metadata.file_id

    @property
    def progress(self) -> float:
        """Phần trăm đã tải, từ 0.0 đến 100.0."""
        total = self.metadata.file_size
        if total <= 0:
            return 100.0 if self.piece_manager.is_complete() else 0.0
        downloaded = self.piece_manager.get_downloaded_bytes()
        return min(100.0, downloaded * 100.0 / total)
