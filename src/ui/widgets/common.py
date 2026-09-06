from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from src.ui.icons import icon, icon_label


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


_BADGE_ICONS = {"success": "check", "warning": "alert-triangle", "danger": "x-circle", "neutral": None}
_BADGE_COLORS_DARK = {"success": "#10B981", "warning": "#F59E0B", "danger": "#EF4444", "neutral": "#9CA3AF"}


def badge(text: str, variant: str = "neutral", with_icon: bool = False) -> QWidget:
    """A small rounded status pill. Pass with_icon=True for a leading
    check/alert/x glyph matching the variant (used where the icon adds
    real scannability -- long status tables, review reason chips)."""
    if not with_icon:
        lbl = QLabel(text)
        lbl.setProperty("cls", f"badge-{variant}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    wrapper = QFrame()
    wrapper.setProperty("cls", f"badge-{variant}")
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(7, 1, 9, 1)
    layout.setSpacing(4)
    icon_name = _BADGE_ICONS.get(variant)
    if icon_name:
        layout.addWidget(icon_label(icon_name, _BADGE_COLORS_DARK.get(variant, "#9CA3AF"), 11, weight=2.5))
    lbl = QLabel(text)
    lbl.setStyleSheet("background: transparent; border: none; font-size: 11px; font-weight: 600;")
    layout.addWidget(lbl)
    return wrapper


class Card(QFrame):
    """A rounded, bordered panel with real elevation (drop shadow) that
    lifts slightly on hover -- the depth cue most flat Qt apps skip."""

    def __init__(self, flat: bool = False, padding: int = 16, spacing: int = 8, hoverable: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("cls", "cardFlat" if flat else "card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(padding, padding, padding, padding)
        self.body.setSpacing(spacing)

        self._hoverable = hoverable
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(18 if flat else 24)
        self._shadow.setOffset(0, 4)
        self._shadow.setColor(QColor(0, 0, 0, 70))
        self.setGraphicsEffect(self._shadow)

    def enterEvent(self, event) -> None:  # noqa: N802
        if self._hoverable:
            self._shadow.setBlurRadius(34)
            self._shadow.setOffset(0, 8)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self._hoverable:
            self._shadow.setBlurRadius(24)
            self._shadow.setOffset(0, 4)
        super().leaveEvent(event)


class StatCard(Card):
    """Dashboard-style 'total exams' / 'average score' style tile, with
    a leading icon in an accent-tinted chip."""

    def __init__(self, label: str, value: str, icon_name: str | None = None, trend: str | None = None, variant: str = "neutral", parent=None):
        super().__init__(padding=16, spacing=6, hoverable=True, parent=parent)
        top_row = QHBoxLayout()
        if icon_name:
            chip = QFrame()
            chip.setFixedSize(34, 34)
            color = {"success": "#10B981", "warning": "#F59E0B", "danger": "#EF4444"}.get(variant, "#4F46E5")
            chip.setStyleSheet(f"background-color: {color}22; border-radius: 9px; border: none;")
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(0, 0, 0, 0)
            chip_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip_layout.addWidget(icon_label(icon_name, color, 17))
            top_row.addWidget(chip)
        top_row.addStretch()
        if trend:
            top_row.addWidget(badge(trend, variant))
        self.body.addLayout(top_row)

        self.body.addWidget(muted(label.upper()))
        value_lbl = QLabel(value)
        value_lbl.setProperty("cls", "statValue")
        self.body.addWidget(value_lbl)
        self.value_label = value_lbl

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class EmptyState(QWidget):
    """Centered empty state with a large muted icon illustration, a
    title, description, and optional action button."""

    def __init__(self, title: str, description: str, action: QWidget | None = None, icon_name: str = "inbox", parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.addStretch()
        inner = QVBoxLayout()
        inner.setSpacing(6)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_row = QHBoxLayout()
        icon_row.addStretch()
        big_icon = icon_label(icon_name, "#6B7280", 40, weight=1.5)
        icon_row.addWidget(big_icon)
        icon_row.addStretch()
        inner.addLayout(icon_row)
        inner.addSpacing(4)

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


def clear_layout(layout) -> None:
    """Removes every widget from a layout, hiding each immediately.
    deleteLater() alone schedules deletion for the next event-loop
    cycle but leaves the widget visible at its last geometry until
    then -- on a fast refresh (e.g. re-filtering a list) this shows
    the old and new content overlapping for a frame. hide() makes the
    removal take effect immediately; deleteLater() still reclaims it."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.hide()
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


_BUTTON_ICON_COLORS = {"primary": "#FFFFFF", "danger": "#EF4444", "ghost": "#9CA3AF", "default": "#9CA3AF"}


def icon_button(text: str, icon_name: str | None = None, cls: str = "default") -> QPushButton:
    """A QPushButton with a leading line-icon and a pointing-hand cursor
    -- the two small touches that make buttons feel clickable rather
    than decorative in a default Qt app."""
    btn = QPushButton(f"  {text}" if icon_name else text)
    if cls != "default":
        btn.setProperty("cls", cls)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if icon_name:
        btn.setIcon(icon(icon_name, _BUTTON_ICON_COLORS.get(cls, "#9CA3AF"), 15))
    return btn


def add_leading_icon(line_edit, icon_name: str, color: str = "#6B7280") -> None:
    """Puts a small line-icon inside the left edge of a QLineEdit --
    the "search bar with a magnifier" look every modern app uses."""
    from PySide6.QtWidgets import QLineEdit

    action = line_edit.addAction(icon(icon_name, color, 15), QLineEdit.ActionPosition.LeadingPosition)
    return action
