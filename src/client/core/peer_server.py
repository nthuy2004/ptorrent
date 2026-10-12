import socket
import threading

from client.core.protocol import Protocol

from client.utils.log import logger

class PeerServer:
    def __init__(self, peer_id: str, host: str = "0.0.0.0", port: int = 6767):
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self._server_socket: socket.socket = None
        self._running = False

    def init_socket(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(20)

        self.port = self._server_socket.getsockname()[1]

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
        try:
            sock.settimeout(15.0)
            msg_type, payload = Protocol.recv(sock)

            logger.d(f"client recv: {msg_type} - {payload}")

            Protocol.send(sock, 5, "PTITTTTTTT".encode("utf-8"))
        except Exception as e:
            logger.e(f"error: {e}")
            Protocol.raw_send(sock, f"error {e}".encode("utf-8"))
            raise e
        finally:
            logger.e("end")
            try:
                sock.close()
            except Exception:
                pass