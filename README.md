# HOC VIEN CONG NGHE BUU CHINH VIEN THONG (PTIT)
## KHOA CONG NGHE THONG TIN
### BAI TAP LON MON HOC: HE THONG PHAN TAN (DISTRIBUTED SYSTEMS)

---

# DE TAI DS02: HE THONG CHIA SE TEP NGANG HANG MO PHONG BITTORRENT
# (P2P FILE-SHARING SYSTEM SIMULATING BITTORRENT)

- Repository: https://github.com/nthuy2004/ptorrent
- Phien ban: v1.0.0
- Nam hoc: 2026 - 2027

---

## 1. THONG TIN NHOM VA PHAN CONG NHIEM VU

Theo quy dinh tai Muc 2 va Muc 10.1 cua dac ta de tai, moi thanh vien chiu trach nhiem chinh cho mot thanh phan he thong va co lich su dong gop ro rang tren GitHub:

| STT | Ho va ten | Ma sinh vien | Vai tro | Nhiem vu chinh va Dong gop tren GitHub |
|:---:|:---|:---:|:---|:---|
| 1 | Nguyễn Tiến Huy (Nhóm trưởng) | B23DCVT213 | Core Network & Tracker Lead | - Khoi tao kien truc base source, tai lieu dac ta.<br>- Giao thuc mang TCP nhi phan (protocol.py).<br>- Module Chunker (chia/ghep tep, SHA-256) va PieceManager.<br>- Tracker backend (PHP, MySQL) va Tracker client.<br>- Quan ly tich hop Git, review PRs va merge code. |
| 2 | Lê Đăng Khoa | B23DCVT236 | Concurrency & Manager Lead | - Xay dung lop dieu phoi da tep TorrentManager va TorrentTask.<br>- Quan ly vong doi tac vu (create, add, pause, resume, remove).<br>- Co che Session Persistence (session.json) phuc vu Resume.<br>- Co che tinh toan bang thong (Speed Loop) va advertise_ip.<br>- Viet bo test tu dong tests/test_manager.py (50 test cases). |
| 3 | Nguyễn Hữu Tuấn Minh | B23DCVT279 | Desktop GUI & Integration Lead | - Cau noi su kien da luong QtEventBridge (PyPubSub -> Qt Signals).<br>- Widget PieceGrid truc quan hoa Bitfield Grid bang QPainter.<br>- Cua so chinh MainWindow tich hop QThreadPool xu ly bat dong bo.<br>- Hop thoai CreateTorrentDialog va OpenTorrentDialog.<br>- Viet bo test kiem thu giao dien nguoi dung (GUI tests). |

---

## 2. TONG QUAN KIEN TRUC HE THONG

He thong gom 2 phan tach biet theo dung nguyen ly He thong phan tan:

1. **Tracker Server (PHP + MySQL):**
   - Dong vai tro la so danh ba trung gian (Central Registry / Swarm Coordinator).
   - Chi quan ly metadata va danh sach IP:Port cua cac Peer dang online.
   - Tuyet doi khong luu tru va khong trung chuyen du lieu tep tin goc.

2. **Peer Node Client (Python 3 + PyQt6):**
   - Vua dong vai tro TCP Server (lang nghe yeu cau upload), vua la TCP Client (tai song song tu nhieu nguon).
   - Giao dien Desktop GUI hien thi danh sach torrent va truc quan hoa trang thai tung manh du lieu (Piece Grid).

```
                 +---------------------------------------------+
                 |            TRACKER SERVER (PHP/MySQL)       |
                 |     (Chi dieu phoi danh ba, khong giu tep)  |
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
                         | - Tai tu ca A va B      |
                         +-------------------------+
```

---

## 3. CAC TINH NANG VA CO CHE PHAN TAN COT LOI

- **Data Chunking & Hashing:** Tep duoc chia thanh cac manh co dinh (16 KiB - 2048 KiB). Moi manh duoc bam SHA-256 doc lap va toan bo tep co mot ma hash dai dien (file_id).
- **Upload while Downloading:** Peer ngay khi tai va xac thuc thanh cong mot manh bat ky se lap tuc mo cong upload de phuc vu cac peer khac trong mang.
- **Parallel Downloading:** Downloader su dung Worker Pool de ket noi dong thoi toi nhieu peer, tai cac chunk khac nhau song song.
- **Piece Integrity Verification:** Moi chunk nhan ve duoc tinh lai SHA-256. Neu phat hien loi (Corrupted Piece), chunk bi huy bo va xep hang tai lai tu nguon khac.
- **Fault Tolerance & Churn Handling:** Khi mot Peer nguon ngat ket noi dot ngot (Timeout), chunk dang tai do duoc tra ve hang doi va tu dong chuyen sang peer khac.
- **Session Persistence & Resume:** Luu trang thai cac tac vu vao session.json. Khi khoi dong lai, ung dung tu dong scan cac chunk .dat tren dia va chi tai tiep phan con thieu.
- **Thread-safe GUI:** Toan bo thao tac doc ghi dia va giao tiep mang duoc xu ly tren luong nen thong qua QThreadPool va EventBus (PyPubSub), dam bao giao dien khong bao gio bi treo (Not Responding).

---

## 4. CAU TRUC THU MUC DU AN


```
ptorrent/
|-- README.md                     # Tai lieu tong quan, kien truc, phan cong, huong dan chay
|-- requirements.txt              # Danh sach thu vien Python phu thuoc
|-- DEBAI.pdf                     # Dac ta yeu cau bai tap lon PTIT
|-- deploy/                       # Cau hinh dong goi va trien khai
|   +-- .gitkeep
|-- docs/                         # Bao cao ky thuat (report.pdf) va slide thuyet trinh
|   +-- .gitkeep
|-- scripts/                      # Script ho tro sinh file test, benchmark, failover
|   +-- .gitkeep
|-- tests/                        # Bo kiem thu tu dong (pytest)
|   |-- test_chunker.py           # Kiem thu chia manh, bam SHA-256 va ghep tep
|   |-- test_manager.py           # 50 test cases cho TorrentManager va TorrentTask
|   |-- test_gui_main_window.py   # Kiem thu giao dien bang danh sach MainWindow
|   |-- test_piece_grid.py        # Kiem thu PieceGrid widget
|   |-- test_qt_bridge.py         # Kiem thu cau noi chuyen tiep tin hieu giua cac luong
|   +-- test_peer_server.py       # Kiem thu PeerServer socket
+-- src/
    |-- tracker/                  # Backend Tracker Server (PHP + MySQL)
    |   |-- database.php          # Ket noi PDO toi MySQL
    |   |-- db.php                # Helpers xu ly request / response JSON
    |   |-- register.php          # API tiep nhan dang ky metadata tep tu Seeder
    |   +-- announce.php          # API tiep nhan heartbeat va tra ve danh sach Peer
    +-- client/                   # Ma nguon Peer Client (Python 3 + PyQt6)
        |-- main.py               # Diem khoi chay ung dung Desktop GUI
        |-- core/                 # Engine xu ly mang va du lieu
        |   |-- bus.py            # In-App EventBus su dung PyPubSub
        |   |-- chunker.py        # Module Metadata, băm SHA-256, doc ghi tep
        |   |-- protocol.py       # Giao thuc dong goi ban tin nhi phan TCP
        |   |-- piece_manager.py  # Quan ly bitfield, luu tru chunk, resume
        |   |-- peer_server.py    # TCP Server lang nghe yeu cau upload tu peer khac
        |   |-- downloader.py     # Worker Pool tai song song va xu ly churn
        |   |-- tracker.py        # HTTP Client giao tiep Tracker API
        |   |-- torrent_manager.py# Lop dieu phoi tong the cac tac vu tai/seed
        |   +-- qt_bridge.py      # Chuyen doi EventBus sang PyQt6 Signals
        |-- gui/                  # Giao dien Desktop PyQt6
        |   |-- app.py            # Ham bootstrap khoi dong QApplication
        |   |-- main_window.py    # Cua so chinh, Toolbar, Table, Log panel
        |   |-- piece_grid.py     # Widget ve ma tran mau Bitfield (QPainter)
        |   +-- dialogs.py        # Hop thoai tao moi va mo tep metadata
        +-- utils/
            +-- log.py            # He thong Logger mau tren console
```

---

## 5. YEU CAU HE THONG VA CAI DAT

### 5.1. Yeu cau moi truong
- He dieu hanh: Windows 10/11, Linux, macOS.
- Python: Phien ban >= 3.10.
- Tracker Server:
  - Tuy chon 1 (Mac dinh): Su dung Tracker truc tuyen da trien khai tai: `https://tracker.nth.id.vn`
  - Tuy chon 2 (Cuc bo): PHP 8.x + MySQL (chay qua XAMPP hoac Docker).

### 5.2. Cai dat moi truong Python
Mo terminal tai thu muc goc cua du an:

```bash
# 1. Tao moi truong ao (khuyen nghi)
python -m venv venv

# Kich hoat moi truong ao tren Windows:
venv\Scripts\activate

# Kich hoat moi truong ao tren Linux/macOS:
source venv/bin/activate

# 2. Cai dat cac goi phu thuoc
pip install -r requirements.txt
```

---

## 6. HUONG DAN VAN HANH (EXECUTION INSTRUCTIONS)

### 6.1. Khoi chay ung dung giao dien Desktop (PyQt6 GUI)

Chay lenh sau tai thu muc goc:

```bash
python src/client/main.py
```

Cac tham so dong lenh ho tro:
- `--tracker-url`: Dia chi Tracker Server (mac dinh: `https://tracker.nth.id.vn`).
- `--port`: Cong TCP lang nghe ket noi tu cac Peer khac (mac dinh: `6881`).
- `--storage-root`: Thu muc luu tru du lieu session va cac chunk (mac dinh: `~/.ptorrent`).

Vi du khoi chay Peer thu 2 tren cung mot may tinh (khac cong va khac thu muc luu tru):

```bash
python src/client/main.py --port 6882 --storage-root C:\temp\peer2
```

### 6.2. Huong dan cac thao tac co ban tren giao dien
1. **Chia se tep moi (Seeder):**
   - Nhan nut **Create torrent** tren thanh cong cu.
   - Chon tep nguon can chia se va kich thuoc chunk mong muon (mac dinh: 256 KiB).
   - Nhan **OK**: He thong tu dong bam SHA-256, tao tep metadata `.ptorrent`, dang ky len Tracker va hien thi 100% tren Piece Grid.
2. **Tai tep (Leecher):**
   - Nhan nut **Open torrent** tren thanh cong cu.
   - Chon tep metadata `.ptorrent` can tai.
   - Nhan **Open**: He thong tu dong ket noi Tracker, lay danh sach peer va tien hanh tai song song.
3. **Dieu khien tac vu:**
   - Chon dong tep tren bang danh sach, su dung cac nut **Pause**, **Resume**, hoac **Remove**.

---

## 7. CHAY BO KIEM THU TU DONG (AUTOMATED TESTS)

Du an co he thong kiem thu tu dong su dung `pytest`. Chay toan bo test suite bang lenh:

```bash
pytest tests/ -v
```

Ket qua kiem thu xac nhan toan bo 71 test cases deu vuot qua (Passed), bao gom:
- Kiem thu logic cat/ghep tep va xac thuc ma bam (test_chunker.py).
- Kiem thu xu ly vong doi TorrentManager, luu tru session, tinh toan bang thong (test_manager.py).
- Kiem thu giao dien nguoi dung, ve ma tran mau Bitfield va chuyen tiep tin hieu da luong (test_gui_*.py, test_qt_bridge.py).

---

## 8. KICH BAN DEMO BAT BUOC TRUOC HOI DONG (7 MANDATORY SCENARIOS)

Theo quy dinh tai Muc 6.4 cua dac ta de tai:

1. **Kich ban 1 - Tao metadata va chia se tep:**
   - Mo Client 1 (Seeder). Nhan "Create torrent", chon tep video mau (vi du: 20 MB).
   - Hien thi: Tep `.ptorrent` duoc sinh ra, Tracker Dashboard ghi nhan tep moi, bang Piece Grid cua Client 1 xanh toan bo 100%.

2. **Kich ban 2 - Tai song song tu it nhat 2 peers:**
   - Khoi chay Seeder A (100%) va Seeder B (100%).
   - Mo Client C (Leecher). Client C ket noi toi ca A va B, bang log the hien cac chunk duoc keo ve dong thoi tu ca 2 dia chi IP:Port khac nhau.

3. **Kich ban 3 - Vua tai vua chia se (Upload while downloading):**
   - Seeder A co 100% tep. Client B bat dau tai tu A.
   - Khi Client B moi tai duoc khoang 25% (10/40 chunks), bat Client C vao tai.
   - Bang log cua Client B xuat hien: `[UPLOAD] Sent piece #x to Client C` ngay khi B chua tai xong tep.

4. **Kich ban 4 - Dung mot nguon khi dang tai (Fault Tolerance):**
   - Client C dang tai tu Seeder A va Client B. Chu dong dong ung dung Seeder A dot ngot (Ctrl+C hoac tat cua so).
   - Client C bat timeout socket, khong bi dung hinh hoac crash ung dung.

5. **Kich ban 5 - Tu dong chuyen sang nguon khac:**
   - Tiep tuc tu Kich ban 4: Client C tu dong chuyen toan bo cac chunk con thieu sang tiep tuc yeu cau tu Client B va hoan thanh qua trinh tai.

6. **Kich ban 6 - Phat hien va xu ly chunk bi hong (Data Corruption):**
   - Mo phong 1 chunk bi sai ma bam SHA-256 tren duong truyen.
   - Tren giao dien: O vuong chunk do chuyen sang mau DO, log canh bao `CORRUPTED: Hash mismatch`. Chunk duoc tu dong yeu cau tai lai va chuyen thanh mau XANH.

7. **Kich ban 7 - Ghep tep va xac thuc Hash cuoi cung:**
   - Sau khi tai du 100% cac chunk, ung dung tu dong ghep thanh tep hoan chinh.
   - So sanh SHA-256 cua tep dau ra voi tep ban dau: Khop 100%. Mo tep len kiem tra noi dung toan ven.
