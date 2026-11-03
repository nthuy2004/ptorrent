from __future__ import annotations

from math import ceil

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget


class PieceGrid(QWidget):
    COLORS = {
        "pending": QColor("#e0e0e0"),
        "downloading": QColor("#fbc02d"),
        "completed": QColor("#4caf50"),
        "corrupted": QColor("#e53935"),
    }

    CELL_SIZE = 16
    CELL_GAP = 4
    MARGIN = 8

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.file_id: str | None = None
        self._statuses: list[str] = []
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setMinimumWidth(180)
        self.setMinimumHeight(self.CELL_SIZE + self.MARGIN * 2)
        self.setAccessibleName("Torrent piece availability grid")

    @property
    def piece_statuses(self) -> tuple[str, ...]:
        return tuple(self._statuses)

    def set_active_file(
        self,
        file_id: str,
        total_pieces: int,
        current_bitfield: list[int],
    ) -> None:
        if total_pieces < 0:
            raise ValueError("total_pieces must be non-negative")

        bitfield = list(current_bitfield[:total_pieces])
        bitfield.extend([0] * (total_pieces - len(bitfield)))
        self.file_id = file_id
        self._statuses = ["completed" if bit == 1 else "pending" for bit in bitfield]
        self.updateGeometry()
        self.update()

    def update_piece_status(self, file_id: str, index: int, status: str) -> bool:
        if file_id != self.file_id or not 0 <= index < len(self._statuses):
            return False
        if status not in self.COLORS:
            return False

        self._statuses[index] = status
        self.update()
        return True

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        columns = self._column_count(width)
        rows = max(1, ceil(len(self._statuses) / columns))
        return self.MARGIN * 2 + rows * self.CELL_SIZE + max(0, rows - 1) * self.CELL_GAP

    def sizeHint(self) -> QSize:
        width = 640
        return QSize(width, self.heightForWidth(width))

    def _column_count(self, width: int) -> int:
        available = max(1, width - self.MARGIN * 2)
        return max(1, (available + self.CELL_GAP) // (self.CELL_SIZE + self.CELL_GAP))

    def _cell_rect(self, index: int, columns: int) -> QRect:
        x = self.MARGIN + (index % columns) * (self.CELL_SIZE + self.CELL_GAP)
        y = self.MARGIN + (index // columns) * (self.CELL_SIZE + self.CELL_GAP)
        return QRect(x, y, self.CELL_SIZE, self.CELL_SIZE)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(QPen(QColor("#616161"), 1))
        columns = self._column_count(self.width())

        for index, status in enumerate(self._statuses):
            rect = self._cell_rect(index, columns)
            painter.fillRect(rect, self.COLORS[status])
            painter.drawRect(rect)

        painter.end()
