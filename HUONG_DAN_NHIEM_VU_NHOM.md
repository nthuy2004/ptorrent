# HƯỚNG DẪN KỸ THUẬT & PHÂN CÔNG NHIỆM VỤ NHÓM
## DỰ ÁN: HỆ THỐNG CHIA SẺ TỆP P2P MÔ PHỎNG BITTORRENT (PTIT - DS02)
> **Dành cho:** 2 thành viên phụ trách tầng **Manager** và tầng **Giao diện (GUI PyQt6)**.  
> **Thư mục dự án:** `D:\ptit\ptorrent`  
> **Trạng thái hiện tại:** Toàn bộ phần Core Mạng (`chunker`, `protocol`, `piece_manager`, `peer_server`, `downloader`, `tracker`, `bus`) đã được hoàn thiện và kiểm thử thành công.

---

## MỤC LỤC
1. [Tổng quan Kiến trúc & Những gì Core đã làm được](#1-tổng-quan-kiến-trúc--những-gì-core-đã-làm-được)
2. [Phân công Nhiệm vụ Chi tiết cho 2 Thành viên](#2-phân-công-nhiệm-vụ-chi-tiết-cho-2-thành-viên)
   - [Nhiệm vụ 1: Thành viên phụ trách `TorrentManager` (Core Manager)](#nhiệm-vụ-1-thành-viên-phụ-trách-torrentmanager-core-manager)
   - [Nhiệm vụ 2: Thành viên phụ trách `QtEventBridge` & Giao diện PyQt6](#nhiệm-vụ-2-thành-viên-phụ-trách-qteventbridge--giao-diện-pyqt6)
3. [Hợp đồng Giao tiếp giữa Manager và GUI (Interface Contract)](#3-hợp-đồng-giao-tiếp-giữa-manager-và-gui-interface-contract)
4. [Hướng dẫn Quy trình Git chuẩn chỉnh (Push / Pull / PR / Merge)](#4-hướng-dẫn-quy-trình-git-chuẩn-chỉnh-push--pull--pr--merge)
5. [Các quy tắc cần nhớ để không bị trừ điểm BTL PTIT](#5-các-quy-tắc-cần-nhớ-để-không-bị-trừ-điểm-btl-ptit)

---

## 1. TỔNG QUAN KIẾN TRÚC & NHỮNG GÌ CORE ĐÃ LÀM ĐƯỢC

Toàn bộ hệ sinh thái của ứng dụng Client được chia thành 3 tầng:

```
+-----------------------------------------------------------------------------------+
|                        TẦNG 3: GIAO DIỆN NGƯỜI DÙNG (GUI PYQT6)                   |
|  (Bảng danh sách file, Nút bấm Tạo/Tải, Bảng ô vuông Bitfield Grid đổi màu)       |
+-----------------------------------------------------------------------------------+
                                         │  ▲
                                         │  │ (pyqtSignal an toàn đa luồng)
                                         ▼  │
+-----------------------------------------------------------------------------------+
|                        TẦNG 2: ĐIỀU PHỐI ĐA TỆP (MANAGER LAYER)                   |
|  ├── QtEventBridge: Cầu nối chuyển sự kiện từ Worker sang GUI Thread.             |
|  └── TorrentManager: Quản lý danh sách nhiều tệp, 1 cổng TCP Server, Session.     |
+-----------------------------------------------------------------------------------+
                                         │  ▲
                                         │  │ (Gọi hàm trực tiếp & EventBus Pub/Sub)
                                         ▼  │
+-----------------------------------------------------------------------------------+
|                        TẦNG 1: CÁC MODULE CORE MẠNG ĐÃ XONG                       |
|  - chunker.py: Cắt/ghép file, băm SHA-256 từng chunk, tạo metadata.               |
|  - protocol.py: Đóng gói TCP nhị phân (HANDSHAKE, BITFIELD, HAVE, REQUEST, PIECE).|
|  - piece_manager.py: Quản lý Bitfield, lưu chunk .dat, Resume khi mở app.         |
|  - peer_server.py: Mở TCP Server, phục vụ Upload, bắn HAVE thời gian thực.        |
|  - downloader.py: Worker Pool kết nối nhiều Peer, tải song song, tự xử lý Churn.  |
|  - tracker.py: Gọi HTTP REST lên Tracker (register, announce).                    |
|  - bus.py: Thư viện PyPubSub bắn sự kiện nội bộ trong app.                        |
+-----------------------------------------------------------------------------------+
```

---

## 2. PHÂN CÔNG NHIỆM VỤ CHI TIẾT CHO 2 THÀNH VIÊN

---

### NHIỆM VỤ 1: THÀNH VIÊN PHỤ TRÁCH `TorrentManager` (CORE MANAGER)

* **Mục tiêu:** Viết một lớp "Tổng quản" gom nhiều tác vụ tải/seeding vào chung 1 ứng dụng Client. Dùng chung **1 cổng TCP Server duy nhất** (chuẩn BitTorrent) và tự động ghi nhớ trạng thái các file vào đĩa cứng (`session.json`).
* **Vị trí file cần tạo:** `src/client/core/torrent_manager.py`

#### Chi tiết các việc cần làm:

1. **Tạo class `TorrentTask`:**
   Mỗi file được nạp vào hệ thống sẽ tương ứng với 1 `TorrentTask` lưu trữ:
   * `metadata`: Đối tượng `Metadata` của file.
   * `piece_manager`: Quản lý bitfield và lưu trữ chunk.
   * `downloader`: Bộ điều phối tải song song (`Downloader`).
   * `status`: Trạng thái chuỗi: `"seeding"` | `"downloading"` | `"completed"` | `"paused"`.
   * `downloaded_bytes_last_sec`, `uploaded_bytes_last_sec`: Dùng để tính tốc độ tức thời.
   * `download_speed` (bytes/s), `upload_speed` (bytes/s).

2. **Tạo class `TorrentManager`:**
   * **Quản lý cổng mạng tập trung:** Khởi động **1 đối tượng `PeerServer` duy nhất** (ví dụ mở cổng `6881`). Mọi `TorrentTask` thêm vào đều đăng ký với Server này qua `server.register_torrent(pm)`.
   * **Các phương thức cần viết:**
     * `__init__(self, storage_root: str, default_port: int = 6881, tracker_url: str = "...")`
     * `create_and_seed(self, file_path: str, piece_size: int) -> TorrentTask`:
       1. Gọi `Chunker().create_metadata(...)` sinh file `.ptorrent`.
       2. Gọi `Tracker.register(...)` báo cho Tracker PHP.
       3. Tạo `PieceManager` (chế độ seeder), nạp vào `PeerServer`.
       4. Gửi `Tracker.announce(event="started", bytes_left=0)`.
       5. Lưu task vào danh sách và gọi `self.save_session()`.
     * `add_torrent(self, meta_path: str) -> TorrentTask`:
       1. Đọc metadata qua `Metadata.from_file(meta_path)`.
       2. Tạo `PieceManager` (tự động quét Resume các chunk đã có).
       3. Nạp vào `PeerServer` (để hỗ trợ vừa tải vừa upload ngay).
       4. Tạo `Downloader`, gọi Tracker lấy danh sách Peer và bắt đầu tải.
       5. Lưu task vào danh sách và gọi `self.save_session()`.
     * `pause_torrent(self, file_id: str)`: Dừng downloader của task đó, đổi status sang `"paused"`.
     * `resume_torrent(self, file_id: str)`: Bật lại downloader, tiếp tục tải các chunk thiếu.
     * `remove_torrent(self, file_id: str, delete_files: bool = False)`: Dừng task, thông báo `announce(event="stopped")`, xóa khỏi `session.json` (nếu `delete_files=True` thì xóa cả thư mục chunk).
     * `save_session(self)`: Lưu danh sách đường dẫn file torrent đang quản lý vào `storage/session.json`.
     * `load_session(self)`: Được gọi khi mở app, tự động duyệt `session.json` nạp lại các file cũ.
     * `start_speed_calculator_loop(self)`: Chạy 1 luồng timer mỗi 1 giây tính toán tốc độ mạng (`KB/s`, `MB/s`) của từng file và bắn sự kiện lên `bus`.

---

### NHIỆM VỤ 2: THÀNH VIÊN PHỤ TRÁCH `QtEventBridge` & GIAO DIỆN PYQT6

* **Mục tiêu:** Xây dựng cầu nối Thread-safe giữa luồng mạng và luồng giao diện, đồng thời thiết kế toàn bộ màn hình desktop bằng **PyQt6** theo chuẩn giao diện BitTorrent chuyên nghiệp (uTorrent / qBittorrent).
* **Vị trí file cần tạo:**
  * `src/client/core/qt_bridge.py`: Cầu nối an toàn đa luồng.
  * `src/client/gui/piece_grid.py`: Bảng ô vuông Bitfield Grid đổi màu động.
  * `src/client/gui/main_window.py`: Cửa sổ chính, bảng danh sách file, thanh công cụ.
  * `src/client/gui/dialogs.py`: Hộp thoại Tạo Torrent và Chọn tệp.

#### Chi tiết các việc cần làm:

1. **Xây dựng `src/client/core/qt_bridge.py` (Cực kỳ quan trọng để không văng app):**
   * Kế thừa `QObject`, định nghĩa các Qt Signals:
     ```python
     from PyQt6.QtCore import QObject, pyqtSignal
     from core.bus import bus

     class QtEventBridge(QObject):
         sig_chunk_updated = pyqtSignal(str, int, str)       # (file_id, index, status)
         sig_progress_updated = pyqtSignal(str, int, int)     # (file_id, downloaded, total)
         sig_speed_updated = pyqtSignal(str, float, float)    # (file_id, dl_speed, ul_speed)
         sig_task_completed = pyqtSignal(str, str)            # (file_id, output_path)
         sig_log_message = pyqtSignal(str, str)               # (level, text)

         def __init__(self):
             super().__init__()
             # Lắng nghe từ PyPubSub và phát lại bằng pyqtSignal để về Main Thread an toàn
             bus.subscribe("chunk.downloading", lambda d: self.sig_chunk_updated.emit(d["file_id"], d["index"], "downloading"))
             bus.subscribe("chunk.completed", lambda d: self.sig_chunk_updated.emit(d["file_id"], d["index"], "completed"))
             bus.subscribe("chunk.corrupted", lambda d: self.sig_chunk_updated.emit(d["file_id"], d["index"], "corrupted"))
             bus.subscribe("file.completed", lambda d: self.sig_task_completed.emit(d["file_id"], d["output_path"]))
     ```

2. **Xây dựng Widget Bảng ô vuông Bitfield (`src/client/gui/piece_grid.py`):**
   * Hiển thị danh sách $N$ ô vuông nhỏ đại diện cho các chunk của file đang được click chọn:
     * ⬜ **Màu xám nhạt (`#e0e0e0`):** Chưa tải (Pending).
     * 🟨 **Màu vàng (`#fbc02d`):** Đang tải (Downloading).
     * 🟩 **Màu xanh lá (`#4caf50`):** Đã tải và verify SHA-256 chuẩn (Completed).
     * 🟥 **Màu đỏ (`#e53935`):** Bị hỏng mã hash (Corrupted - đang chờ tải lại).
   * Viết hàm `set_active_file(file_id, total_pieces, current_bitfield)` khi người dùng đổi tệp trên bảng danh sách.
   * Viết hàm `update_piece_status(file_id, index, status)` để đổi màu ô tương ứng khi nhận tín hiệu từ `QtEventBridge`.

3. **Xây dựng Cửa sổ chính (`src/client/gui/main_window.py`):**
   * **Thanh công cụ trên cùng:** 
     * `[ + Tạo Torrent ]`: Mở popup chọn file gốc $\rightarrow$ gọi `manager.create_and_seed()`.
     * `[ 📂 Mở Torrent ]`: Mở popup chọn file `.ptorrent` $\rightarrow$ gọi `manager.add_torrent()`.
     * `[ ▶ Tiếp tục ]`, `[ ⏸ Tạm dừng ]`, `[ ❌ Xóa ]`.
   * **Bảng danh sách Torrent (QTableWidget):**
     * Cột: `Tên tệp`, `Dung lượng`, `Tiến độ (%)`, `Tốc độ Tải`, `Tốc độ Gửi`, `Trạng thái`.
     * Khi người dùng click chọn dòng nào $\rightarrow$ Bảng Bitfield Grid bên dưới lập tức hiển thị trạng thái các chunk của file đó!
   * **Khung Log thời gian thực (dưới cùng):** Hiển thị các sự kiện bắt tay, kết nối, tải chunk.

---

## 3. HỢP ĐỒNG GIAO TIẾP GIỮA MANAGER VÀ GUI (INTERFACE CONTRACT)

Để 2 bạn có thể code độc lập cùng lúc mà không cần chờ nhau, đây là quy chuẩn kết nối giữa 2 tầng:

### A. Chiều GUI gọi xuống Manager:
Thành viên làm GUI chỉ cần gọi các hàm sau từ instance `torrent_manager`:
```python
task = torrent_manager.add_torrent(meta_file_path)
task = torrent_manager.create_and_seed(source_file_path, piece_size=256*1024)
torrent_manager.pause_torrent(file_id)
torrent_manager.resume_torrent(file_id)
torrent_manager.remove_torrent(file_id, delete_files=False)
all_tasks = torrent_manager.get_all_tasks() # Trả về danh sách để nạp vào bảng khi mở app
```

### B. Chiều Manager/Worker bắn ngược lên GUI:
Toàn bộ thông tin cập nhật sẽ được `QtEventBridge` bắt và bắn tín hiệu:
* Khi 1 chunk đổi trạng thái: `bridge.sig_chunk_updated.connect(self.piece_grid.on_chunk_update)`
* Khi tải xong 100%: `bridge.sig_task_completed.connect(self.on_download_complete)`
* Khi cập nhật tốc độ mỗi giây: `bridge.sig_speed_updated.connect(self.update_table_speed)`

---

## 4. HƯỚNG DẪN QUY TRÌNH GIT CHUẨN CHỈNH (PUSH / PULL / PR / MERGE)

*(Đề bài PTIT quy định: Mỗi thành viên phải có lịch sử commit riêng biệt, rõ ràng trên GitHub để được tính điểm cá nhân).*

### Bước 1: Cấu hình thông tin Git cá nhân trên máy của mỗi bạn
Trước khi gõ lệnh commit, mỗi bạn hãy chạy 2 lệnh sau (email phải trùng với tài khoản GitHub):
```bash
git config --global user.name "Ho Va Ten Cua Ban"
git config --global user.email "email_tai_khoan_github_cua_ban@gmail.com"
```

### Bước 2: Tạo nhánh làm việc riêng từ nhánh `develop`
* Mở terminal tại thư mục `D:\ptit\ptorrent`:
```bash
# 1. Chuyển sang nhánh develop và kéo code mới nhất về
git checkout develop
git pull origin develop

# 2. Bạn làm Manager tạo nhánh:
git checkout -b feat/torrent-manager

# HOẶC Bạn làm GUI tạo nhánh:
git checkout -b feat/gui-pyqt6
```

### Bước 3: Commit code đều đặn theo chuẩn Conventional Commits
Đừng code cả tuần mới commit 1 lần. Hãy commit sau khi làm xong từng hàm nhỏ:
* `git add src/client/core/torrent_manager.py`
* `git commit -m "feat(manager): implement add_torrent and task lifecycle"`
* `git commit -m "feat(gui): create piece grid color widget with QGridLayout"`
* `git commit -m "fix(manager): resolve file seek race condition"`

### Bước 4: Đẩy nhánh lên GitHub
```bash
git push -u origin feat/torrent-manager
# hoặc
git push -u origin feat/gui-pyqt6
```

### Bước 5: Mở Pull Request (PR) & Gộp code vào `develop`
1. Lên giao diện GitHub của nhóm, bấm **New Pull Request**.
2. Chọn gộp từ nhánh của bạn (`feat/...`) vào nhánh **`develop`** (KHÔNG merge thẳng vào `master`/`main`).
3. Gán thành viên còn lại vào mục **Reviewers** để họ duyệt code.
4. Bấm **Merge Pull Request** sau khi test không có lỗi.

### Bước 6: Cập nhật code mới từ đồng đội về máy mình
Khi đồng đội đã merge xong tính năng của họ vào `develop`:
```bash
git checkout develop
git pull origin develop
git checkout <nhanh-cua-ban>
git merge develop
```

---

## 5. CÁC QUY TẮC CẦN NHỚ ĐỂ KHÔNG BỊ TRỪ ĐIỂM BTL PTIT

1. **Tuyệt đối không đẩy file rác lên Git:** Không commit thư mục `__pycache__`, file `.dat`, file video `.mp4` dung lượng lớn. File `.gitignore` đã chặn sẵn, đừng dùng lệnh ép `git add -f`.
2. **Không sửa các hàm cốt lõi đã chạy ổn định:** Các module `chunker.py`, `protocol.py`, `peer_server.py`, `downloader.py` đã pass toàn bộ bài test mạng socket. Chỉ gọi hàm của chúng, không sửa đổi logic socket nếu không thật sự cần thiết.
3. **Phải luôn test trước khi nộp:** 
   * Bạn làm Manager hãy viết 1 file test nhỏ `test_manager.py` chạy trên console trước xem thêm/tải 2 file cùng lúc có mượt không.
   * Bạn làm GUI hãy chạy thử giao diện riêng lẻ xem đổi màu ô vuông có giật lag không.
   * Khi cả 2 ráp lại với nhau sẽ chạy cực kỳ mượt mà!