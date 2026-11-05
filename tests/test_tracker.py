import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.core.chunker import Metadata
from client.core.tracker import Tracker


def test_tracker_register_success(requests_mock):
    base_url = "http://127.0.0.1:8000"
    tracker = Tracker(base_url)
    requests_mock.post(
        f"{base_url}/register.php",
        json={"status": "success", "message": "Registered"},
        status_code=200,
    )
    meta = Metadata("fid123", "sample.txt", 1024, 256, 4, "hash123", [], base_url)
    ok = tracker.register(meta)
    assert ok is True


def test_tracker_register_failure(requests_mock):
    base_url = "http://127.0.0.1:8000"
    tracker = Tracker(base_url)
    requests_mock.post(
        f"{base_url}/register.php",
        status_code=500,
    )
    meta = Metadata("fid123", "sample.txt", 1024, 256, 4, "hash123", [], base_url)
    ok = tracker.register(meta)
    assert ok is False


def test_tracker_announce_success(requests_mock):
    base_url = "http://127.0.0.1:8000"
    tracker = Tracker(base_url)
    requests_mock.post(
        f"{base_url}/announce.php",
        json={
            "interval": 30,
            "complete": 1,
            "incomplete": 2,
            "peers": [{"peer_id": "P2", "ip": "127.0.0.1", "port": 6882}],
        },
        status_code=200,
    )
    res = tracker.announce(
        file_id="fid123",
        peer_id="P1",
        port=6881,
        uploaded=0,
        downloaded=256,
        bytes_left=768,
        event="started",
        bitfield=[1, 0, 0, 0],
        ip="127.0.0.1",
    )
    assert res.get("complete") == 1
    assert len(res.get("peers")) == 1


def test_tracker_announce_error(requests_mock):
    base_url = "http://127.0.0.1:8000"
    tracker = Tracker(base_url)
    requests_mock.post(
        f"{base_url}/announce.php",
        status_code=500,
    )
    res = tracker.announce(
        file_id="fid123",
        peer_id="P1",
        port=6881,
        uploaded=0,
        downloaded=0,
        bytes_left=1024,
    )
    assert res.get("peers") == []
    assert res.get("interval") == 15
