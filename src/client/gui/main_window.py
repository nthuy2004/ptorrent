from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QTimer, pyqtSignal, pyqtSlot, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QWidget,
    QVBoxLayout,
)

from client.core.qt_bridge import QtEventBridge
from client.gui.dialogs import CreateTorrentDialog, OpenTorrentDialog
from client.gui.piece_grid import PieceGrid


class _OperationSignals(QObject):
    finished = pyqtSignal(str, object)
    failed = pyqtSignal(str, str)


class _Operation(QRunnable):
    def __init__(self, key: str, operation: Callable, args: tuple, kwargs: dict):
        super().__init__()
        self.key = key
        self.operation = operation
        self.args = args
        self.kwargs = kwargs
        self.signals = _OperationSignals()

    def run(self) -> None:
        try:
            result = self.operation(*self.args, **self.kwargs)
        except Exception as exc:
            self.signals.failed.emit(self.key, str(exc))
        else:
            self.signals.finished.emit(self.key, result)


class MainWindow(QMainWindow):
    COLUMNS = ("File", "Size", "Progress", "Download", "Upload", "Status")

    def __init__(self, manager: Any, bridge: QtEventBridge | None = None):
        super().__init__()
        self.manager = manager
        self.bridge = bridge or QtEventBridge(self)
        self._workers: dict[str, _Operation] = {}
        self._operation_sequence = 0
        self._tasks_by_id: dict[str, Any] = {}
        self._row_by_id: dict[str, int] = {}
        self._active_file_id: str | None = None
        self._pool = QThreadPool.globalInstance()

        self.setWindowTitle("pTorrent")
        self.resize(1080, 720)
        self._build_ui()
        self._connect_bridge()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self.refresh_tasks)
        self._refresh_timer.start()
        self.refresh_tasks()

    def _build_ui(self) -> None:
        toolbar = QToolBar("Torrent actions", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.create_action = toolbar.addAction("Create torrent")
        self.open_action = toolbar.addAction("Open torrent")
        toolbar.addSeparator()
        self.resume_action = toolbar.addAction("Resume")
        self.pause_action = toolbar.addAction("Pause")
        self.remove_action = toolbar.addAction("Remove")
        self.create_action.triggered.connect(self._create_torrent)
        self.open_action.triggered.connect(self._open_torrent)
        self.resume_action.triggered.connect(self._resume_selected)
        self.pause_action.triggered.connect(self._pause_selected)
        self.remove_action.triggered.connect(self._remove_selected)

        self.torrent_table = QTableWidget(0, len(self.COLUMNS), self)
        self.torrent_table.setHorizontalHeaderLabels(self.COLUMNS)
        self.torrent_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.torrent_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.torrent_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.torrent_table.verticalHeader().setVisible(False)
        self.torrent_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.torrent_table.itemSelectionChanged.connect(self._on_selection_changed)

        self.piece_grid = PieceGrid(self)
        self.grid_scroll = QScrollArea(self)
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.grid_scroll.setWidget(self.piece_grid)

        grid_panel = QWidget(self)
        grid_layout = QVBoxLayout(grid_panel)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.addWidget(QLabel("Pieces", grid_panel))
        grid_layout.addWidget(self.grid_scroll, 1)

        self.log_view = QTextEdit(self)
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(110)

        lower = QSplitter(Qt.Orientation.Vertical, self)
        lower.addWidget(grid_panel)
        lower.addWidget(self.log_view)
        lower.setStretchFactor(0, 3)
        lower.setStretchFactor(1, 1)

        content = QSplitter(Qt.Orientation.Vertical, self)
        content.addWidget(self.torrent_table)
        content.addWidget(lower)
        content.setStretchFactor(0, 2)
        content.setStretchFactor(1, 3)
        self.setCentralWidget(content)

    def _connect_bridge(self) -> None:
        self.bridge.sig_chunk_updated.connect(self._on_chunk_update)
        self.bridge.sig_progress_updated.connect(self._on_progress_update)
        self.bridge.sig_speed_updated.connect(self._on_speed_update)
        self.bridge.sig_task_completed.connect(self._on_task_completed)
        self.bridge.sig_log_message.connect(self._append_log)

    def _run_operation(
        self,
        key: str,
        operation: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        worker_key = f"{key}:{self._operation_sequence}"
        self._operation_sequence += 1
        worker = _Operation(worker_key, operation, args, kwargs)
        worker.signals.finished.connect(self._on_operation_finished)
        worker.signals.failed.connect(self._on_operation_failed)
        self._workers[worker_key] = worker
        self._append_log("INFO", f"{key.replace('_', ' ').capitalize()} started")
        self._pool.start(worker)

    @pyqtSlot(str, object)
    def _on_operation_finished(self, key: str, result: Any) -> None:
        self._workers.pop(key, None)
        self._append_log("INFO", f"{key.split(':', 1)[0].replace('_', ' ').capitalize()} finished")
        self.refresh_tasks()

    @pyqtSlot(str, str)
    def _on_operation_failed(self, key: str, error: str) -> None:
        self._workers.pop(key, None)
        self._append_log("ERROR", f"{key.split(':', 1)[0]} failed: {error}")
        QMessageBox.critical(self, "Torrent operation failed", error)

    def _create_torrent(self) -> None:
        dialog = CreateTorrentDialog(self)
        if dialog.exec() == CreateTorrentDialog.DialogCode.Accepted:
            self._run_operation(
                "create_and_seed",
                self.manager.create_and_seed,
                dialog.file_path,
                piece_size=dialog.piece_size,
            )

    def _open_torrent(self) -> None:
        dialog = OpenTorrentDialog(self)
        if dialog.exec() == OpenTorrentDialog.DialogCode.Accepted:
            self._run_operation("add_torrent", self.manager.add_torrent, dialog.metadata_path)

    def _selected_file_id(self) -> str | None:
        row = self.torrent_table.currentRow()
        if row < 0:
            return None
        item = self.torrent_table.item(row, 0)
        return str(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _pause_selected(self) -> None:
        file_id = self._selected_file_id()
        if file_id:
            self._run_operation("pause_torrent", self.manager.pause_torrent, file_id)

    def _resume_selected(self) -> None:
        file_id = self._selected_file_id()
        if file_id:
            self._run_operation("resume_torrent", self.manager.resume_torrent, file_id)

    def _remove_selected(self) -> None:
        file_id = self._selected_file_id()
        if not file_id:
            return
        answer = QMessageBox.question(
            self,
            "Remove torrent",
            "Remove the selected torrent from this client?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._run_operation("remove_torrent", self.manager.remove_torrent, file_id)

    def _task_file_id(self, task: Any) -> str:
        metadata = getattr(task, "metadata", None)
        piece_manager = getattr(task, "piece_manager", None)
        file_id = getattr(metadata, "file_id", None) or getattr(piece_manager, "file_id", None)
        if file_id is None:
            raise ValueError("Torrent task does not expose a file_id")
        return str(file_id)

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if value < 1024 or unit == "TiB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024
        return f"{value:.1f} TiB"

    @staticmethod
    def _format_speed(speed: float) -> str:
        return f"{MainWindow._format_size(max(0, speed))}/s"

    def refresh_tasks(self) -> None:
        try:
            tasks = self.manager.get_all_tasks()
        except Exception as exc:
            self._append_log("ERROR", f"Could not load torrents: {exc}")
            return

        selected_id = self._selected_file_id()
        task_map = {self._task_file_id(task): task for task in tasks}
        self._tasks_by_id = task_map
        self._row_by_id = {}
        self.torrent_table.setRowCount(len(tasks))

        for row, task in enumerate(tasks):
            file_id = self._task_file_id(task)
            self._row_by_id[file_id] = row
            metadata = getattr(task, "metadata", None)
            piece_manager = getattr(task, "piece_manager", None)
            file_name = getattr(metadata, "file_name", None) or getattr(piece_manager, "file_name", file_id)
            file_size = getattr(metadata, "file_size", None)
            if file_size is None:
                file_size = getattr(piece_manager, "file_size", 0)
            downloaded = (
                piece_manager.get_downloaded_bytes()
                if piece_manager and hasattr(piece_manager, "get_downloaded_bytes")
                else getattr(task, "downloaded_bytes", 0)
            )
            total = int(file_size or 0)
            progress = 100.0 if total == 0 and getattr(task, "status", "") == "completed" else (
                min(100.0, downloaded * 100.0 / total) if total else 0.0
            )
            values = (
                str(file_name),
                self._format_size(total),
                f"{progress:.1f}%",
                self._format_speed(getattr(task, "download_speed", 0.0)),
                self._format_speed(getattr(task, "upload_speed", 0.0)),
                str(getattr(task, "status", "unknown")).capitalize(),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, file_id)
                self.torrent_table.setItem(row, column, item)

        if selected_id in self._row_by_id:
            self.torrent_table.selectRow(self._row_by_id[selected_id])
        elif tasks:
            self.torrent_table.selectRow(0)
        else:
            self._active_file_id = None
            self.piece_grid.set_active_file("", 0, [])

    @pyqtSlot()
    def _on_selection_changed(self) -> None:
        file_id = self._selected_file_id()
        if not file_id or file_id == self._active_file_id:
            return
        task = self._tasks_by_id.get(file_id)
        if task is None:
            return
        self._active_file_id = file_id
        metadata = getattr(task, "metadata", None)
        piece_manager = getattr(task, "piece_manager", None)
        total_pieces = int(
            getattr(metadata, "total_pieces", None)
            or getattr(piece_manager, "total_pieces", 0)
        )
        bitfield = (
            piece_manager.get_bitfield()
            if piece_manager and hasattr(piece_manager, "get_bitfield")
            else getattr(piece_manager, "bitfield", [0] * total_pieces)
        )
        self.piece_grid.set_active_file(file_id, total_pieces, bitfield)
        states = getattr(piece_manager, "piece_states", []) if piece_manager else []
        for index, state in enumerate(states):
            status = getattr(state, "name", str(state)).lower()
            if status in self.piece_grid.COLORS:
                self.piece_grid.update_piece_status(file_id, index, status)

    @pyqtSlot(str, int, str)
    def _on_chunk_update(self, file_id: str, index: int, status: str) -> None:
        self.piece_grid.update_piece_status(file_id, index, status)
        self._append_log("INFO", f"Piece {index} {status} for {file_id[:12]}")

    @pyqtSlot(str, int, int)
    def _on_progress_update(self, file_id: str, downloaded: int, total: int) -> None:
        row = self._row_by_id.get(file_id)
        if row is None:
            return
        percent = min(100.0, downloaded * 100.0 / total) if total else 0.0
        self.torrent_table.item(row, 2).setText(f"{percent:.1f}%")

    @pyqtSlot(str, float, float)
    def _on_speed_update(self, file_id: str, download_speed: float, upload_speed: float) -> None:
        row = self._row_by_id.get(file_id)
        if row is None:
            return
        self.torrent_table.item(row, 3).setText(self._format_speed(download_speed))
        self.torrent_table.item(row, 4).setText(self._format_speed(upload_speed))

    @pyqtSlot(str, str)
    def _on_task_completed(self, file_id: str, output_path: str) -> None:
        self._append_log("INFO", f"Completed {file_id[:12]}: {output_path}")
        self.refresh_tasks()

    @pyqtSlot(str, str)
    def _append_log(self, level: str, message: str) -> None:
        self.log_view.append(f"[{level.upper()}] {message}")

    def closeEvent(self, event) -> None:
        self._refresh_timer.stop()
        self.bridge.close()
        super().closeEvent(event)
