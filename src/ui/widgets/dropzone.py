from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFileDialog, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from src.services.grading_service import SUPPORTED_SUFFIXES


class DropZone(QFrame):
    """Drag & drop target + Browse button. Validates extensions before
    accepting -- rejected files get a signal with a clear reason, per
    spec (never a silent no-op)."""

    files_accepted = Signal(list)   # list[Path]
    files_rejected = Signal(list)   # list[str] human-readable reasons

    def __init__(
        self, title: str = "Drag & drop files here",
        subtitle_text: str = "or click Browse to select files",
        allow_folders: bool = False, multiple: bool = True, parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._allow_folders = allow_folders
        self._multiple = multiple
        self.setAcceptDrops(True)
        self.setProperty("cls", "dropzone")
        self.setMinimumHeight(140)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        self._title_label = QLabel(title)
        self._title_label.setProperty("cls", "h3")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._sub_label = QLabel(subtitle_text)
        self._sub_label.setProperty("cls", "muted")
        self._sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        browse_btn = QPushButton("Browse files" + (" or folder" if allow_folders else ""))
        browse_btn.setProperty("cls", "primary")
        browse_btn.setFixedWidth(200)
        browse_btn.clicked.connect(self._browse)

        layout.addWidget(self._title_label)
        layout.addWidget(self._sub_label)
        layout.addSpacing(4)
        layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _browse(self) -> None:
        if self._multiple:
            paths, _ = QFileDialog.getOpenFileNames(self, "Select files")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Select file")
            paths = [path] if path else []
        if paths:
            self._validate_and_emit([Path(p) for p in paths])

    def dragEnterEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("cls", "dropzoneActive")
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self.setProperty("cls", "dropzone")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event) -> None:  # noqa: N802
        self.setProperty("cls", "dropzone")
        self.style().unpolish(self)
        self.style().polish(self)
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                paths.append(Path(local))
        self._validate_and_emit(paths)

    def _validate_and_emit(self, paths: list[Path]) -> None:
        accepted: list[Path] = []
        rejected: list[str] = []
        for p in paths:
            if p.is_dir():
                if self._allow_folders:
                    for child in sorted(p.iterdir()):
                        if child.is_file() and child.suffix.lower() in SUPPORTED_SUFFIXES:
                            accepted.append(child)
                else:
                    rejected.append(f"'{p.name}' is a folder -- drop individual files here.")
                continue
            if p.suffix.lower() in SUPPORTED_SUFFIXES:
                accepted.append(p)
            else:
                rejected.append(
                    f"'{p.name}' isn't a supported file type. "
                    "Supported formats: PDF, DOCX, TXT, PNG, JPG, JPEG, TIFF, BMP."
                )
        if accepted:
            self.files_accepted.emit(accepted)
        if rejected:
            self.files_rejected.emit(rejected)
