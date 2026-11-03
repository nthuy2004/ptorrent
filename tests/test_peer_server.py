"""Test PeerServer.unregister_torrent (chạy được khi không có mạng).

    python -m pytest tests/test_peer_server.py -q
"""

import os
import socket
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.core.chunker import Chunker
from client.core.peer_server import PeerServer
from client.core.piece_manager import PieceManager
from client.core.protocol import Protocol

PIECE = 1024


def make_server_with_file(tmp_path):
    src = tmp_path / "source.bin"
    src.write_bytes(os.urandom(3 * PIECE))
    meta = Chunker().create_metadata(str(src), "http://x/announce.php", PIECE)
    pm = PieceManager(meta, str(tmp_path / "storage"), original_file_path=str(src))
    server = PeerServer("PEER_TEST", "127.0.0.1", 0)
    server.register_torrent(pm)
    server.start()
    return server, pm


def connect(server, file_id):
    sock = socket.create_connection(("127.0.0.1", server.port), timeout=3)
    Protocol.send_handshake(sock, file_id, "PEER_CLIENT")
    return sock


def test_unregister_removes_the_torrent_and_closes_its_clients(tmp_path):
    server, pm = make_server_with_file(tmp_path)
    try:
        sock = connect(server, pm.file_id)
        assert Protocol.recv(sock)[0] == Protocol.MSG_HANDSHAKE_OK
        assert Protocol.recv(sock)[0] == Protocol.MSG_BITFIELD

        deadline = time.monotonic() + 3  # đợi server ghi nhận kết nối
        while not server._active_clients.get(pm.file_id) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server._active_clients[pm.file_id]

        server.unregister_torrent(pm.file_id)
        assert pm.file_id not in server._piece_managers
        assert pm.file_id not in server._active_clients

        with pytest.raises(ConnectionError):  # kết nối đang mở bị đóng
            Protocol.recv(sock)
        sock.close()

        # kết nối mới vào file này bị từ chối
        again = connect(server, pm.file_id)
        assert Protocol.recv(again)[0] == Protocol.MSG_ERROR
        again.close()
    finally:
        server.stop()


def test_unregister_unknown_torrent_does_nothing(tmp_path):
    server, pm = make_server_with_file(tmp_path)
    try:
        server.unregister_torrent("khong-co")
        assert pm.file_id in server._piece_managers  # file khác không bị ảnh hưởng
    finally:
        server.stop()
