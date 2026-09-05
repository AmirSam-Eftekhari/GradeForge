from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


def _label(text: str, cls: str, parent: QWidget | None = None) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setProperty("cls", cls)
    lbl.setWordWrap(True)
    return lbl


def h1(text: str) -> QLabel:
    return _label(text, "h1")


def h2(text: str) -> QLabel:
    return _label(text, "h2")


def h3(text: str) -> QLabel:
    return _label(text, "h3")


def subtitle(text: str) -> QLabel:
    return _label(text, "subtitle")


def muted(text: str) -> QLabel:
    return _label(text, "muted")


def mono(text: str) -> QLabel:
    return _label(text, "mono")


def hline() -> QFrame:
    line = QFrame()
    line.setProperty("cls", "hline")
    line.setFixedHeight(1)
    return line


def badge(text: str, variant: str = "neutral") -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("cls", f"badge-{variant}")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


class Card(QFrame):
    """A rounded, bordered panel. Use .body for its inner QVBoxLayout."""

    def __init__(self, flat: bool = False, padding: int = 16, spacing: int = 8, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("cls", "cardFlat" if flat else "card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(padding, padding, padding, padding)
        self.body.setSpacing(spacing)


class StatCard(Card):
    """Dashboard-style 'total exams' / 'average score' style tile."""

    def __init__(self, label: str, value: str, trend: str | None = None, variant: str = "neutral", parent=None):
        super().__init__(padding=16, spacing=4, parent=parent)
        self.body.addWidget(muted(label.upper()))
        row = QHBoxLayout()
        value_lbl = QLabel(value)
        value_lbl.setProperty("cls", "statValue")
        row.addWidget(value_lbl)
        row.addStretch()
        if trend:
            row.addWidget(badge(trend, variant))
        self.body.addLayout(row)
        self.value_label = value_lbl

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class EmptyState(QWidget):
    """Centered icon-free empty state: title + description + optional action button widget."""

    def __init__(self, title: str, description: str, action: QWidget | None = None, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.addStretch()
        inner = QVBoxLayout()
        inner.setSpacing(6)
        title_lbl = h2(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl = subtitle(description)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(title_lbl)
        inner.addWidget(desc_lbl)
        if action is not None:
            action_row = QHBoxLayout()
            action_row.addStretch()
            action_row.addWidget(action)
            action_row.addStretch()
            inner.addSpacing(6)
            inner.addLayout(action_row)
        wrapper = QHBoxLayout()
        wrapper.addStretch()
        wrapper.addLayout(inner)
        wrapper.addStretch()
        outer.addLayout(wrapper)
        outer.addStretch()


def spacer_widget() -> QWidget:
    w = QWidget()
    w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return w
