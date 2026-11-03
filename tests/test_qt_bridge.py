import os
import sys
import threading
import time

from PyQt6.QtCore import QObject, QThread, pyqtSlot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.core.bus import bus
from client.core.qt_bridge import QtEventBridge


class _ChunkReceiver(QObject):
    def __init__(self):
        super().__init__()
        self.events = []
        self.delivery_thread = None

    @pyqtSlot(str, int, str)
    def receive(self, file_id, index, status):
        self.events.append((file_id, index, status))
        self.delivery_thread = QThread.currentThread()


def test_chunk_event_from_worker_is_delivered_on_qt_thread(qapp):
    bridge = QtEventBridge()
    receiver = _ChunkReceiver()
    bridge.sig_chunk_updated.connect(receiver.receive)

    worker = threading.Thread(
        target=lambda: bus.publish(
            "chunk.completed",
            {"file_id": "demo-file", "index": 2},
        )
    )
    try:
        worker.start()
        worker.join(timeout=2)
        assert not worker.is_alive()

        deadline = time.monotonic() + 2
        while not receiver.events and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)

        assert receiver.events == [("demo-file", 2, "completed")]
        assert receiver.delivery_thread == qapp.thread()
    finally:
        bridge.close()


def test_bridge_maps_task_and_peer_events(qapp):
    bridge = QtEventBridge()
    chunks = []
    progress = []
    speeds = []
    completed = []
    logs = []

    bridge.sig_chunk_updated.connect(lambda *args: chunks.append(args))
    bridge.sig_progress_updated.connect(lambda *args: progress.append(args))
    bridge.sig_speed_updated.connect(lambda *args: speeds.append(args))
    bridge.sig_task_completed.connect(lambda *args: completed.append(args))
    bridge.sig_log_message.connect(lambda *args: logs.append(args))

    try:
        bus.publish("chunk.downloading", {"file_id": "f1", "index": 0})
        bus.publish("chunk.corrupted", {"file_id": "f1", "index": 1})
        bus.publish("task.progress", {"file_id": "f1", "downloaded": 10, "total": 20})
        bus.publish("task.speed", {"file_id": "f1", "download_speed": 1.5, "upload_speed": 2})
        bus.publish("file.completed", {"file_id": "f1", "output_path": "out.bin"})
        bus.publish("peer.connected", {"peer_id": "peer-a", "ip": "127.0.0.1", "port": 6767})
        bus.publish("peer.handshake.started", {
            "peer_id": "peer-a", "ip": "127.0.0.1", "port": 6767, "direction": "outgoing"
        })
        bus.publish("peer.handshake.succeeded", {
            "peer_id": "peer-a", "ip": "127.0.0.1", "port": 6767, "direction": "outgoing"
        })
        bus.publish("peer.handshake.failed", {
            "peer_id": "peer-b", "ip": "127.0.0.2", "port": 6768,
            "direction": "incoming", "reason": "unknown file ID"
        })

        qapp.processEvents()

        assert chunks == [("f1", 0, "downloading"), ("f1", 1, "corrupted")]
        assert progress == [("f1", 10, 20)]
        assert speeds == [("f1", 1.5, 2.0)]
        assert completed == [("f1", "out.bin")]
        assert logs == [
            ("INFO", "Peer peer-a (127.0.0.1:6767) connected"),
            ("INFO", "Handshake started with outgoing peer peer-a (127.0.0.1:6767)"),
            ("INFO", "Handshake succeeded with outgoing peer peer-a (127.0.0.1:6767)"),
            ("WARNING", "Handshake failed with incoming peer peer-b (127.0.0.2:6768): unknown file ID"),
        ]
    finally:
        bridge.close()


def test_close_unsubscribes_bridge_from_event_bus(qapp):
    bridge = QtEventBridge()
    events = []
    bridge.sig_chunk_updated.connect(lambda *args: events.append(args))

    bridge.close()
    bus.publish("chunk.completed", {"file_id": "f1", "index": 3})
    qapp.processEvents()

    assert events == []
