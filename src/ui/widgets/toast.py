from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

from src.ui.icons import icon_label
from src.ui.theme import Palette

_ICONS = {"success": "check-circle", "warning": "alert-triangle", "danger": "x-circle", "info": "info"}


class Toast(QWidget):
    """One floating notification. Fades in, waits, fades out, then asks
    its manager to remove it -- used for non-blocking confirmations
    ("Report exported") so routine feedback doesn't interrupt the person
    with a modal dialog the way QMessageBox would."""

    def __init__(self, message: str, variant: str, palette: Palette, on_closed, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._on_closed = on_closed
        color = {"success": palette.success, "warning": palette.warning, "danger": palette.danger, "info": palette.accent}[variant]

        self.setStyleSheet(
            f"Toast {{ background-color: {palette.bg_elevated_2}; border: 1px solid {palette.border_strong}; "
            f"border-left: 3px solid {color}; border-radius: 10px; }}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 14, 10)
        layout.setSpacing(10)
        layout.addWidget(icon_label(_ICONS.get(variant, "info"), color, 18))
        label = QLabel(message)
        label.setStyleSheet(f"color: {palette.text_primary}; font-size: 12.5px; background: transparent; border: none;")
        label.setWordWrap(True)
        layout.addWidget(label, 1)
        self.setFixedWidth(320)
        self.adjustSize()

        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)

        self._fade_in = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_in.setDuration(180)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_out.setDuration(220)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self._finish)

    def play(self, lifetime_ms: int = 3200) -> None:
        self.show()
        self._fade_in.start()
        QTimer.singleShot(lifetime_ms, self._fade_out.start)

    def _finish(self) -> None:
        self._on_closed(self)
        self.deleteLater()


class ToastManager:
    """Stacks toasts bottom-right of the given host widget (the main
    window), repositioning the stack whenever one is added or removed."""

    def __init__(self, host: QWidget, palette_provider):
        self._host = host
        self._palette_provider = palette_provider
        self._active: list[Toast] = []

    def show(self, message: str, variant: str = "success") -> None:
        palette = self._palette_provider()
        toast = Toast(message, variant, palette, on_closed=self._remove, parent=self._host)
        self._active.append(toast)
        self._reposition()
        toast.play()

    def _remove(self, toast: Toast) -> None:
        if toast in self._active:
            self._active.remove(toast)
        self._reposition()

    def _reposition(self) -> None:
        margin = 20
        spacing = 10
        y = self._host.height() - margin
        for toast in reversed(self._active):
            y -= toast.sizeHint().height()
            toast.move(self._host.width() - toast.width() - margin, y)
            toast.raise_()
            y -= spacing
