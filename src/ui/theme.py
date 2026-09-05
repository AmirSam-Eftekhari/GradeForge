"""
GradeForge visual theme.

One accent (indigo) and one semantic success/warning/danger triad, shared
with src/reports/pdf_report.py's PDF colors so the desktop app and the
exported PDF reports feel like the same product. Dark is the default
per spec; light is fully supported via the same Palette shape.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    bg: str
    bg_elevated: str
    bg_elevated_2: str
    bg_hover: str
    border: str
    border_strong: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_text: str
    success: str
    success_bg: str
    warning: str
    warning_bg: str
    danger: str
    danger_bg: str
    sidebar_bg: str


DARK = Palette(
    bg="#0F1115",
    bg_elevated="#181B22",
    bg_elevated_2="#20242D",
    bg_hover="#262B35",
    border="#2A2F3A",
    border_strong="#3A4152",
    text_primary="#E7E9EE",
    text_secondary="#9CA3AF",
    text_muted="#6B7280",
    accent="#4F46E5",
    accent_hover="#6366F1",
    accent_text="#FFFFFF",
    success="#10B981",
    success_bg="#0F2E27",
    warning="#F59E0B",
    warning_bg="#2E2410",
    danger="#EF4444",
    danger_bg="#301418",
    sidebar_bg="#14161C",
)

LIGHT = Palette(
    bg="#F7F8FA",
    bg_elevated="#FFFFFF",
    bg_elevated_2="#F3F4F6",
    bg_hover="#EEF0F3",
    border="#E5E7EB",
    border_strong="#D1D5DB",
    text_primary="#111827",
    text_secondary="#4B5563",
    text_muted="#9CA3AF",
    accent="#4F46E5",
    accent_hover="#4338CA",
    accent_text="#FFFFFF",
    success="#059669",
    success_bg="#ECFDF5",
    warning="#D97706",
    warning_bg="#FFFBEB",
    danger="#DC2626",
    danger_bg="#FEF2F2",
    sidebar_bg="#FFFFFF",
)


def build_stylesheet(p: Palette) -> str:
    return f"""
QWidget {{
    background-color: {p.bg};
    color: {p.text_primary};
    font-family: "Segoe UI", "Vazirmatn", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}}
QMainWindow, #centralArea {{ background-color: {p.bg}; }}

/* ---- Sidebar ---- */
#sidebar {{
    background-color: {p.sidebar_bg};
    border-right: 1px solid {p.border};
}}
#sidebarTitle {{
    color: {p.text_primary};
    font-size: 16px;
    font-weight: 700;
}}
#sidebarTagline {{
    color: {p.text_muted};
    font-size: 10.5px;
}}
QListWidget#navList {{
    background: transparent;
    border: none;
    outline: none;
    padding: 6px;
}}
QListWidget#navList::item {{
    padding: 9px 12px;
    border-radius: 8px;
    margin: 2px 0px;
    color: {p.text_secondary};
}}
QListWidget#navList::item:hover {{
    background-color: {p.bg_hover};
    color: {p.text_primary};
}}
QListWidget#navList::item:selected {{
    background-color: {p.accent};
    color: {p.accent_text};
    font-weight: 600;
}}

/* ---- Typography helpers (set via setProperty("class", ...)) ---- */
QLabel[cls="h1"] {{ font-size: 22px; font-weight: 700; color: {p.text_primary}; }}
QLabel[cls="h2"] {{ font-size: 16px; font-weight: 600; color: {p.text_primary}; }}
QLabel[cls="h3"] {{ font-size: 13px; font-weight: 600; color: {p.text_primary}; }}
QLabel[cls="subtitle"] {{ font-size: 12.5px; color: {p.text_secondary}; }}
QLabel[cls="muted"] {{ font-size: 11.5px; color: {p.text_muted}; }}
QLabel[cls="statValue"] {{ font-size: 26px; font-weight: 700; color: {p.text_primary}; }}
QLabel[cls="statLabel"] {{ font-size: 11px; color: {p.text_muted}; font-weight: 600; letter-spacing: 0.4px; }}
QLabel[cls="mono"] {{ font-family: "Consolas", "Menlo", monospace; color: {p.text_secondary}; }}

/* ---- Cards ---- */
QFrame[cls="card"] {{
    background-color: {p.bg_elevated};
    border: 1px solid {p.border};
    border-radius: 12px;
}}
QFrame[cls="cardFlat"] {{
    background-color: {p.bg_elevated_2};
    border: 1px solid {p.border};
    border-radius: 10px;
}}
QFrame[cls="dropzone"] {{
    background-color: {p.bg_elevated_2};
    border: 2px dashed {p.border_strong};
    border-radius: 12px;
}}
QFrame[cls="dropzoneActive"] {{
    background-color: {p.accent};
    border: 2px dashed {p.accent_hover};
    border-radius: 12px;
}}
QFrame[cls="hline"] {{ background-color: {p.border}; max-height: 1px; min-height: 1px; }}

/* ---- Buttons ---- */
QPushButton {{
    background-color: {p.bg_elevated_2};
    color: {p.text_primary};
    border: 1px solid {p.border_strong};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
}}
QPushButton:hover {{ background-color: {p.bg_hover}; }}
QPushButton:disabled {{ color: {p.text_muted}; border-color: {p.border}; }}
QPushButton[cls="primary"] {{
    background-color: {p.accent};
    border: 1px solid {p.accent};
    color: {p.accent_text};
    font-weight: 600;
}}
QPushButton[cls="primary"]:hover {{ background-color: {p.accent_hover}; }}
QPushButton[cls="primary"]:disabled {{ background-color: {p.bg_elevated_2}; color: {p.text_muted}; border-color: {p.border}; }}
QPushButton[cls="danger"] {{ color: {p.danger}; border-color: {p.danger}; background-color: transparent; }}
QPushButton[cls="danger"]:hover {{ background-color: {p.danger_bg}; }}
QPushButton[cls="ghost"] {{ background-color: transparent; border: 1px solid transparent; }}
QPushButton[cls="ghost"]:hover {{ background-color: {p.bg_hover}; }}
QPushButton[cls="navPill"] {{ border-radius: 14px; padding: 5px 12px; font-size: 11.5px; }}

/* ---- Inputs ---- */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {p.bg_elevated_2};
    border: 1px solid {p.border_strong};
    border-radius: 8px;
    padding: 6px 10px;
    color: {p.text_primary};
    selection-background-color: {p.accent};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
    border: 1px solid {p.accent};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: {p.bg_elevated_2};
    border: 1px solid {p.border_strong};
    selection-background-color: {p.accent};
    color: {p.text_primary};
    outline: none;
}}

/* ---- Tables ---- */
QTableWidget, QTableView {{
    background-color: {p.bg_elevated};
    alternate-background-color: {p.bg_elevated_2};
    border: 1px solid {p.border};
    border-radius: 10px;
    gridline-color: {p.border};
    selection-background-color: {p.accent};
    selection-color: {p.accent_text};
}}
QHeaderView::section {{
    background-color: {p.bg_elevated_2};
    color: {p.text_secondary};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {p.border};
    font-weight: 600;
    font-size: 11.5px;
}}
QTableWidget::item, QTableView::item {{ padding: 4px; }}

/* ---- Lists ---- */
QListWidget {{
    background-color: {p.bg_elevated};
    border: 1px solid {p.border};
    border-radius: 10px;
}}

/* ---- Tabs ---- */
QTabWidget::pane {{ border: 1px solid {p.border}; border-radius: 10px; top: -1px; }}
QTabBar::tab {{
    background: transparent;
    color: {p.text_secondary};
    padding: 8px 16px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {p.text_primary}; border-bottom: 2px solid {p.accent}; font-weight: 600; }}
QTabBar::tab:hover {{ color: {p.text_primary}; }}

/* ---- Progress ---- */
QProgressBar {{
    background-color: {p.bg_elevated_2};
    border: 1px solid {p.border};
    border-radius: 8px;
    text-align: center;
    color: {p.text_primary};
    height: 16px;
}}
QProgressBar::chunk {{ background-color: {p.accent}; border-radius: 7px; }}

/* ---- Scrollbars ---- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {p.border_strong}; border-radius: 5px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {p.text_muted}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: {p.border_strong}; border-radius: 5px; min-width: 24px; }}

/* ---- Badges (QLabel with cls="badge-<variant>") ---- */
QLabel[cls="badge-neutral"] {{
    background-color: {p.bg_elevated_2}; color: {p.text_secondary};
    border: 1px solid {p.border_strong}; border-radius: 9px; padding: 1px 8px; font-size: 11px; font-weight: 600;
}}
QLabel[cls="badge-success"] {{
    background-color: {p.success_bg}; color: {p.success};
    border: 1px solid {p.success}; border-radius: 9px; padding: 1px 8px; font-size: 11px; font-weight: 600;
}}
QLabel[cls="badge-warning"] {{
    background-color: {p.warning_bg}; color: {p.warning};
    border: 1px solid {p.warning}; border-radius: 9px; padding: 1px 8px; font-size: 11px; font-weight: 600;
}}
QLabel[cls="badge-danger"] {{
    background-color: {p.danger_bg}; color: {p.danger};
    border: 1px solid {p.danger}; border-radius: 9px; padding: 1px 8px; font-size: 11px; font-weight: 600;
}}

/* ---- Tooltips ---- */
QToolTip {{
    background-color: {p.bg_elevated_2};
    color: {p.text_primary};
    border: 1px solid {p.border_strong};
    padding: 6px 8px;
    border-radius: 6px;
}}

QSplitter::handle {{ background-color: {p.border}; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid {p.border_strong}; background-color: {p.bg_elevated_2};
}}
QCheckBox::indicator:checked {{ background-color: {p.accent}; border-color: {p.accent}; }}

QRadioButton::indicator {{
    width: 16px; height: 16px; border-radius: 8px;
    border: 1px solid {p.border_strong}; background-color: {p.bg_elevated_2};
}}
QRadioButton::indicator:checked {{ background-color: {p.accent}; border: 4px solid {p.bg_elevated_2}; outline: 1px solid {p.accent}; }}
"""


def palette_for(theme_name: str) -> Palette:
    return LIGHT if theme_name == "light" else DARK


def score_color(pct: float, p: Palette) -> str:
    if pct >= 80:
        return p.success
    if pct >= 50:
        return p.warning
    return p.danger
