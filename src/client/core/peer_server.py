import socket
import threading

from client.core.protocol import Protocol
from client.core.piece_manager import PieceManager
from client.utils.log import logger
from client.core.bus import bus

class PeerServer:
    def __init__(self, peer_id: str, host: str = "0.0.0.0", port: int = 6767):
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self._server_socket: socket.socket = None
        self._running = False

        self._piece_managers: dict[str, PieceManager] = {}
        self._active_clients: dict[str, list[socket.socket]] = {}
        self._lock = threading.Lock()

        bus.subscribe("chunk.completed", self._on_local_chunk_completed)

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

    def start(self):
        if self._running:
            return
        self._running = True
        self.init_socket()

        accept_thread = threading.Thread(target=self.accept_loop_thread, daemon=True)
        accept_thread.start()

    def stop(self):
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass

    def accept_loop_thread(self) -> None:
        while self._running:
            try:
                client_sock, client_addr = self._server_socket.accept()
                logger.d(f"Client {client_addr} accepted. sock={client_sock}")
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
        try:
            sock.settimeout(15.0)
            msg_type, payload = Protocol.recv(sock)
            if msg_type != Protocol.MSG_HANDSHAKE:
                Protocol.send_error(sock, "handshake first.")
                return

            hs_data = Protocol.parse_handshake(payload)
            file_id = hs_data.get("file_id")

            with self._lock:
                pm = self._piece_managers.get(file_id)

            if not pm:
                Protocol.send_error(sock, f"pm is null: {file_id}")
                return

            Protocol.send_handshake(sock, file_id, self.peer_id, is_ack=True)
            Protocol.send_bitfield(sock, pm.get_bitfield())

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

                    Protocol.send_piece(sock, piece_index, piece_data)
                    pm.record_uploaded(len(piece_data))

        except (ConnectionError, socket.timeout, OSError):
            pass
        finally:
            if file_id:
                with self._lock:
                    if file_id in self._active_clients and sock in self._active_clients[file_id]:
                        self._active_clients[file_id].remove(sock)
            try:
                sock.close()
            except Exception:
                pass