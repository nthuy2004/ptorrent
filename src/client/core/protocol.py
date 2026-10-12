import socket
import struct

MAX_BUF_LEN = 10 * 1024 * 1024

class Protocol:
    # msg type
    MSG_HANDSHAKE = 0
    MSG_HANDSHAKE_OK = 1
    MSG_BITFIELD = 2
    MSG_HAVE = 3
    MSG_REQUEST = 4
    MSG_PIECE = 5
    MSG_ERROR = 6

    @staticmethod
    def raw_recv(sock: socket.socket, length: int) -> bytes:
        buffer = bytearray()
        while len(buffer) < length:
            packet = sock.recv(length - len(buffer))
            if not packet:
                raise ConnectionError("tcp closed")
            buffer.extend(packet)
        return bytes(buffer)

    @staticmethod
    def raw_send(sock: socket.socket, msg: bytes):
        sock.sendall(msg)

    @classmethod
    def send(self, sock: socket.socket, type: int, payload: bytes = b""):
        length = len(payload) + 1
        header = struct.pack(">IB", length, type)
        self.raw_send(sock, header + payload)

    @classmethod
    def recv(self, sock: socket.socket) -> tuple[int, bytes]:
        raw_len = self.raw_recv(sock, 4)
        (length,) = struct.unpack(">I", raw_len)

        if length == 0 or length > MAX_BUF_LEN:
            raise ValueError(f"invalid buffer length: len > {MAX_BUF_LEN}")

        raw_type = self.raw_recv(sock, 1)
        (type,) = struct.unpack(">B", raw_type)

        payload_len = length - 1
        payload = self.raw_recv(sock, payload_len) if payload_len > 0 else b""
        return type, payload