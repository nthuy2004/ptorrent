from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class CreateTorrentDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Create torrent")
        self.setMinimumWidth(460)

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_file)

        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse_button)

        self.piece_size_spin = QSpinBox()
        self.piece_size_spin.setRange(16, 8192)
        self.piece_size_spin.setValue(256)
        self.piece_size_spin.setSuffix(" KiB")

        form = QFormLayout()
        form.addRow("Source file", path_row)
        form.addRow("Piece size", self.piece_size_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def file_path(self) -> str:
        return self.path_edit.text()

    @property
    def piece_size(self) -> int:
        return self.piece_size_spin.value() * 1024

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select source file")
        if path:
            self.path_edit.setText(path)

    def _accept_if_valid(self) -> None:
        if not self.file_path:
            QMessageBox.warning(self, "Source file required", "Choose a source file first.")
            return
        self.accept()


class OpenTorrentDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Open torrent metadata")
        self.setMinimumWidth(460)

        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_file)

        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse_button)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(path_row)
        layout.addWidget(buttons)

    @property
    def metadata_path(self) -> str:
        return self.path_edit.text()

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select torrent metadata",
            filter="Torrent metadata (*.ptorrent *.json);;All files (*)",
        )
        if path:
            self.path_edit.setText(path)

    def _accept_if_valid(self) -> None:
        if not self.metadata_path:
            QMessageBox.warning(self, "Metadata required", "Choose a metadata file first.")
            return
        self.accept()
