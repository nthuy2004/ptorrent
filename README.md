# HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG (PTIT)
## KHOA CÔNG NGHỆ THÔNG TIN
### BÀI TẬP LỚN MÔN HỌC: HỆ THỐNG PHÂN TÁN (DISTRIBUTED SYSTEMS)

---

# ĐỀ TÀI: HỆ THỐNG CHIA SẺ TỆP NGANG HÀNG MÔ PHỎNG BITTORRENT (pTorrent)
### (P2P FILE-SHARING SYSTEM SIMULATING BITTORRENT)

- Kho mã nguồn: https://github.com/nthuy2004/ptorrent
- Phiên bản: v1.0.0
- Năm học: 2026 - 2027

---

## 1. THÔNG TIN NHÓM VÀ PHÂN CÔNG NHIỆM VỤ

Mỗi thành viên trong nhóm phụ trách một mảng kiến trúc cốt lõi của hệ thống và phối hợp liên tục qua kho mã nguồn GitHub:

| STT | Họ và tên | Mã sinh viên | Vai trò | Nhiệm vụ chính và Đóng góp |
|:---:|:---|:---:|:---|:---|
| 1 | Nguyễn Tiến Huy (Nhóm trưởng) | B23DCVT213 | Core Network & Tracker Lead | - Khởi tạo kiến trúc base source và tài liệu kỹ thuật.<br>- Giao thức mạng TCP nhị phân (protocol.py).<br>- Module Chunker (chia/ghép tệp, SHA-256) và PieceManager.<br>- Tracker backend (PHP, MySQL) và Tracker client.<br>- Quản lý tích hợp Git, review PR và điều phối merge code. |
| 2 | Lê Đăng Khoa | B23DCVT236 | Concurrency & Manager Lead | - Xây dựng lớp điều phối đa tệp TorrentManager và TorrentTask.<br>- Quản lý vòng đời tác vụ (create, add, pause, resume, remove).<br>- Cơ chế Session Persistence (session.json) phục vụ tính năng Resume.<br>- Cơ chế đo lường băng thông (Speed Loop) và giới hạn tốc độ (Rate Limiter).<br>- Viết bộ kiểm thử tự động cho TorrentManager và luồng xử lý lỗi. |
| 3 | Nguyễn Hữu Tuấn Minh | B23DCVT279 | Desktop GUI & Integration Lead | - Cầu nối sự kiện đa luồng QtEventBridge (PyPubSub -> Qt Signals).<br>- Widget PieceGrid trực quan hóa ma trận Bitfield bằng QPainter.<br>- Cửa sổ chính MainWindow tích hợp QThreadPool xử lý bất đồng bộ.<br>- Hộp thoại CreateTorrentDialog, OpenTorrentDialog, thanh trạng thái và tiến độ.<br>- Viết bộ kiểm thử giao diện người dùng và kiểm thử tích hợp. |

---

## 2. TỔNG QUAN KIẾN TRÚC HỆ THỐNG

Hệ thống được thiết kế theo mô hình lai (Hybrid P2P Architecture) gồm 2 thành phần độc lập:

1. **Tracker Server (PHP + MySQL):**
   - Đóng vai trò là sổ danh bạ trung tâm (Central Registry / Swarm Coordinator).
   - Tiếp nhận thông tin đăng ký tệp và theo dõi trạng thái các Peer (heartbeat/announce).
   - Chỉ quản lý danh bạ IP:Port và metadata, hoàn toàn không lưu trữ hay chuyển tiếp dữ liệu tệp tin.

2. **Peer Node Client (Python 3 + PyQt6):**
   - Hoạt động song song với tư cách TCP Server (lắng nghe yêu cầu tải lên) và TCP Client (kết nối tải về từ nhiều nguồn).
   - Tích hợp giao diện đồ họa Desktop GUI trực quan, theo dõi tiến độ từng mảnh dữ liệu (Piece Grid) theo thời gian thực.

```
                 +---------------------------------------------+
                 |            TRACKER SERVER (PHP/MySQL)       |
                 |     (Chỉ điều phối danh bạ, không giữ tệp)  |
                 +---------------------------------------------+
                           ^                         ^
            POST /register |                         | GET /announce
            POST /announce |                         |
                           v                         v
        +-------------------------+         +-------------------------+
        |   PEER A (SEEDER 100%)  |         |  PEER B (LEECHER -> 50%)|
        | - PeerServer (Port 6881)|<=======>| - PeerServer (Port 6882)|
        | - PieceManager (Seeding)|   TCP   | - Downloader (Worker)   |
        +-------------------------+  Socket +-------------------------+
                    ^                                   ^
                    |          Direct P2P Transfer      |
                    +-----------------+-----------------+
                                      |
                                      v
                         +-------------------------+
                         |  PEER C (LEECHER -> 20%)|
                         | - Downloader (Parallel) |
                         | - Tải từ cả A và B      |
                         +-------------------------+
```

---

## 3. CÁC TÍNH NĂNG VÀ CƠ CHẾ PHÂN TÁN CỐT LÕI

- **Phân mảnh dữ liệu và băm SHA-256 (Chunking & Hashing):** Tệp được chia thành các mảnh cố định (16 KiB - 2048 KiB). Mỗi mảnh được băm SHA-256 độc lập và toàn bộ tệp được định danh bằng một mã băm đại diện (file_id).
- **Vừa tải vừa chia sẻ (Upload while Downloading):** Ngay khi một mảnh dữ liệu được tải về và xác thực tính toàn vẹn thành công, Peer lập tức mở cổng upload mảnh đó để phục vụ các peer khác trong mạng.
- **Tải song song đa nguồn (Parallel Downloading):** Downloader sử dụng Worker Pool để kết nối đồng thời tới nhiều peer, yêu cầu các mảnh dữ liệu khác nhau song song nhằm tối ưu hóa băng thông.
- **Xác thực toàn vẹn từng mảnh (Piece Integrity Verification):** Mọi mảnh nhận về đều được tính lại mã băm SHA-256. Nếu phát hiện sai lệch (Corrupted Chunk), mảnh đó bị hủy bỏ và tự động xếp hàng tải lại từ peer khác.
- **Khả năng chịu lỗi và thích ứng biến động mạng (Fault Tolerance & Churn Handling):** Khi một Peer nguồn ngắt kết nối đột ngột hoặc quá thời gian chờ (Socket Timeout), mảnh dữ liệu đang tải dở sẽ được đưa trở lại hàng đợi và chuyển tiếp sang peer còn hoạt động.
- **Lưu phiên làm việc và tiếp tục tải (Session Persistence & Resume):** Trạng thái các tác vụ được lưu vào tệp session.json. Khi khởi động lại, ứng dụng tự quét các chunk .dat trên đĩa và chỉ tải tiếp những phần còn thiếu mà không phải tải lại từ đầu.
- **Giao diện đa luồng an toàn (Thread-safe GUI):** Toàn bộ thao tác I/O đọc ghi đĩa và truyền nhận mạng được tách biệt trên các luồng nền thông qua QThreadPool và cơ chế lắng nghe sự kiện EventBus (PyPubSub), đảm bảo giao diện luôn mượt mà.
- **Điều tiết tốc độ và giả lập lỗi (Rate Limiter & Fault Injection):** Hỗ trợ giới hạn tốc độ truyền tải (Token Bucket) và giả lập tỷ lệ lỗi đường truyền nhằm kiểm nghiệm độ tin cậy của thuật toán tự phục hồi.

---

## 4. CẤU TRÚC THƯ MỤC DỰ ÁN

```
ptorrent/
|-- README.md                     # Tài liệu tổng quan, kiến trúc, phân công và hướng dẫn sử dụng
|-- requirements.txt              # Danh sách thư viện Python phụ thuộc
|-- .env.example                  # Mẫu biến môi trường cấu hình hệ thống
|-- deploy/                       # Cấu hình đóng gói và triển khai Tracker (Docker, SQL schema)
|   |-- Dockerfile
|   |-- docker-compose.yml
|   |-- schema.sql
|   +-- README.md
|-- docs/                         # Báo cáo kỹ thuật và slide thuyết trình
|-- scripts/                      # Script hỗ trợ sinh tệp kiểm thử, chạy nhanh demo và kiểm tra lỗi
|   |-- generate_sample.py
|   |-- run_demo_3peers.ps1
|   |-- run_demo_3peers.bat
|   |-- fault_injection_corrupt_chunk.py
|   +-- demo_fault_scenarios.py
|-- tests/                        # Bộ kiểm thử tự động (pytest)
|   |-- test_chunker.py           # Kiểm thử chia mảnh, băm SHA-256 và ghép tệp
|   |-- test_manager.py           # Kiểm thử TorrentManager và vòng đời TorrentTask
|   |-- test_gui_main_window.py   # Kiểm thử giao diện danh sách tác vụ MainWindow
|   |-- test_piece_grid.py        # Kiểm thử widget ma trận mảnh PieceGrid
|   |-- test_qt_bridge.py         # Kiểm thử cầu nối tín hiệu giữa các luồng
|   |-- test_peer_server.py       # Kiểm thử TCP PeerServer
|   |-- test_fault_recovery.py    # Kiểm thử cơ chế phát hiện chunk lỗi và tự tải lại
|   +-- test_rate_limiter_and_fault.py # Kiểm thử giới hạn băng thông và cơ chế mô phỏng lỗi
+-- src/
    |-- tracker/                  # Backend Tracker Server (PHP + MySQL)
    |   |-- database.php          # Kết nối PDO tới MySQL
    |   |-- db.php                # Tiện ích xử lý truy vấn và phản hồi JSON
    |   |-- register.php          # API đăng ký thông tin tệp từ Seeder
    |   +-- announce.php          # API điểm danh heartbeat và trả về danh sách Peer
    +-- client/                   # Mã nguồn ứng dụng Client (Python 3 + PyQt6)
        |-- main.py               # Điểm khởi chạy ứng dụng Desktop GUI
        |-- config.py             # Cấu hình mặc định và quản lý tham số hệ thống
        |-- core/                 # Khối xử lý mạng và truyền nhận dữ liệu
        |   |-- bus.py            # EventBus nội bộ ứng dụng sử dụng PyPubSub
        |   |-- chunker.py        # Module băm SHA-256, đọc ghi và phân mảnh tệp
        |   |-- protocol.py       # Giao thức đóng gói bản tin nhị phân TCP
        |   |-- piece_manager.py  # Quản lý bitfield, lưu trữ chunk và hỗ trợ resume
        |   |-- peer_server.py    # TCP Server lắng nghe yêu cầu upload từ peer khác
        |   |-- downloader.py     # Worker Pool tải song song và xử lý ngắt kết nối
        |   |-- tracker.py        # HTTP Client giao tiếp với Tracker API
        |   |-- torrent_manager.py# Bộ điều phối trung tâm các tác vụ tải và chia sẻ
        |   |-- rate_limiter.py   # Thuật toán Token Bucket kiểm soát băng thông
        |   +-- qt_bridge.py      # Chuyển đổi sự kiện EventBus sang PyQt6 Signals
        |-- gui/                  # Giao diện người dùng Desktop PyQt6
        |   |-- app.py            # Khởi động ứng dụng QApplication và nạp cấu hình
        |   |-- main_window.py    # Cửa sổ chính, thanh công cụ, bảng tác vụ và log
        |   |-- piece_grid.py     # Widget vẽ ma trận màu trực quan hóa Bitfield (QPainter)
        |   +-- dialogs.py        # Các hộp thoại tạo tệp torrent và mở tệp chia sẻ
        +-- utils/
            +-- log.py            # Hệ thống ghi log console màu
```

---

## 5. YÊU CẦU HỆ THỐNG VÀ CÀI ĐẶT

### 5.1. Yêu cầu môi trường
- Hệ điều hành: Windows 10/11, Linux, macOS.
- Python: Phiên bản >= 3.10.
- Tracker Server:
  - Tùy chọn 1 (Trực tuyến): Sử dụng Tracker có sẵn tại: `https://tracker.nth.id.vn`
  - Tùy chọn 2 (Cục bộ): PHP 8.x + MySQL (triển khai qua Docker Compose trong thư mục deploy/ hoặc XAMPP).

### 5.2. Cài đặt môi trường Python
Mở terminal tại thư mục gốc của dự án:

```bash
# 1. Tạo môi trường ảo (khuyến nghị)
python -m venv venv

# Kích hoạt môi trường ảo trên Windows:
venv\Scripts\activate

# Kích hoạt môi trường ảo trên Linux/macOS:
source venv/bin/activate

# 2. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

---

## 6. HƯỚNG DẪN VẬN HÀNH

### 6.1. Khởi chạy ứng dụng giao diện Desktop (PyQt6 GUI)

Chạy lệnh sau tại thư mục gốc:

```bash
python src/client/main.py
```

Các tham số dòng lệnh hỗ trợ:
- `--tracker-url`: Địa chỉ Tracker Server (mặc định: `https://tracker.nth.id.vn`).
- `--port`: Cổng TCP lắng nghe kết nối từ các Peer khác (mặc định: `6881`).
- `--storage-root`: Thư mục lưu trữ dữ liệu session và các chunk (mặc định: `~/.ptorrent`).
- `--rate-limit`: Giới hạn tốc độ tải xuống theo Byte/giây (mặc định: không giới hạn, ví dụ: `--rate-limit 524288` cho 512 KB/s).
- `--fault-rate`: Tỷ lệ giả lập hỏng chunk khi truyền nhận (từ 0.0 đến 1.0, ví dụ: `--fault-rate 0.1` cho 10%).

Ví dụ khởi chạy Peer thứ 2 trên cùng một máy tính (khác cổng và khác thư mục lưu trữ):

```bash
python src/client/main.py --port 6882 --storage-root C:\temp\peer2
```

Hoặc sử dụng script khởi động nhanh 3 Peer độc lập:
```powershell
.\scripts\run_demo_3peers.ps1
```

### 6.2. Hướng dẫn các thao tác cơ bản trên giao diện
1. **Chia sẻ tệp mới (Seeder):**
   - Nhấn nút **Create torrent** trên thanh công cụ.
   - Chọn tệp nguồn cần chia sẻ và kích thước chunk mong muốn (mặc định: 256 KiB).
   - Nhấn **OK**: Hệ thống tự động băm SHA-256, tạo tệp metadata `.ptorrent`, đăng ký lên Tracker và hiển thị 100% trên Piece Grid.
2. **Tải tệp (Leecher):**
   - Nhấn nút **Open torrent** trên thanh công cụ.
   - Chọn tệp metadata `.ptorrent` cần tải và chọn thư mục đích lưu tệp hoàn chỉnh.
   - Nhấn **Open**: Hệ thống tự động kết nối Tracker, lấy danh sách peer và tiến hành tải song song.
3. **Điều khiển tác vụ:**
   - Chọn dòng tệp trên bảng danh sách, sử dụng các nút **Pause**, **Resume**, hoặc **Remove**.

---

## 7. BỘ KIỂM THỬ TỰ ĐỘNG (AUTOMATED TESTS)

Dự án tích hợp hệ thống kiểm thử tự động toàn diện với `pytest`. Chạy toàn bộ test suite bằng lệnh:

```bash
pytest tests/ -v
```

Hệ thống kiểm thử xác nhận toàn bộ hơn 80 test cases đều vượt qua (Passed), bao gồm:
- Kiểm thử logic phân mảnh, ghép tệp và xác thực mã băm SHA-256 (test_chunker.py).
- Kiểm thử xử lý vòng đời TorrentManager, lưu trữ session, khôi phục tiến độ (test_manager.py).
- Kiểm thử giao diện người dùng, vẽ ma trận PieceGrid và cầu nối tín hiệu đa luồng (test_gui_*.py, test_qt_bridge.py).
- Kiểm thử cơ chế phát hiện chunk lỗi, hủy bỏ và tự động tải lại (test_fault_recovery.py).
- Kiểm thử bộ điều tiết băng thông Token Bucket và mô phỏng lỗi (test_rate_limiter_and_fault.py).

---

## 8. CÁC KỊCH BẢN THỰC NGHIỆM VÀ DEMO HỆ THỐNG

Dưới đây là các kịch bản kiểm thử nhằm minh họa toàn diện các đặc tính của hệ thống mạng ngang hàng:

1. **Kịch bản 1 - Tạo metadata và chia sẻ tệp ban đầu:**
   - Khởi chạy Client 1 (Seeder). Nhấn "Create torrent", chọn tệp mẫu (ví dụ video hoặc tệp nén 20 MB).
   - Kết quả: Tệp `.ptorrent` được sinh ra, Tracker Dashboard ghi nhận thông tin tệp mới, ma trận Piece Grid của Client 1 phủ màu xanh 100%.

2. **Kịch bản 2 - Tải song song từ nhiều nguồn (Parallel Downloading):**
   - Khởi chạy Seeder A (100%) và Seeder B (100%).
   - Mở Client C (Leecher). Client C kết nối đồng thời tới cả A và B, nhật ký log thể hiện các chunk được tải về song song từ cả hai địa chỉ IP:Port khác nhau.

3. **Kịch bản 3 - Vừa tải vừa chia sẻ (Upload while downloading):**
   - Seeder A nắm giữ 100% tệp. Client B bắt đầu tải từ A.
   - Khi Client B mới chỉ tải được một phần (ví dụ 25%), mở Client C tham gia tải.
   - Client B lập tức phục vụ các chunk đã xác thực cho Client C: log hiển thị `[UPLOAD] Sent piece #x to Client C` ngay khi B chưa tải xong tệp.

4. **Kịch bản 4 - Xử lý ngắt kết nối đột ngột (Fault Tolerance):**
   - Client C đang tải từ Seeder A và Client B. Chủ động tắt ứng dụng Seeder A đột ngột.
   - Client C bắt sự kiện timeout, không bị treo ứng dụng và giữ nguyên các chunk đã hoàn thành.

5. **Kịch bản 5 - Tự động chuyển đổi sang nguồn khác (Failover):**
   - Nối tiếp Kịch bản 4: Client C tự động phân bổ lại các chunk còn thiếu sang Client B để tiếp tục tiến trình tải cho đến khi đạt 100%.

6. **Kịch bản 6 - Phát hiện và tự sửa lỗi chunk hỏng (Data Corruption Handling):**
   - Mô phỏng một chunk bị sai lệch mã băm SHA-256 trên đường truyền hoặc bị can thiệp dữ liệu.
   - Ứng dụng phát hiện bất thường: cảnh báo log `CORRUPTED: Hash mismatch`, ô mảnh dữ liệu trên Piece Grid hiển thị cảnh báo đỏ, sau đó chunk được hủy và tự động tải lại từ nguồn hợp lệ thành màu xanh.

7. **Kịch bản 7 - Ghép tệp và xác thực toàn vẹn cuối cùng:**
   - Sau khi hoàn tất 100% các chunk, ứng dụng tự động lắp ghép thành tệp hoàn chỉnh tại thư mục đích.
   - So sánh mã SHA-256 của tệp đầu ra với tệp gốc ban đầu: trùng khớp tuyệt đối, nội dung tệp nguyên vẹn.
