import os
import sys
import socket
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.core.bus import bus
from client.core.downloader import Downloader
from client.core.peer_server import PeerServer
from client.core.protocol import Protocol


class _PieceManager:
    file_id = "file-a"

    def is_complete(self):
        return True

    def get_bitfield(self):
        return [1]


def _capture_handshake_events():
    events = []
    callbacks = []
    for topic in (
        "peer.handshake.started",
        "peer.handshake.succeeded",
        "peer.handshake.failed",
    ):
        def callback(data=None, topic=topic):
            events.append((topic, data))

        callbacks.append((topic, callback))
        bus.subscribe(topic, callback)
    return events, callbacks


def _unsubscribe(callbacks):
    for topic, callback in callbacks:
        bus.unsubscribe(topic, callback)


def test_downloader_emits_outgoing_handshake_success():
    events, callbacks = _capture_handshake_events()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(2)
    listener.settimeout(2)
    port = listener.getsockname()[1]

    def respond(send_ack):
        try:
            conn, _ = listener.accept()
            with conn:
                conn.settimeout(2)
                assert Protocol.recv(conn)[0] == Protocol.MSG_HANDSHAKE
                if send_ack:
                    Protocol.send_handshake(conn, "file-a", "remote-peer", is_ack=True)
                    Protocol.send_bitfield(conn, [1])
                else:
                    Protocol.send_error(conn, "rejected")
        finally:
            listener.close()

    try:
        server = threading.Thread(target=respond, args=(True,))
        server.start()
        downloader = Downloader("local-peer", _PieceManager(), socket_timeout=2)
        downloader.start()
        downloader._peer_worker_thread("127.0.0.1", port, "remote-peer")
        server.join(timeout=2)
        assert not server.is_alive()

        assert [topic for topic, _ in events] == [
            "peer.handshake.started",
            "peer.handshake.succeeded",
        ]
        assert events[0][1]["direction"] == "outgoing"
        assert events[1][1]["peer_id"] == "remote-peer"
    finally:
        _unsubscribe(callbacks)
        try:
            listener.close()
        except OSError:
            pass


def test_downloader_emits_outgoing_handshake_failure():
    events, callbacks = _capture_handshake_events()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(2)
    port = listener.getsockname()[1]

    def reject():
        try:
            conn, _ = listener.accept()
            with conn:
                conn.settimeout(2)
                assert Protocol.recv(conn)[0] == Protocol.MSG_HANDSHAKE
                Protocol.send_error(conn, "rejected")
        finally:
            listener.close()

    try:
        server = threading.Thread(target=reject)
        server.start()
        downloader = Downloader("local-peer", _PieceManager(), socket_timeout=2)
        downloader.start()
        downloader._peer_worker_thread("127.0.0.1", port, "remote-peer")
        server.join(timeout=2)
        assert not server.is_alive()

        assert [topic for topic, _ in events] == [
            "peer.handshake.started",
            "peer.handshake.failed",
        ]
        assert events[1][1]["reason"] == "expected handshake ACK, received message type 6"
    finally:
        _unsubscribe(callbacks)
        try:
            listener.close()
        except OSError:
            pass


def test_peer_server_emits_incoming_handshake_success():
    events, callbacks = _capture_handshake_events()
    server = PeerServer("local-peer")
    server._running = True
    server.register_torrent(_PieceManager())
    server_sock, client_sock = socket.socketpair()
    worker = threading.Thread(
        target=server.handle_client,
        args=(server_sock, ("127.0.0.1", 54321)),
    )

    try:
        worker.start()
        Protocol.send_handshake(client_sock, "file-a", "remote-peer")
        assert Protocol.recv(client_sock)[0] == Protocol.MSG_HANDSHAKE_OK
        assert Protocol.recv(client_sock)[0] == Protocol.MSG_BITFIELD
        client_sock.close()
        worker.join(timeout=2)
        assert not worker.is_alive()

        assert [topic for topic, _ in events] == [
            "peer.handshake.started",
            "peer.handshake.succeeded",
        ]
        assert events[0][1]["direction"] == "incoming"
        assert events[1][1]["peer_id"] == "remote-peer"
    finally:
        client_sock.close()
        server._running = False
        _unsubscribe(callbacks)


def test_peer_server_emits_incoming_handshake_failure_for_unknown_file():
    events, callbacks = _capture_handshake_events()
    server = PeerServer("local-peer")
    server._running = True
    server_sock, client_sock = socket.socketpair()
    worker = threading.Thread(
        target=server.handle_client,
        args=(server_sock, ("127.0.0.1", 54322)),
    )

    try:
        worker.start()
        Protocol.send_handshake(client_sock, "unknown-file", "remote-peer")
        assert Protocol.recv(client_sock)[0] == Protocol.MSG_ERROR
        worker.join(timeout=2)
        assert not worker.is_alive()

        assert [topic for topic, _ in events] == [
            "peer.handshake.started",
            "peer.handshake.failed",
        ]
        assert "unknown file ID" in events[1][1]["reason"]
    finally:
        client_sock.close()
        server._running = False
        _unsubscribe(callbacks)
