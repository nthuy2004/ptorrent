import socket
import struct
import json
from typing import Any

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

    #each msg def

    @classmethod
    def send_handshake(self, sock: socket.socket, file_id: str, peer_id: str, is_ack: bool = False) -> None:
        data = json.dumps({"file_id": file_id, "peer_id": peer_id}).encode("utf-8")
        msg_id = self.MSG_HANDSHAKE_OK if is_ack else self.MSG_HANDSHAKE
        self.send(sock, msg_id, data)

    @staticmethod
    def parse_handshake(payload: bytes) -> dict[str, Any]:
        return json.loads(payload.decode("utf-8"))

    @classmethod
    def send_bitfield(self, sock: socket.socket, bitfield: list[int]) -> None:
        data = json.dumps(bitfield).encode("utf-8")
        self.send(sock, self.MSG_BITFIELD, data)

    @staticmethod
    def parse_bitfield(payload: bytes) -> list[int]:
        return json.loads(payload.decode("utf-8"))

    @classmethod
    def send_have(self, sock: socket.socket, piece_index: int) -> None:
        payload = struct.pack(">I", piece_index)
        self.send(sock, self.MSG_HAVE, payload)

    @staticmethod
    def parse_have(payload: bytes) -> int:
        (piece_index,) = struct.unpack(">I", payload[:4])
        return piece_index

    @classmethod
    def send_request(self, sock: socket.socket, piece_index: int) -> None:
        payload = struct.pack(">I", piece_index)
        self.send(sock, self.MSG_REQUEST, payload)

    @staticmethod
    def parse_request(payload: bytes) -> int:
        (piece_index,) = struct.unpack(">I", payload[:4])
        return piece_index

    @classmethod
    def send_piece(self, sock: socket.socket, piece_index: int, piece_data: bytes) -> None:
        header = struct.pack(">I", piece_index)
        self.send(sock, self.MSG_PIECE, header + piece_data)

    @staticmethod
    def parse_piece(payload: bytes) -> tuple[int, bytes]:
        (piece_index,) = struct.unpack(">I", payload[:4])
        piece_data = payload[4:]
        return piece_index, piece_data

    @classmethod
    def send_error(self, sock: socket.socket, error_msg: str) -> None:
        self.send(sock, self.MSG_ERROR, error_msg.encode("utf-8"))
