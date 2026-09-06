"""
A small, self-contained icon set in the Lucide/Feather style (thin 2px
stroke, 24x24 viewBox) -- the line-icon look used across most modern
desktop/SaaS UI today. Bundled as inline SVG path data (no asset files,
no extra pip dependency, no network fetch) so every icon can be recolored
to match the current theme and rendered at exactly the size needed.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel

_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{color}" stroke-width="{weight}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
)

# name -> inner SVG body (paths/shapes only). Sourced from the Lucide
# icon set's path geometry (ISC-licensed), reproduced here as plain path
# data -- no image assets, no bundled font, no network call.
_ICONS: dict[str, str] = {
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
    "plus-circle": '<circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/>',
    "book-open": '<path d="M2 4.5A2.5 2.5 0 0 1 4.5 2H9a2.5 2.5 0 0 1 2.5 2.5v15A2 2 0 0 0 9.5 17H2zM22 4.5A2.5 2.5 0 0 0 19.5 2H15a2.5 2.5 0 0 0-2.5 2.5v15a2 2 0 0 1 2-2h7.5z"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    "check-circle": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="M22 4 12 14.01l-3-3"/>',
    "bar-chart": '<path d="M12 20V10M18 20V4M6 20v-4"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5M12 15V3"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "trash": '<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6"/><path d="M10 11v6M14 11v6"/>',
    "edit": '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4z"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "award": '<circle cx="12" cy="8" r="6"/><path d="M15.5 13.5 17 22l-5-3-5 3 1.5-8.5"/>',
    "layers": '<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/>',
    "folder": '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>',
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "x-circle": '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/>',
    "refresh": '<path d="M21 12a9 9 0 0 1-15.5 6.36M3 12a9 9 0 0 1 15.5-6.36"/><path d="M21 3v6h-6M3 21v-6h6"/>',
    "moon": '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/>',
    "sun": '<circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>',
    "zap": '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z"/>',
    "shield-check": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    "arrow-left": '<path d="M19 12H5M12 19l-7-7 7-7"/>',
    "filter": '<path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3Z"/>',
    "message-square": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z"/>',
    "save": '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
    "upload-cloud": '<path d="M4 14.9A5 5 0 0 1 6 5.03 6 6 0 0 1 17.9 8H19a4 4 0 0 1 1 7.87"/><path d="M12 12v9M9 16l3-3 3 3"/>',
    "file-text": '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5Z"/><path d="M14 2v6h6M9 13h6M9 17h6M9 9h1"/>',
    "alert-triangle": '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><path d="M12 9v4M12 17h.01"/>',
    "inbox": '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z"/>',
    "sparkles": '<path d="m12 3-1.9 4.9L5 9.8l4.9 1.9L12 17l1.9-4.9 4.9-1.9-4.9-1.9Z"/><path d="M5 3v4M19 17v4M3 19h4M17 5h4"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    "more-horizontal": '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
    "graduation-cap": '<path d="M22 10 12 5 2 10l10 5 10-5Z"/><path d="M6 12v5c0 1.1 2.7 3 6 3s6-1.9 6-3v-5"/>',
}


def svg_source(name: str, color: str, weight: float = 2.0) -> str:
    body = _ICONS.get(name, _ICONS["info"])
    return _TEMPLATE.format(color=color, weight=weight, body=body)


def pixmap(name: str, color: str, size: int = 20, weight: float = 2.0) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg_source(name, color, weight).encode("utf-8")))
    dpr = 2  # render at 2x and mark as such, so icons stay crisp on hi-DPI displays
    pix = QPixmap(QSize(size * dpr, size * dpr))
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Explicit target rect in LOGICAL pixels (size x size), not physical --
    # renderer.render(painter) with no rect double-applies the pixmap's own
    # devicePixelRatio scale on top of the painter's already-DPR-aware
    # transform, so only a corner of the icon ends up visible. Passing the
    # rect explicitly avoids that ambiguity entirely.
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pix


def icon(name: str, color: str, size: int = 20, weight: float = 2.0) -> QIcon:
    return QIcon(pixmap(name, color, size, weight))


def icon_label(name: str, color: str, size: int = 20, weight: float = 2.0) -> QLabel:
    lbl = QLabel()
    lbl.setPixmap(pixmap(name, color, size, weight))
    lbl.setFixedSize(size, size)
    return lbl
