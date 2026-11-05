import random
import socket
import threading

from client.core.protocol import Protocol
from client.core.piece_manager import PieceManager
from client.core.rate_limiter import TokenBucketRateLimiter
from client.utils.log import logger
from client.core.bus import bus


class PeerServer:
    def __init__(
        self,
        peer_id: str,
        host: str = "0.0.0.0",
        port: int = 6767,
        upload_limit: int = 0,
        fault_rate: float = 0.0,
    ):
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.upload_limit = upload_limit
        self.rate_limiter = TokenBucketRateLimiter(upload_limit) if upload_limit > 0 else None
        self.fault_rate = max(0.0, min(1.0, float(fault_rate)))

        self._server_socket: socket.socket | None = None
        self._running = False

        self._piece_managers: dict[str, PieceManager] = {}
        self._active_clients: dict[str, list[socket.socket]] = {}
        self._lock = threading.Lock()

        bus.subscribe("chunk.completed", self._on_local_chunk_completed)

    def set_upload_limit(self, limit_kib_s: int) -> None:
        self.upload_limit = limit_kib_s
        if limit_kib_s > 0:
            if not self.rate_limiter:
                self.rate_limiter = TokenBucketRateLimiter(limit_kib_s)
            else:
                self.rate_limiter.set_limit(limit_kib_s)
        else:
            self.rate_limiter = None

    def _on_local_chunk_completed(self, data: dict) -> None:
        file_id = data.get("file_id")
        piece_index = data.get("index")
        if file_id is None or piece_index is None:
            return

        with self._lock:
            clients = list(self._active_clients.get(file_id, []))

        for sock in clients:
            try:
                Protocol.send_have(sock, piece_index)
            except Exception:
                pass

    def init_socket(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(20)

        self.port = self._server_socket.getsockname()[1]

    def register_torrent(self, piece_manager: PieceManager) -> None:
        with self._lock:
            self._piece_managers[piece_manager.file_id] = piece_manager
            if piece_manager.file_id not in self._active_clients:
                self._active_clients[piece_manager.file_id] = []

    def unregister_torrent(self, file_id: str) -> None:
        with self._lock:
            self._piece_managers.pop(file_id, None)
            clients = self._active_clients.pop(file_id, [])

        for sock in clients:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def start(self):
        if self._running:
            return
        self._running = True
        self.init_socket()

        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        with self._lock:
            for clients in self._active_clients.values():
                for sock in clients:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    try:
                        sock.close()
                    except OSError:
                        pass
            self._active_clients.clear()

        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass

    def _listen(self):
        while self._running:
            try:
                client_sock, client_addr = self._server_socket.accept()
                t = threading.Thread(
                    target=self.handle_client,
                    args=(client_sock, client_addr),
                    daemon=True
                )
                t.start()
            except Exception:
                if not self._running:
                    break

    def handle_client(self, sock: socket.socket, addr):
        file_id = None
        peer_id = f"{addr[0]}:{addr[1]}"
        handshake_started = False
        handshake_succeeded = False
        try:
            sock.settimeout(15.0)
            msg_type, payload = Protocol.recv(sock)
            if msg_type != Protocol.MSG_HANDSHAKE:
                bus.publish("peer.handshake.failed", {
                    "peer_id": peer_id,
                    "ip": addr[0],
                    "port": addr[1],
                    "direction": "incoming",
                    "reason": f"expected handshake, received message type {msg_type}",
                })
                Protocol.send_error(sock, "handshake first.")
                return

            handshake_started = True
            bus.publish("peer.handshake.started", {
                "peer_id": peer_id,
                "ip": addr[0],
                "port": addr[1],
                "direction": "incoming",
            })
            try:
                hs_data = Protocol.parse_handshake(payload)
            except (ValueError, UnicodeError) as exc:
                bus.publish("peer.handshake.failed", {
                    "peer_id": peer_id,
                    "ip": addr[0],
                    "port": addr[1],
                    "direction": "incoming",
                    "reason": f"invalid handshake payload: {exc}",
                })
                Protocol.send_error(sock, "invalid handshake payload")
                return

            file_id = hs_data.get("file_id")
            peer_id = hs_data.get("peer_id") or peer_id

            with self._lock:
                pm = self._piece_managers.get(file_id)

            if not pm:
                bus.publish("peer.handshake.failed", {
                    "peer_id": peer_id,
                    "ip": addr[0],
                    "port": addr[1],
                    "direction": "incoming",
                    "reason": f"unknown file ID: {file_id}",
                })
                Protocol.send_error(sock, f"pm is null: {file_id}")
                return

            Protocol.send_handshake(sock, file_id, self.peer_id, is_ack=True)
            Protocol.send_bitfield(sock, pm.get_bitfield())
            handshake_succeeded = True
            bus.publish("peer.handshake.succeeded", {
                "peer_id": peer_id,
                "ip": addr[0],
                "port": addr[1],
                "direction": "incoming",
            })

            with self._lock:
                self._active_clients[file_id].append(sock)

            while self._running:
                msg_type, payload = Protocol.recv(sock)
                if msg_type == -1:
                    break

                if msg_type == Protocol.MSG_REQUEST:
                    piece_index = Protocol.parse_request(payload)
                    piece_data = pm.get_piece_data(piece_index)

                    if piece_data is None:
                        Protocol.send_error(sock, f"piece {piece_index} is None")
                        continue

                    # Rate limiting before transmitting piece
                    if self.rate_limiter:
                        self.rate_limiter.acquire(len(piece_data))

                    # Fault simulation: randomly corrupt piece payload
                    send_data = piece_data
                    if self.fault_rate > 0.0 and random.random() < self.fault_rate:
                        corrupted = bytearray(piece_data)
                        if corrupted:
                            corrupted[0] ^= 0xFF
                        send_data = bytes(corrupted)
                        logger.w(
                            f"Fault simulation: intentionally corrupted piece {piece_index} to peer {peer_id}"
                        )

                    Protocol.send_piece(sock, piece_index, send_data)
                    pm.record_uploaded(len(piece_data))

        except (ConnectionError, socket.timeout, OSError, ValueError) as exc:
            if handshake_started and not handshake_succeeded:
                bus.publish("peer.handshake.failed", {
                    "peer_id": peer_id,
                    "ip": addr[0],
                    "port": addr[1],
                    "direction": "incoming",
                    "reason": str(exc) or exc.__class__.__name__,
                })
        finally:
            if file_id:
                with self._lock:
                    if file_id in self._active_clients and sock in self._active_clients[file_id]:
                        self._active_clients[file_id].remove(sock)
            try:
                sock.close()
            except OSError:
                pass
