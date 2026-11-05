import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.core.peer_server import PeerServer


def test_peer_server_lifecycle():
    server = PeerServer("PEER_LIFECYCLE_TEST", "127.0.0.1", 0)
    assert server.peer_id == "PEER_LIFECYCLE_TEST"
    assert server._running is False
    server.start()
    assert server._running is True
    assert server.port > 0
    server.stop()
    assert server._running is False
