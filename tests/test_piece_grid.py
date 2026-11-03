import os
import sys

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QColor, QImage, QPainter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from client.gui.piece_grid import PieceGrid


def test_active_file_snapshot_and_incremental_updates(qapp):
    grid = PieceGrid()
    grid.set_active_file("file-a", 4, [1, 0, 1])

    assert grid.piece_statuses == ("completed", "pending", "completed", "pending")
    assert grid.update_piece_status("other-file", 1, "downloading") is False
    assert grid.update_piece_status("file-a", 4, "completed") is False
    assert grid.update_piece_status("file-a", 1, "downloading") is True
    assert grid.update_piece_status("file-a", 1, "corrupted") is True
    assert grid.piece_statuses[1] == "corrupted"


def test_grid_reflows_rows_for_narrow_width(qapp):
    grid = PieceGrid()
    grid.set_active_file("file-a", 100, [0] * 100)

    assert grid.hasHeightForWidth()
    assert grid.heightForWidth(220) > grid.heightForWidth(640)


def test_render_uses_documented_piece_colors(qapp):
    grid = PieceGrid()
    grid.set_active_file("file-a", 4, [0, 1, 0, 0])
    grid.resize(200, grid.heightForWidth(200))

    image = QImage(grid.size(), QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    grid.render(painter)
    painter.end()

    pending = image.pixelColor(QPoint(12, 12))
    completed = image.pixelColor(QPoint(32, 12))
    assert pending == PieceGrid.COLORS["pending"]
    assert completed == PieceGrid.COLORS["completed"]
