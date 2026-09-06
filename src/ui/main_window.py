from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from src.ui.app_context import AppContext
from src.ui.icons import icon
from src.ui.theme import build_stylesheet, palette_for
from src.ui.widgets.common import hline
from src.ui.widgets.toast import ToastManager

_NAV_ITEMS = [
    ("dashboard", "Dashboard", "grid"),
    ("new_grading", "New Grading", "plus-circle"),
    ("exams", "Exams", "book-open"),
    ("students", "Students", "users"),
    ("review", "Review", "check-circle"),
    ("analytics", "Analytics", "bar-chart"),
    ("reports", "Reports", "download"),
    ("settings", "Settings", "settings"),
]


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle("GradeForge")
        self.resize(1360, 860)
        self.setMinimumSize(QSize(980, 640))

        central = QWidget()
        central.setObjectName("centralArea")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        self._page_host = QWidget()
        page_layout = QVBoxLayout(self._page_host)
        page_layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        page_layout.addWidget(self.stack)
        root.addWidget(self._page_host, 1)

        self.setCentralWidget(central)
        self.toasts = ToastManager(central, palette_provider=lambda: palette_for(self.ctx.theme))

        self._pages: dict[str, QWidget] = {}
        self._nav_keys = {key for key, _, _ in _NAV_ITEMS}
        self._register_pages()

        ctx.signals.navigate.connect(self._on_navigate)
        ctx.signals.theme_changed.connect(lambda _: self._apply_theme())
        ctx.signals.toast_requested.connect(self.toasts.show)

        self._apply_theme()
        self._on_navigate("dashboard", {})

    # ------------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(224)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(2)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(8)
        self._logo_mark = QLabel()
        brand_row.addWidget(self._logo_mark)
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title = QLabel("GradeForge")
        title.setObjectName("sidebarTitle")
        tagline = QLabel("offline & explainable")
        tagline.setObjectName("sidebarTagline")
        title_col.addWidget(title)
        title_col.addWidget(tagline)
        brand_row.addLayout(title_col)
        brand_row.addStretch()
        layout.addLayout(brand_row)
        layout.addSpacing(16)
        layout.addWidget(hline())
        layout.addSpacing(10)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        self.nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_list.setIconSize(QSize(17, 17))
        self._nav_icon_names = {}
        for key, label, icon_name in _NAV_ITEMS:
            item = QListWidgetItem(f"  {label}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setSizeHint(QSize(-1, 40))
            self._nav_icon_names[key] = icon_name
            self.nav_list.addItem(item)
        self.nav_list.currentItemChanged.connect(self._on_nav_clicked)
        layout.addWidget(self.nav_list)
        layout.addStretch()

        layout.addWidget(hline())
        layout.addSpacing(8)
        theme_row = QHBoxLayout()
        self.theme_btn = QPushButton("  Light mode")
        self.theme_btn.setProperty("cls", "ghost")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        theme_row.addWidget(self.theme_btn)
        layout.addLayout(theme_row)

        version = QLabel("v1.0 · local & offline")
        version.setObjectName("sidebarTagline")
        layout.addWidget(version)
        return sidebar

    def _register_pages(self) -> None:
        # Imported lazily (not at module top) to avoid a circular import
        # between main_window and pages that navigate via ctx.
        from src.ui.pages.analytics import AnalyticsPage
        from src.ui.pages.dashboard import DashboardPage
        from src.ui.pages.exam_detail import ExamDetailPage
        from src.ui.pages.exam_history import ExamHistoryPage
        from src.ui.pages.grading_execution import GradingExecutionPage
        from src.ui.pages.new_grading.wizard import NewGradingWizard
        from src.ui.pages.reports import ReportsPage
        from src.ui.pages.review_center import ReviewCenterPage
        from src.ui.pages.settings_page import SettingsPage
        from src.ui.pages.student_history import StudentHistoryPage
        from src.ui.pages.student_result import StudentResultPage
        from src.ui.pages.students import StudentsPage

        page_classes = {
            "dashboard": DashboardPage,
            "new_grading": NewGradingWizard,
            "grading_execution": GradingExecutionPage,
            "exams": ExamHistoryPage,
            "exam_detail": ExamDetailPage,
            "students": StudentsPage,
            "student_history": StudentHistoryPage,
            "student_result": StudentResultPage,
            "review": ReviewCenterPage,
            "analytics": AnalyticsPage,
            "reports": ReportsPage,
            "settings": SettingsPage,
        }
        for key, cls in page_classes.items():
            page = cls(self.ctx)
            self._pages[key] = page
            self.stack.addWidget(page)

    def _on_nav_clicked(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            return
        key = current.data(Qt.ItemDataRole.UserRole)
        self.ctx.navigate(key)

    def _on_navigate(self, key: str, params: dict) -> None:
        page = self._pages.get(key)
        if page is None:
            return
        if hasattr(page, "on_show"):
            page.on_show(**params)

        if self.stack.currentWidget() is not page:
            self.stack.setCurrentWidget(page)

        if key in self._nav_keys:
            for i in range(self.nav_list.count()):
                item = self.nav_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == key:
                    self.nav_list.blockSignals(True)
                    self.nav_list.setCurrentItem(item)
                    self.nav_list.blockSignals(False)
                    break
            self._update_nav_icons()

    def _toggle_theme(self) -> None:
        self.ctx.set_theme("light" if self.ctx.theme == "dark" else "dark")

    def _apply_theme(self) -> None:
        palette = palette_for(self.ctx.theme)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(palette))

        self._logo_mark.setPixmap(icon("graduation-cap", palette.accent, 26).pixmap(26, 26))
        self.theme_btn.setText("  Light mode" if self.ctx.theme == "dark" else "  Dark mode")
        self.theme_btn.setIcon(icon("sun" if self.ctx.theme == "dark" else "moon", palette.text_secondary, 15))

        self._update_nav_icons()

    def _update_nav_icons(self) -> None:
        palette = palette_for(self.ctx.theme)
        for key, name in self._nav_icon_names.items():
            for i in range(self.nav_list.count()):
                item = self.nav_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == key:
                    selected = item.isSelected()
                    color = palette.accent_text if selected else palette.text_secondary
                    item.setIcon(icon(name, color, 17))
                    break

    def closeEvent(self, event) -> None:  # noqa: N802
        self.ctx.shutdown()
        super().closeEvent(event)
