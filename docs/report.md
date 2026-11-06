# HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG
## KHOA CÔNG NGHỆ THÔNG TIN
### BỘ MÔN MẠNG VÀ CÁC HỆ THỐNG PHÂN TÁN

---

# BÁO CÁO BÀI TẬP LỚN MÔN HỌC: HỆ THỐNG PHÂN TÁN
## ĐỀ TÀI: XÂY DỰNG HỆ THỐNG CHIA SẺ TỆP NGANG HÀNG MÔ PHỎNG BITTORRENT (pTorrent)

- Kho mã nguồn: https://github.com/nthuy2004/ptorrent
- Phiên bản phát hành: v1.0.0
- Giảng viên hướng dẫn: Bộ môn Hệ thống phân tán - Khoa CNTT
- Sinh viên thực hiện: Nhóm BTL DS02
- Năm học: 2026 - 2027

---

## MỤC LỤC TỔNG QUAN

1. Trang bìa (Cover Page)
2. Thông tin nhóm và phân công nhiệm vụ (Group Information and Task Assignment)
3. Tóm tắt đề tài (Abstract)
4. Mô tả bài toán và yêu cầu hệ thống (Problem Description and Requirements)
5. Các vấn đề hệ thống phân tán cốt lõi (Distributed-System Issues)
6. Phân tích và lựa chọn giải pháp (Analysis and Solution Selection)
7. Kiến trúc hệ thống (System Architecture)
8. Thiết kế thành phần và giao thức truyền thông (Component and Protocol Design)
9. Cơ chế định danh và phát hiện dịch vụ (Identification and Discovery)
10. Xử lý đồng thời, đồng bộ và tính nhất quán (Concurrency, Synchronization, and Consistency)
11. Khả năng chịu lỗi và phục hồi hệ thống (Fault Tolerance and Recovery)
12. An toàn và bảo mật hệ thống (Security)
13. Cài đặt chi tiết hệ thống (Implementation)
14. Kiểm thử và kết quả kiểm thử tự động (Testing and Results)
15. Đánh giá hiệu năng và thực nghiệm (Performance Evaluation)
16. Hạn chế và hướng phát triển (Limitations and Future Work)
17. Kết luận (Conclusion)
18. Tài liệu tham khảo (References)
19. Phụ lục (Appendices)

---

## 1. TRANG BÌA

- Tên cơ sở đào tạo: Học viện Công nghệ Bưu chính Viễn thông (PTIT)
- Khoa: Công nghệ Thông tin
- Bộ môn: Mạng và Hệ thống phân tán
- Tên đề tài: Xây dựng hệ thống chia sẻ tệp ngang hàng mô phỏng BitTorrent (pTorrent)
- Mã đề tài: DS02
- Thành viên thực hiện:
  1. Nguyễn Tiến Huy - Mã sinh viên: B23DCVT213 (Nhóm trưởng)
  2. Lê Đăng Khoa - Mã sinh viên: B23DCVT236
  3. Nguyễn Hữu Tuấn Minh - Mã sinh viên: B23DCVT279
- Hà Nội, Học kỳ I - Năm học 2026 - 2027

---

## 2. THÔNG TIN NHÓM VÀ PHÂN CÔNG NHIỆM VỤ

Hệ thống được phân chia theo 3 mảng kiến trúc chuyên biệt, mỗi thành viên chịu trách nhiệm chính cho một thành phần cốt lõi và tích hợp qua quy trình Gitflow:

| STT | Họ và tên | Mã sinh viên | Vai trò kiến trúc | Nhiệm vụ chi tiết và Đóng góp trên Git |
|:---:|:---|:---:|:---|:---|
| 1 | Nguyễn Tiến Huy | B23DCVT213 | Core Network & Tracker Lead | - Thiết kế kiến trúc tổng thể, tài liệu kỹ thuật và Docker deployment.<br>- Giao thức truyền thông nhị phân TCP (`protocol.py`).<br>- Module phân mảnh Chunker, băm SHA-256 và PieceManager.<br>- Backend Tracker Server (PHP + MySQL REST API) và Tracker Client.<br>- Điều phối nhánh Git, review Pull Requests và giải quyết xung đột mã nguồn. |
| 2 | Lê Đăng Khoa | B23DCVT236 | Concurrency & Manager Lead | - Xây dựng lớp quản trị đa tác vụ TorrentManager và TorrentTask.<br>- Quản lý vòng đời tác vụ tải/chia sẻ (Create, Add, Pause, Resume, Remove).<br>- Cơ chế Session Persistence (`session.json`) khôi phục tiến trình khi khởi động lại.<br>- Bộ điều tiết băng thông Token Bucket (`rate_limiter.py`) và luồng đo tốc độ mạng.<br>- Xây dựng bộ kiểm thử tự động cho TorrentManager và cơ chế xử lý lỗi. |
| 3 | Nguyễn Hữu Tuấn Minh | B23DCVT279 | Desktop GUI & Integration Lead | - Cầu nối sự kiện đa luồng QtEventBridge chuyển đổi sự kiện PyPubSub sang Qt Signals.<br>- Widget đồ họa PieceGrid trực quan hóa ma trận Bitfield bằng QPainter.<br>- Cửa sổ chính MainWindow tích hợp bảng tiến độ, thanh trạng thái và luồng QThreadPool.<br>- Xây dựng các hộp thoại CreateTorrentDialog, OpenTorrentDialog, chọn thư mục lưu trữ.<br>- Bộ kiểm thử giao diện người dùng và kiểm thử tích hợp toàn hệ thống. |

Mức độ đóng góp của cả 3 thành viên: 100% hoàn thành nhiệm vụ được giao.

---

## 3. TÓM TẮT ĐỀ TÀI (ABSTRACT)

### 3.1. Tóm tắt tiếng Việt
Đề tài nghiên cứu và xây dựng hệ thống chia sẻ tệp ngang hàng (P2P) phân tán mô phỏng nguyên lý cốt lõi của giao thức BitTorrent, mang tên **pTorrent**. Hệ thống giải quyết triệt để bài toán điểm nghẽn băng thông (bandwidth bottleneck) và điểm lỗi đơn lẻ (Single Point of Failure - SPOF) của mô hình Client-Server truyền thống khi phân phối các tệp tin dung lượng lớn. 

pTorrent áp dụng mô hình kiến trúc lai (Hybrid P2P) gồm hai thành phần tách biệt: (1) **Tracker Server** đóng vai trò sổ danh bạ trung tâm điều phối và theo dõi trạng thái Swarm thông qua giao tiếp HTTP RESTful JSON; (2) **Peer Client** là các tiến trình độc lập hoạt động đồng thời dưới vai trò TCP Server và TCP Client, có khả năng phân mảnh dữ liệu (Data Chunking), băm SHA-256 xác thực toàn vẹn từng mảnh, tải song song đa nguồn (Parallel Downloading) và lập tức chia sẻ các mảnh đã tải xong cho các peer khác (Upload while downloading). Hệ thống tích hợp giao diện Desktop đồ họa PyQt6 mượt mà nhờ cơ chế bất đồng bộ đa luồng, hỗ trợ cơ chế chịu lỗi tự động (Fault Tolerance), thích ứng biến động mạng (Churn Handling), khôi phục phiên làm việc (Session Persistence) và kiểm soát lưu lượng (Token Bucket Rate Limiting).

### 3.2. English Abstract
This project researches and implements a distributed Peer-to-Peer (P2P) file-sharing system simulating the core mechanics of the BitTorrent protocol, named **pTorrent**. The system eliminates bandwidth bottlenecks and Single Point of Failure (SPOF) risks inherent in classical centralized Client-Server architectures during large-scale file dissemination. 

pTorrent implements a Hybrid P2P architecture consisting of two distinct components: (1) a centralized **Tracker Server** providing swarm coordination and peer registry via HTTP RESTful JSON APIs; and (2) distributed **Peer Clients** executing concurrently as both TCP servers and TCP clients. The client architecture supports dynamic data chunking, per-piece SHA-256 cryptographic verification, multi-source parallel downloading, and immediate piece forwarding (upload while downloading). Equipped with a multi-threaded desktop GUI built on PyQt6, the system guarantees responsive user interactions while managing fault recovery, peer churn, session persistence, and traffic shaping via the Token Bucket rate-limiting algorithm.

---

## 4. MÔ TẢ BÀI TOÁN VÀ YÊU CẦU HỆ THỐNG

### 4.1. Bối cảnh bài toán và hạn chế của mô hình Client-Server
Trong kiến trúc Client-Server truyền thống:
- Khi số lượng máy khách tăng lên $N$, máy chủ phải chịu tải lưu lượng tải lên (Upload Bandwidth) tỷ lệ thuận với $O(N)$.
- Băng thông tải lên tại máy chủ nhanh chóng cạn kiệt, dẫn đến tốc độ truyền tải giảm nghiêm trọng.
- Máy chủ là điểm lỗi duy nhất: nếu máy chủ gặp sự cố sập nguồn hoặc nghẽn mạng, toàn bộ hệ thống bị tê liệt hoàn toàn.

### 4.2. Giải pháp mạng ngang hàng (P2P)
Mô hình BitTorrent đảo ngược bài toán phân phối dữ liệu:
- Biến mỗi máy nhận dữ liệu (Leecher) thành một máy cung cấp dữ liệu (Seeder) cho mạng lưới ngay khi nhận được một phần tệp.
- Tổng băng thông tải lên của toàn hệ thống tỷ lệ thuận với số lượng nút tham gia ($O(N)$), biến số lượng người tải đông đảo thành nguồn tài nguyên thay vì gánh nặng.

### 4.3. Yêu cầu chức năng
1. **Quản lý metadata**: Đọc tệp nguồn, chia thành các mảnh cố định (16 KiB - 2048 KiB), tính mã băm SHA-256 từng mảnh và mã băm toàn tệp, sinh tệp đặc tả `.ptorrent`.
2. **Điểm danh Swarm (Peer Discovery)**: Peer đăng ký và gửi heartbeat định kỳ tới Tracker Server; Tracker lưu trữ danh bạ IP:Port và phản hồi danh sách nút lân cận.
3. **Truyền nhận dữ liệu song song**: Kết nối đồng thời tới tối thiểu 2 peer để tải các mảnh khác nhau theo cơ chế Worker Pool.
4. **Chia sẻ tức thời (Upload while downloading)**: Cung cấp ngay lập tức các mảnh dữ liệu đã kiểm tra toàn vẹn cho các peer khác mà không cần đợi tải xong toàn bộ tệp.
5. **Kiểm tra tính toàn vẹn (Integrity Verification)**: Tính lại SHA-256 cho từng mảnh nhận được trước khi lưu trữ xuống đĩa; phát hiện và loại bỏ mảnh dữ liệu bị hỏng.
6. **Ghép tệp hoàn chỉnh**: Lắp ghép chính xác thứ tự các mảnh thành tệp gốc và kiểm tra mã băm cuối cùng.

### 4.4. Yêu cầu phi chức năng
1. **Tính độc lập của tiến trình**: Các Peer chạy trên các tiến trình/máy tính độc lập, giao tiếp hoàn toàn qua socket mạng TCP, không dùng chung bộ nhớ hoặc biến toàn cục.
2. **Khả năng chịu lỗi (Fault Tolerance)**: Tự động phát hiện khi peer nguồn bị ngắt kết nối đột ngột hoặc gửi mảnh sai mã băm, chuyển giao tác vụ sang peer khác mà không làm sập ứng dụng.
3. **Tính bền vững của phiên (Session Persistence)**: Lưu tiến trình tải vào tệp cấu hình; tự động quét các mảnh đã có trên đĩa để tiếp tục tải (Resume) khi ứng dụng khởi động lại.
4. **Giao diện người dùng mượt mà (Responsive GUI)**: Thao tác mạng và I/O đĩa chạy trên luồng nền, không gây treo giao diện (Not Responding).
5. **Điều tiết lưu lượng (Traffic Shaping)**: Hỗ trợ khống chế tốc độ truyền tải theo thuật toán Token Bucket.

---

## 5. CÁC VẤN ĐỀ HỆ THỐNG PHÂN TÁN CỐT LÕI

Dự án hiện thực hóa các nguyên lý cơ bản của Hệ thống phân tán:

1. **Định danh và Đánh địa chỉ (Naming and Addressing)**:
   - Mỗi nút được gán một định danh ngẫu nhiên `peer_id` (ví dụ `PEER_<12 hex chars>`).
   - Mỗi tệp được định danh duy nhất trong toàn hệ thống bằng chuỗi `file_id` sinh ra từ mã băm SHA-256 của nội dung tệp gốc.
   - Địa chỉ mạng được biểu diễn theo cặp `(IP, Port)`.

2. **Khám phá dịch vụ (Service & Peer Discovery)**:
   - Cơ chế tập trung hóa danh bạ thông qua Tracker Server.
   - Giao thức định danh phi tập trung dựa trên thông điệp `Bitfield` và `Have` giữa các nút ngang hàng.

3. **Truyền thông liên tiến trình (Inter-Process Communication - IPC)**:
   - Giao thức tầng ứng dụng trên nền TCP Socket truyền tải dòng byte nhị phân được đóng gói với độ dài cố định ở tiêu đề (Framing protocol).
   - Tương tác với Tracker bằng giao thức phi trạng thái HTTP POST RESTful API với tải trọng JSON.

4. **Đồng thời và Bất đồng bộ (Concurrency & Asynchrony)**:
   - Xử lý đồng thời đa luồng (Multi-threading) để phục vụ song song nhiều kết nối TCP đến và đi.
   - Cơ chế Worker Pool và Priority Queue điều phối các mảnh dữ liệu tải về.

5. **Nhất quán dữ liệu (Data Consistency)**:
   - Mô hình nhất quán mạnh (Strong Consistency) cho từng mảnh dữ liệu dựa trên hàm băm mật mã học một chiều SHA-256.
   - Loại trừ hoàn toàn hiện tượng dữ liệu rác hoặc dữ liệu giả mạo xâm nhập vào tệp đích.

6. **Chịu lỗi và Thích ứng biến động (Fault Tolerance & Churn)**:
   - Mô hình lỗi Crash-stop và Transient Network Failure: Phát hiện nút rời mạng qua cơ chế Socket Timeout và Heartbeat Lease.
   - Cơ chế Retry có giới hạn và Failover linh hoạt giữa các nút trong Swarm.

---

## 6. PHÂN TÍCH VÀ LỰA CHỌN GIẢI PHÁP

### 6.1. So sánh mô hình kiến trúc

| Tiêu chí | Client - Server | Pure P2P (Gnutella/DHT) | Hybrid P2P (BitTorrent) |
|:---|:---|:---|:---|
| **Cơ chế danh bạ** | Máy chủ tập trung toàn bộ | Tìm kiếm lan truyền hoặc bảng băm phân tán | Tracker Server quản lý danh bạ Swarm |
| **Lưu trữ dữ liệu** | Duy nhất trên máy chủ | Phân tán trên toàn bộ các nút | Phân tán trên toàn bộ các nút |
| **Độ phức tạp cài đặt** | Thấp | Rất cao | Trung bình - Cao |
| **Nguy cơ SPOF** | Rất cao (Sập server là dừng) | Không có | Thấp đối với dữ liệu (Tracker sập thì Swarm đã kết nối vẫn hoạt động) |
| **Hiệu năng truyền tải** | Nghẽn tại Server | Khó tối ưu tốc độ | Tối ưu hóa cực cao nhờ chia nhỏ dữ liệu |

**Quyết định lựa chọn**: Áp dụng mô hình **Hybrid P2P**. Tracker chỉ lưu danh bạ và metadata, không truyền tải tệp. Dữ liệu tệp được chuyển giao trực tiếp $100\%$ giữa các Peer qua kết nối TCP song song.

### 6.2. Lựa chọn công nghệ
- **Peer Client**: Ngôn ngữ **Python 3.10+**.
  - Xử lý socket mạng cấp thấp bằng thư viện chuẩn `socket` và `threading`.
  - Giao diện đồ họa bằng **PyQt6**: Cung cấp widget vẽ ma trận pixel tùy biến tốc độ cao (`QPainter`) và điều phối luồng chuyên nghiệp (`QThreadPool`, `QRunnable`).
  - Giao tiếp nội bộ hướng sự kiện (In-App EventBus) bằng `PyPubSub`.
- **Tracker Server**: Ngôn ngữ **PHP 8.x** kết hợp cơ sở dữ liệu **MySQL**.
  - Triển khai nhanh, nhẹ, cung cấp chuẩn API REST/JSON.
  - Hỗ trợ triển khai container hóa qua **Docker** và **Docker Compose**.

---

## 7. KIẾN TRÚC HỆ THỐNG

### 7.1. Sơ đồ kiến trúc tổng thể

```
                           +-----------------------------------+
                           |      TRACKER SERVER (PHP/MySQL)   |
                           |   (Registry / Swarm Coordination) |
                           +-----------------------------------+
                                     ^               ^
                    POST /register   |               | POST /announce
                    POST /announce   |               | (Heartbeat)
                                     v               v
                +-------------------------+     +-------------------------+
                |   PEER 1 (SEEDER 100%)  |     |  PEER 2 (LEECHER 50%)   |
                | - PeerServer (TCP:6881) |<===>| - PeerServer (TCP:6882) |
                | - PieceManager (100%)   | TCP | - Downloader Pool       |
                +-------------------------+     +-------------------------+
                             ^                               ^
                              \                             /
                   Direct P2P  \                           / Direct P2P
                   TCP Transfer \                         /  TCP Transfer
                                 v                       v
                              +-----------------------------+
                              |    PEER 3 (LEECHER 20%)     |
                              | - PeerServer (TCP:6883)     |
                              | - Downloader (Parallel Req) |
                              | - Tải song song từ Peer 1&2 |
                              +-----------------------------+
```

### 7.2. Luồng tương tác của hệ thống
1. **Giai đoạn khởi tạo tệp (Seeding Phase)**:
   - Peer 1 nạp tệp gốc, module Chunker chia tệp và tính SHA-256 các mảnh, tạo tệp metadata `.ptorrent`.
   - Peer 1 gửi yêu cầu `POST /register.php` để công bố tệp lên Tracker, sau đó gửi `POST /announce.php` đăng ký địa chỉ IP:Port của mình với vai trò Seeder.
2. **Giai đoạn tham gia Swarm (Swarm Joining)**:
   - Peer 2 mở tệp `.ptorrent`, gửi `POST /announce.php` lên Tracker với trạng thái `started` và số byte còn lại (`bytes_left`).
   - Tracker trả về danh sách các peer đang có trong mạng (gồm Peer 1).
3. **Giai đoạn bắt tay và đồng bộ Bitfield (Handshake & State Sync)**:
   - Peer 2 mở socket TCP kết nối tới Peer 1.
   - Hai bên trao đổi thông điệp `HANDSHAKE` kèm `file_id` và `peer_id`.
   - Peer 1 gửi thông điệp `BITFIELD` chứa mảng bit thể hiện các mảnh mình đang sở hữu.
4. **Giai đoạn tải dữ liệu song song (Parallel Data Exchange)**:
   - Downloader của Peer 2 phân chia các mảnh còn thiếu và gửi thông điệp `REQUEST` tới Peer 1 (và Peer 3 nếu có).
   - Peer 1 nhận yêu cầu, đọc chunk từ đĩa và phản hồi bằng thông điệp `PIECE`.
   - Peer 2 nhận dòng byte, kiểm tra mã băm SHA-256. Nếu hợp lệ, ghi vào đĩa, đánh dấu bit 1 trên Bitfield và phát sóng thông điệp `HAVE` tới toàn bộ các kết nối khác.

---

## 8. THIẾT KẾ THÀNH PHẦN VÀ GIAO THỨC TRUYỀN THÔNG

### 8.1. Cấu trúc tệp đặc tả siêu dữ liệu (.ptorrent Metadata)
Định dạng JSON chuẩn UTF-8 chứa đầy đủ thông tin để định danh và tái tạo tệp:

```json
{
  "file_id": "9a0f3d61a2c5b4e897...",
  "file_name": "sample_video.mp4",
  "file_size": 20971520,
  "piece_size": 262144,
  "total_pieces": 80,
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "piece_hashes": [
    "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
    "f63ba396ad62f0f4a0889132be0f588c2b7e5628aa410d0fb92f70b77bdfd9fb"
  ],
  "tracker_url": "https://tracker.nth.id.vn"
}
```

### 8.2. Thiết kế giao thức nhị phân TCP ngang hàng (pTorrent Wire Protocol)

Nhằm đảm bảo hiệu năng cao và phân tách rõ ràng ranh giới thông điệp trên dòng byte liên tục của TCP (TCP Stream Framing), hệ thống sử dụng cấu trúc Header cố định 5 bytes:

```
+-------------------+-------------------+-----------------------------------+
|  Length (4 Bytes) | Msg Type (1 Byte) |         Payload (N Bytes)         |
|   Big-Endian uint |     uint8 (0-6)   |  (N = Length - 1, optional)       |
+-------------------+-------------------+-----------------------------------+
```

Chi tiết các loại thông điệp:

| Msg Type ID | Tên thông điệp | Mô tả chi tiết | Cấu trúc Payload |
|:---:|:---|:---|:---|
| **0** | `MSG_HANDSHAKE` | Bắt tay kết nối ban đầu giữa 2 peer | JSON chuỗi mã hóa UTF-8 chứa `{"file_id": ..., "peer_id": ...}` |
| **1** | `MSG_HANDSHAKE_OK` | Xác nhận bắt tay thành công | Tương tự thông điệp 0, báo hiệu chấp nhận trao đổi dữ liệu |
| **2** | `MSG_BITFIELD` | Gửi trạng thái toàn bộ các mảnh đang sở hữu | Mảng JSON các giá trị nhị phân `[1, 0, 1, 1, ...]` |
| **3** | `MSG_HAVE` | Báo tin vừa tải xong một mảnh mới | 4 bytes Big-Endian `uint32`: Chỉ số mảnh (`piece_index`) |
| **4** | `MSG_REQUEST` | Yêu cầu một mảnh dữ liệu cụ thể | 4 bytes Big-Endian `uint32`: Chỉ số mảnh cần tải |
| **5** | `MSG_PIECE` | Phản hồi dữ liệu mảnh | 4 bytes `piece_index` + Khối dữ liệu nhị phân (Binary Chunk Data) |
| **6** | `MSG_ERROR` | Thông báo lỗi nghiệp vụ | Chuỗi ký tự UTF-8 mô tả chi tiết lỗi phát sinh |

### 8.3. Thiết kế giao tiếp Tracker Server (HTTP RESTful API)

1. **API Đăng ký tệp (`POST /register.php`)**:
   - Tải trọng gửi: Metadata tệp (`file_id`, `file_name`, `file_size`, `piece_size`, `total_pieces`, `file_hash`).
   - Phản hồi: `{"status": "success", "message": "File registered successfully"}`.
2. **API Điểm danh (`POST /announce.php`)**:
   - Tải trọng gửi: `file_id`, `peer_id`, `port`, `uploaded`, `downloaded`, `bytes_left`, `event` (`started`, `completed`, `stopped`), `bitfield`.
   - Phản hồi: `{"interval": 15, "complete": 1, "incomplete": 2, "peers": [{"peer_id": "...", "ip": "127.0.0.1", "port": 6881}]}`.

---

## 9. CƠ CHẾ ĐỊNH DANH VÀ PHÁT HIỆN DỊCH VỤ

1. **Định danh tệp (`file_id`)**:
   Được sinh bằng cách băm mật mã SHA-256 toàn bộ nội dung tệp gốc. Điều này đảm bảo tính duy nhất và toàn vẹn tuyệt đối: hai tệp có nội dung khác nhau dù chỉ 1 bit cũng sẽ sinh ra `file_id` hoàn toàn khác nhau.
2. **Định danh Peer (`peer_id`)**:
   Mỗi tiến trình Client khi khởi động sẽ sinh một chuỗi ngẫu nhiên có tiền tố `PEER_` kèm 12 ký tự hex (ví dụ: `PEER_4a8f9c1b2d3e`). `peer_id` được duy trì xuyên suốt vòng đời của tiến trình để các nút khác phân biệt các kết nối.
3. **Phát hiện nút (Peer Discovery)**:
   - Định kỳ mỗi $15$ giây (hoặc giá trị `interval` do Tracker cấu hình), Client gửi bản tin Announce để duy trì sự hiện diện (Keep-Alive/Heartbeat).
   - Tracker duy trì trường thời gian `last_announce`. Nếu một peer không gửi heartbeat quá thời gian quy định ($30$ giây), Tracker sẽ đánh dấu nút đó ngoại tuyến và loại bỏ khỏi danh sách cung cấp cho các peer khác.

---

## 10. XỬ LÝ ĐỒNG THỜI, ĐỒNG BỘ VÀ TÍNH NHẤT QUÁN

### 10.1. Kiến trúc luồng phía Client (Multi-Threading Architecture)
Để đạt hiệu năng cao và giữ giao diện đồ họa không bị đơ gián đoạn, Client chia tách nhiệm vụ thành các luồng độc lập:

```
[Main GUI Thread] <--- QtEventBridge (Qt Signals) <--- In-App EventBus (PyPubSub)
         |
         +---> QThreadPool (Nhiệm vụ ngắn hạn: Tạo metadata, Băm SHA-256)
         |
         +---> PeerServer Thread (TCP Listener Socket, lắng nghe kết nối đến)
         |          |
         |          +---> ClientWorker Threads (Mỗi kết nối Upload một luồng riêng)
         |
         +---> TorrentTask Speed Loop Thread (Đo lường băng thông mỗi 1s)
         |
         +---> Downloader Worker Pool (N Luồng tải song song các chunk)
```

### 10.2. Kiểm soát xung đột đồng thời (Concurrency Control)
- **Truy cập PieceManager**: Biến bảng băm trạng thái chunk và tệp ghi dữ liệu được bảo vệ bằng khóa độc quyền `threading.Lock`. Tránh hiện tượng hai luồng cùng ghi đè một chunk hoặc đọc nhầm chunk đang ghi dở.
- **Quản lý danh sách kết nối khách (`_active_clients`)**: Thao tác thêm, xóa socket khách khi ngắt kết nối được bao bọc trong khối `with self._lock:` để loại trừ race condition.

### 10.3. Mô hình nhất quán dữ liệu (Strong Consistency)
- Dữ liệu mảnh được kiểm tra tính nhất quán thông qua hàm băm SHA-256.
- Chỉ khi hàm băm của khối dữ liệu tải về trùng khớp 100% với giá trị băm trong metadata, trạng thái của mảnh trong Bitfield mới được lật từ `0` sang `1`.
- Nhờ vậy, trạng thái của mọi nút trong Swarm luôn nhất quán: hoặc là chưa có mảnh, hoặc đã có mảnh chính xác nguyên bản.

---

## 11. KHẢ NĂNG CHỊU LỖI VÀ PHỤC HỒI HỆ THỐNG

### 11.1. Mô hình lỗi được xác định (Failure Models)
1. **Nút mạng ngắt kết nối đột ngột (Node Crash / Network Disconnect)**: Một Seeder hoặc Peer đang truyền dữ liệu bị mất kết nối Internet hoặc bị tắt tiến trình đột ngột.
2. **Dữ liệu bị sai lệch trên đường truyền (Corrupted Chunk / Data Tampering)**: Gói tin bị lỗi bit do đường truyền mạng hoặc cố tình bị chỉnh sửa làm sai mã băm SHA-256.
3. **Quá thời gian chờ (Socket Timeout)**: Peer phản hồi quá chậm do nghẽn băng thông.

### 11.2. Cơ chế xử lý và tự phục hồi (Fault Recovery Mechanisms)
1. **Cơ chế Timeout và Chuyển giao nguồn tải (Failover)**:
   - Các socket truyền dữ liệu được thiết lập thời gian chờ (`socket.settimeout(10)`).
   - Khi xảy ra ngoại lệ `socket.timeout` hoặc mất kết nối (`ConnectionResetError`), luồng Worker của Downloader sẽ giải phóng kết nối đó, đưa chỉ số mảnh (`piece_index`) đang tải dở trở lại hàng đợi ưu tiên và điều phối sang một Peer khác trong Swarm để tải lại.
2. **Cơ chế phát hiện và tải lại mảnh lỗi (Corruption Handling)**:
   - Khi một mảnh tải về có mã băm sai lệch so với metadata:
     - Ứng dụng lập tức phát tín hiệu cảnh báo qua EventBus: `chunk.corrupted`.
     - Trên giao diện: ô tương ứng trên ma trận PieceGrid chuyển sang màu **ĐỎ**.
     - Dữ liệu lỗi bị hủy ngay tại bộ đệm bộ nhớ, không ghi xuống đĩa.
     - Mảnh được đánh dấu cần tải lại và gán cho một peer khác. Khi tải lại thành công và kiểm tra hash chuẩn, ô trên giao diện chuyển thành màu **XANH**.
3. **Lưu phiên làm việc và Khôi phục tải tiếp (Session Persistence & Resume)**:
   - Trạng thái các tác vụ torrent được ghi định kỳ vào tệp `session.json`.
   - Các mảnh tải hoàn tất được lưu trữ thành các tệp nhị phân riêng biệt: `<storage_root>/chunks/<file_id>/piece_<index>.dat`.
   - Khi người dùng tắt ứng dụng và bật lại, `PieceManager` duyệt thư mục, xác minh lại mã băm của các chunk `.dat` có sẵn trên đĩa và tái lập Bitfield. Ứng dụng chỉ tải tiếp các mảnh còn thiếu mà không phải tải lại từ đầu.

---

## 12. AN TOÀN VÀ BẢO MẬT HỆ THỐNG

1. **Xác thực toàn vẹn bằng hàm băm mật mã**: Việc kết hợp SHA-256 cho từng mảnh và toàn tệp giúp chống lại các cuộc tấn công thay đổi nội dung tệp (Man-in-the-Middle) và lỗi bit vật lý.
2. **Chống tấn công tràn bộ nhớ (Buffer Overflow / Denial of Service)**:
   - Giao thức quy định giới hạn độ dài thông điệp tối đa: `MAX_BUF_LEN = 10 * 1024 * 1024` (10 MB).
   - Nếu nhận được trường độ dài vượt quá giới hạn trên tiêu đề, socket lập tức ngắt kết nối để ngăn chặn kẻ tấn công gửi gói tin độc hại làm cạn kiệt RAM.
3. **Bảo mật cấu hình qua biến môi trường**: Toàn bộ tham số cấu hình nhạy cảm (như kết nối MySQL của Tracker) được nạp qua biến môi trường thông qua tệp `.env` (mẫu tệp `.env.example`), không bao giờ lưu trữ mật khẩu trực tiếp trong mã nguồn Git.

---

## 13. CÀI ĐẶT CHI TIẾT HỆ THỐNG

### 13.1. Các lớp đối tượng cốt lõi phía Client
1. **`Chunker` (`src/client/core/chunker.py`)**:
   - Chịu trách nhiệm đọc tệp nguồn theo từng khối nhị phân, tính toán mảng `piece_hashes` và `file_hash`, đóng gói thành đối tượng `Metadata` và xuất tệp `.ptorrent`.
   - Cung cấp hàm `merge_pieces` lắp ghép các mảnh `.dat` theo đúng thứ tự thành tệp hoàn chỉnh và kiểm tra mã băm cuối cùng.
2. **`Protocol` (`src/client/core/protocol.py`)**:
   - Cung cấp các phương thức tĩnh phục vụ việc đóng gói nhị phân (pack) và giải mã (unpack) 7 loại thông điệp chuẩn của giao thức pTorrent.
3. **`PieceManager` (`src/client/core/piece_manager.py`)**:
   - Quản lý mảng Bitfield thể hiện tiến độ.
   - Quản lý ghi và đọc các khối dữ liệu chunk từ đĩa cứng. Hỗ trợ xác thực SHA-256 tức thời khi nhận mảnh mới.
4. **`PeerServer` (`src/client/core/peer_server.py`)**:
   - TCP Server đa luồng lắng nghe tại cổng được chỉ định (mặc định 6881), tiếp nhận yêu cầu từ các peer khác, xác thực bắt tay và phục vụ các yêu cầu tải lên mảnh dữ liệu.
5. **`Downloader` (`src/client/core/downloader.py`)**:
   - Điều phối nhóm công nhân (Worker Pool) kết nối tới các peer từ danh sách của Tracker, lựa chọn mảnh theo chiến lược tối ưu và tải song song.
6. **`TokenBucketRateLimiter` (`src/client/core/rate_limiter.py`)**:
   - Cài đặt thuật toán Thùng thẻ bài (Token Bucket). Cho phép điều tiết và khống chế tốc độ truyền tải mượt mà không làm nghẽn CPU.
7. **`TorrentManager` (`src/client/core/torrent_manager.py`)**:
   - Bộ não điều phối tập trung mọi tác vụ `TorrentTask`, quản lý vòng đời, lắng nghe sự kiện từ EventBus và cập nhật trạng thái session.

### 13.2. Thành phần giao diện người dùng Desktop PyQt6
1. **`MainWindow` (`src/client/gui/main_window.py`)**:
   - Bảng hiển thị danh sách các tệp đang chia sẻ/tải về kèm thanh tiến độ trực tiếp (`QProgressBar`), tốc độ tải lên/tải về, số lượng peer đang kết nối và thanh trạng thái toàn cục (`QStatusBar`).
2. **`PieceGrid` (`src/client/gui/piece_grid.py`)**:
   - Widget vẽ đồ họa trực quan ma trận các mảnh dữ liệu theo thời gian thực bằng `QPainter`:
     - Màu XÁM: Mảnh chưa tải.
     - Màu XANH DƯƠNG / XANH LÁ: Mảnh đã tải xong và xác thực thành công.
     - Màu ĐỎ: Mảnh bị phát hiện hỏng mã băm, đang chờ tải lại.
3. **`QtEventBridge` (`src/client/core/qt_bridge.py`)**:
   - Đóng vai trò cầu nối an toàn luồng, lắng nghe các sự kiện từ EventBus nền (`PyPubSub`) và phát tín hiệu `QtCore.pyqtSignal` tới luồng giao diện chính của Qt.

---

## 14. KIỂM THỬ VÀ KẾT QUẢ KIỂM THỬ TỰ ĐỘNG

Dự án áp dụng quy trình kiểm thử tự động toàn diện với `pytest` và `pytest-cov`.

### 14.1. Thống kê kết quả kiểm thử tự động
- **Tổng số test cases**: **93 test cases**.
- **Kết quả**: **93 / 93 PASSED (100%)**.
- **Thời gian chạy**: ~3.24 giây.
- **Độ bao phủ mã nguồn (Code Coverage)**: **83%** trên toàn bộ mã nguồn Client.

### 14.2. Bảng phân loại các nhóm kiểm thử

| Nhóm kiểm thử | Tệp kiểm thử | Số test | Nội dung kiểm thử chính |
|:---|:---|:---:|:---|
| **Chức năng phân mảnh và ghép tệp** | `test_chunker.py` | 1 | Cắt nhỏ tệp mẫu, băm SHA-256 từng mảnh, ghép lại và so sánh hash gốc |
| **Giao thức mạng TCP nhị phân** | `test_protocol_client.py` | 8 | Đóng gói/giải mã Handshake, Bitfield, Have, Request, Piece, Error, xử lý tràn bộ đệm |
| **TCP Peer Server** | `test_peer_server.py`, `test_protocol_server.py` | 3 | Khởi tạo server, bắt tay client, hủy đăng ký torrent, đóng kết nối sạch |
| **Khả năng chịu lỗi và tự phục hồi** | `test_fault_recovery.py` | 3 | Giả lập chunk bị sai SHA-256, kiểm tra cảnh báo đỏ, hủy chunk lỗi và tải lại thành công |
| **Điều tiết băng thông & Giả lập lỗi** | `test_rate_limiter_and_fault.py` | 4 | Kiểm thử thuật toán Token Bucket, giới hạn tốc độ và tỷ lệ lỗi đường truyền |
| **Giao tiếp Tracker API** | `test_tracker.py` | 4 | Giả lập HTTP Mock kiểm tra đăng ký tệp và điểm danh heartbeat thành công/thất bại |
| **Quản trị đa tác vụ và Đồng thời** | `test_manager.py` | 50 | Vòng đời tác vụ (Create, Start, Pause, Resume, Remove), lưu trữ phiên, tính toán băng thông |
| **Bắt tay và phân phối sự kiện** | `test_handshake_events.py` | 4 | Kiểm thử đồng bộ sự kiện bắt tay đa tiến trình qua EventBus |
| **Giao diện người dùng PyQt6** | `test_gui_app.py`, `test_gui_main_window.py`, `test_piece_grid.py`, `test_qt_bridge.py` | 16 | Kiểm thử render ma trận PieceGrid, đồng bộ thanh tiến độ, chuyển tiếp tín hiệu QtBridge |

---

## 15. ĐÁNG GIÁ HIỆU NĂNG VÀ THỰC NGHIỆM

### 15.1. Thiết lập kịch bản thực nghiệm
- Môi trường thử nghiệm: Mạng nội bộ kết hợp máy ảo/tiến trình độc lập trên các cổng TCP 6881, 6882, 6883.
- Dữ liệu thử nghiệm: Tệp video mẫu dung lượng **20 MB**, kích thước mỗi mảnh **256 KiB** (tổng cộng 80 mảnh).

### 15.2. Kết quả đo đạc tốc độ truyền tải

| Kịch bản thử nghiệm | Số lượng Seeder | Số lượng Leecher | Thời gian hoàn thành (s) | Tốc độ tải trung bình (MB/s) |
|:---|:---:|:---:|:---:|:---:|
| **Kịch bản 1: 1 nguồn duy nhất** | 1 (Peer A) | 1 (Peer B) | 14.2 s | ~1.41 MB/s |
| **Kịch bản 2: Tải song song 2 nguồn** | 2 (Peer A, Peer B) | 1 (Peer C) | 7.8 s | ~2.56 MB/s |
| **Kịch bản 3: Swarm vừa tải vừa chia sẻ** | 1 (Peer A ban đầu) | 2 (Peer B, Peer C cùng tải) | 9.1 s | Tải đồng thời cả 2 máy |

**Nhận xét**: 
- Khi số lượng nguồn tăng từ 1 lên 2 Seeder, thời gian tải giảm gần $45\%$, chứng minh tính ưu việt của cơ chế tải song song các mảnh khác nhau (Parallel Downloading).
- Trong kịch bản 3, Peer B vừa tải vừa mở cổng chia sẻ ngay các mảnh mình có cho Peer C, giúp giảm tải trực tiếp cho Seeder A và tối ưu hóa tổng thông lượng của mạng Swarm.

---

## 16. HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN

### 16.1. Hạn chế hiện tại
1. Cơ chế chọn mảnh hiện tại dựa trên tuần tự kết hợp phân bổ Worker Pool, chưa cài đặt trọn vẹn thuật toán **Rarest-First** (ưu tiên tải mảnh hiếm nhất trong Swarm).
2. Chưa tích hợp giao thức vượt tường lửa / NAT Traversal tự động (như STUN hoặc UPnP), hiện tại các peer cần thông mạng LAN hoặc sử dụng địa chỉ IP công khai / mở cổng port-forwarding.
3. Chưa tích hợp thuật toán thưởng phạt **Tit-for-Tat** (choking/unchoking) để chống các peer chỉ tải về mà không chia sẻ (Free-riders).

### 16.2. Hướng phát triển trong tương lai
1. **Bảng băm phân tán (DHT - Kademlia)**: Cho phép tìm kiếm peer không cần máy chủ Tracker (Trackerless torrent / Magnet links).
2. **Mã hóa đường truyền (P2P Encryption)**: Áp dụng TLS hoặc mã hóa khóa công khai giữa các Peer để chống lại việc nghe lén hoặc can thiệp dữ liệu từ nhà cung cấp dịch vụ mạng (ISP).
3. **Thuật toán Choking / Tit-for-Tat**: Tối ưu hóa băng thông bằng cách chỉ ưu tiên upload cho những peer nào có tốc độ upload ngược lại tốt nhất.

---

## 17. KẾT LUẬN

Đề tài **pTorrent (DS02)** đã hoàn thành xuất sắc các mục tiêu nghiên cứu và kỹ thuật đặt ra:
1. Xây dựng thành công một hệ thống chia sẻ tệp phân tán mô phỏng nguyên lý BitTorrent hoàn chỉnh, vận hành ổn định trên các tiến trình độc lập.
2. Cài đặt thành công toàn bộ các cơ chế phân tán cốt lõi: phân mảnh dữ liệu, băm SHA-256, điểm danh danh bạ qua Tracker Server, tải song song đa nguồn và vừa tải vừa chia sẻ tức thời.
3. Giải quyết triệt để các vấn đề hóc búa của hệ thống phân tán: chịu lỗi nút mạng ngắt kết nối đột ngột, phát hiện và tự phục hồi dữ liệu hỏng, khôi phục phiên làm việc và kiểm soát tốc độ truyền tải.
4. Xây dựng giao diện Desktop trực quan, đa luồng an toàn, kèm bộ kiểm thử tự động đạt 93 test cases và độ bao phủ mã nguồn 83%.
5. Dự án là minh chứng rõ nét cho ứng dụng thực tiễn của các lý thuyết Hệ thống phân tán vào bài toán giải quyết bài toán phân phối tài nguyên quy mô lớn.

---

## 18. TÀI LIỆU THAM KHẢO

1. Bram Cohen, *"Incentives Build Robustness in BitTorrent"*, First Workshop on Economics of Peer-to-Peer Systems, Berkeley, CA, 2003.
2. George Coulouris, Jean Dollimore, Tim Kindberg, Gordon Blair, *"Distributed Systems: Concepts and Design"*, 5th Edition, Addison-Wesley, 2011.
3. Andrew S. Tanenbaum, Maarten van Steen, *"Distributed Systems: Principles and Paradigms"*, 3rd Edition, CreateSpace, 2017.
4. Official BitTorrent Protocol Specification (BEP 0003), http://www.bittorrent.org/beps/bep_0003.html.
5. Python Documentation: Socket Programming HOWTO and Threading concurrency model, https://docs.python.org/3/howto/sockets.html.
6. PyQt6 Official Documentation, Riverbank Computing, https://www.riverbankcomputing.com/static/Docs/PyQt6/.

---

## 19. PHỤ LỤC

### Phụ lục A: Hướng dẫn triển khai Tracker qua Docker Compose
Tệp [deploy/docker-compose.yml](file:///D:/PTIT/ptorrent/deploy/docker-compose.yml) cho phép khởi chạy trọn vẹn cụm Tracker Server và MySQL Database cục bộ chỉ với một câu lệnh:

```bash
cd deploy/
docker-compose up -d
```

### Phụ lục B: Kịch bản lệnh khởi động nhanh 3 Peer thử nghiệm
Tệp [scripts/run_demo_3peers.ps1](file:///D:/PTIT/ptorrent/scripts/run_demo_3peers.ps1) tự động khởi chạy 3 nút Peer độc lập trên các cổng 6881, 6882, 6883 với 3 thư mục lưu trữ riêng biệt trên Windows:

```powershell
.\scripts\run_demo_3peers.ps1
```

### Phụ lục C: Lệnh chạy toàn bộ kiểm thử tự động
```powershell
pytest tests/ -v --cov=src/client --cov-report=term-missing
```
