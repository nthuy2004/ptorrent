import time
import socket
import threading
from typing import Optional, Callable
from client.core.protocol import Protocol
from client.core.piece_manager import PieceManager
from client.core.bus import bus


class Downloader:
    def __init__(
        self,
        peer_id: str,
        piece_manager: PieceManager,
        max_workers: int = 4,
        socket_timeout: float = 5.0,
        on_source_lost_callback: Optional[Callable[[], None]] = None
    ):
        self.peer_id = peer_id
        self.pm = piece_manager
        self.max_workers = max_workers
        self.socket_timeout = socket_timeout
        self.on_source_lost_callback = on_source_lost_callback

        self._active_peers: set[tuple[str, int]] = set()
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def add_peers(self, peers_list: list[dict]) -> None:
        if not self._running or self.pm.is_complete():
            return

        for p in peers_list:
            ip = p.get("ip", "127.0.0.1")
            port = int(p.get("port", 0))
            remote_peer_id = p.get("peer_id", f"{ip}:{port}")
            if port <= 0 or remote_peer_id == self.peer_id:
                continue

            peer_addr = (ip, port)
            with self._lock:
                if peer_addr in self._active_peers or len(self._active_peers) >= self.max_workers:
                    continue
                self._active_peers.add(peer_addr)

            t = threading.Thread(
                target=self._peer_worker_thread,
                args=(ip, port, remote_peer_id),
                daemon=True
            )
            t.start()

    def _peer_worker_thread(self, ip: str, port: int, remote_peer_id: str) -> None:
        peer_addr = (ip, port)
        peer_label = f"{remote_peer_id} ({ip}:{port})"
        sock: Optional[socket.socket] = None
        current_piece: Optional[int] = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.socket_timeout)
            sock.connect(peer_addr)

            Protocol.send_handshake(sock, self.pm.file_id, self.peer_id, is_ack=False)

            msg_type, payload = Protocol.recv(sock)
            if msg_type != Protocol.MSG_HANDSHAKE_OK:
                return

            hs_ack = Protocol.parse_handshake(payload)
            remote_peer_id = hs_ack.get("peer_id", remote_peer_id)
            peer_label = f"{remote_peer_id} ({ip}:{port})"

            msg_type, payload = Protocol.recv(sock)
            if msg_type != Protocol.MSG_BITFIELD:
                return
            remote_bitfield = Protocol.parse_bitfield(payload)

            bus.publish("peer.connected", {
                "peer_id": remote_peer_id,
                "ip": ip,
                "port": port
            })

            while self._running and not self.pm.is_complete():
                current_piece = self.pm.select_next_piece_to_download(remote_bitfield)

                if current_piece is None:
                    # Đối phương hiện chưa có chunk nào mà mình cần -> Lắng nghe bản tin HAVE mới
                    sock.settimeout(0.5)
                    try:
                        m_type, m_payload = Protocol.recv(sock)
                        if m_type == Protocol.MSG_HAVE:
                            new_idx = Protocol.parse_have(m_payload)
                            if 0 <= new_idx < len(remote_bitfield):
                                remote_bitfield[new_idx] = 1
                        elif m_type == -1:
                            break
                    except socket.timeout:
                        pass
                    finally:
                        sock.settimeout(self.socket_timeout)
                    continue

                # Phát sự kiện đang tải chunk
                bus.publish("chunk.downloading", {
                    "file_id": self.pm.file_id,
                    "index": current_piece,
                    "peer": peer_label
                })

                # Gửi MSG_REQUEST(current_piece)
                Protocol.send_request(sock, current_piece)

                # Chờ nhận MSG_PIECE (trong lúc chờ vẫn có thể nhận xen kẽ gói MSG_HAVE)
                while self._running:
                    m_type, m_payload = Protocol.recv(sock)
                    if m_type == Protocol.MSG_HAVE:
                        new_idx = Protocol.parse_have(m_payload)
                        if 0 <= new_idx < len(remote_bitfield):
                            remote_bitfield[new_idx] = 1
                    elif m_type == Protocol.MSG_PIECE:
                        recv_idx, piece_data = Protocol.parse_piece(m_payload)
                        # Lưu và kiểm tra SHA-256
                        self.pm.save_and_verify_piece(recv_idx, piece_data, from_peer=peer_label)
                        current_piece = None
                        break
                    elif m_type == Protocol.MSG_ERROR:
                        self.pm.switch_piece_to_pending(current_piece)
                        current_piece = None
                        time.sleep(0.2)
                        break
                    else:
                        raise ConnectionError("Gói tin không hợp lệ hoặc kết nối đã đóng.")

        except (ConnectionError, socket.timeout, OSError):
            if current_piece is not None:
                self.pm.switch_piece_to_pending(current_piece)
                current_piece = None

            if not self.pm.is_complete():
                bus.publish("peer.disconnected", {
                    "peer_id": remote_peer_id,
                    "ip": ip,
                    "port": port
                })
                if self.on_source_lost_callback:
                    try:
                        self.on_source_lost_callback()
                    except Exception:
                        pass
        finally:
            if current_piece is not None:
                self.pm.switch_piece_to_pending(current_piece)
            with self._lock:
                self._active_peers.discard(peer_addr)
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
