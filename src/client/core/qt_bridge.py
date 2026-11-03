from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal

from client.core.bus import bus


class QtEventBridge(QObject):
    """Forward core EventBus messages to Qt's thread-aware signal system."""

    sig_chunk_updated = pyqtSignal(str, int, str)
    sig_progress_updated = pyqtSignal(str, int, int)
    sig_speed_updated = pyqtSignal(str, float, float)
    sig_task_completed = pyqtSignal(str, str)
    sig_log_message = pyqtSignal(str, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._subscriptions: list[tuple[str, Callable]] = []
        self._closed = False

        self._subscribe("chunk.downloading", self._on_chunk_downloading)
        self._subscribe("chunk.completed", self._on_chunk_completed)
        self._subscribe("chunk.corrupted", self._on_chunk_corrupted)
        self._subscribe("file.completed", self._on_file_completed)
        self._subscribe("task.progress", self._on_progress)
        self._subscribe("task.speed", self._on_speed)
        self._subscribe("peer.handshake.started", self._on_handshake_started)
        self._subscribe("peer.handshake.succeeded", self._on_handshake_succeeded)
        self._subscribe("peer.handshake.failed", self._on_handshake_failed)
        self._subscribe("peer.connected", self._on_peer_connected)
        self._subscribe("peer.disconnected", self._on_peer_disconnected)

    def _subscribe(self, topic: str, callback: Callable) -> None:
        bus.subscribe(topic, callback)
        self._subscriptions.append((topic, callback))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for topic, callback in self._subscriptions:
            bus.unsubscribe(topic, callback)
        self._subscriptions.clear()

    def _emit_chunk_status(self, data: dict, status: str) -> None:
        file_id = data.get("file_id")
        index = data.get("index")
        if file_id is not None and isinstance(index, int):
            self.sig_chunk_updated.emit(str(file_id), index, status)

    def _on_chunk_downloading(self, data: dict | None = None) -> None:
        self._emit_chunk_status(data or {}, "downloading")

    def _on_chunk_completed(self, data: dict | None = None) -> None:
        self._emit_chunk_status(data or {}, "completed")

    def _on_chunk_corrupted(self, data: dict | None = None) -> None:
        self._emit_chunk_status(data or {}, "corrupted")

    def _on_file_completed(self, data: dict | None = None) -> None:
        data = data or {}
        file_id = data.get("file_id")
        output_path = data.get("output_path")
        if file_id is not None and output_path is not None:
            self.sig_task_completed.emit(str(file_id), str(output_path))

    def _on_progress(self, data: dict | None = None) -> None:
        data = data or {}
        file_id = data.get("file_id")
        downloaded = data.get("downloaded")
        total = data.get("total")
        if file_id is not None and isinstance(downloaded, int) and isinstance(total, int):
            self.sig_progress_updated.emit(str(file_id), downloaded, total)

    def _on_speed(self, data: dict | None = None) -> None:
        data = data or {}
        file_id = data.get("file_id")
        download_speed = data.get("download_speed")
        upload_speed = data.get("upload_speed")
        if file_id is not None and isinstance(download_speed, (int, float)) and isinstance(upload_speed, (int, float)):
            self.sig_speed_updated.emit(str(file_id), float(download_speed), float(upload_speed))

    def _on_peer_connected(self, data: dict | None = None) -> None:
        self._emit_peer_log(data or {}, "connected")

    def _on_peer_disconnected(self, data: dict | None = None) -> None:
        self._emit_peer_log(data or {}, "disconnected")

    def _emit_peer_log(self, data: dict, state: str) -> None:
        peer_id = data.get("peer_id", "unknown peer")
        address = data.get("ip")
        port = data.get("port")
        endpoint = f" ({address}:{port})" if address is not None and port is not None else ""
        self.sig_log_message.emit("INFO", f"Peer {peer_id}{endpoint} {state}")

    def _on_handshake_started(self, data: dict | None = None) -> None:
        self._emit_handshake_log(data or {}, "started", "INFO")

    def _on_handshake_succeeded(self, data: dict | None = None) -> None:
        self._emit_handshake_log(data or {}, "succeeded", "INFO")

    def _on_handshake_failed(self, data: dict | None = None) -> None:
        self._emit_handshake_log(data or {}, "failed", "WARNING")

    def _emit_handshake_log(self, data: dict, state: str, level: str) -> None:
        peer_id = data.get("peer_id", "unknown peer")
        address = data.get("ip")
        port = data.get("port")
        endpoint = f" ({address}:{port})" if address is not None and port is not None else ""
        direction = data.get("direction", "peer")
        message = f"Handshake {state} with {direction} peer {peer_id}{endpoint}"
        reason = data.get("reason")
        if reason:
            message = f"{message}: {reason}"
        self.sig_log_message.emit(level, message)
