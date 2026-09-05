from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QStackedWidget, QVBoxLayout, QWidget,
)

from src.ui.app_context import AppContext
from src.ui.theme import build_stylesheet, palette_for
from src.ui.widgets.common import hline

_NAV_ITEMS = [
    ("dashboard", "Dashboard"),
    ("new_grading", "New Grading"),
    ("exams", "Exams"),
    ("students", "Students"),
    ("review", "Review"),
    ("analytics", "Analytics"),
    ("reports", "Reports"),
    ("settings", "Settings"),
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

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.setCentralWidget(central)

        self._pages: dict[str, QWidget] = {}
        self._nav_keys = {key for key, _ in _NAV_ITEMS}
        self._register_pages()

        ctx.signals.navigate.connect(self._on_navigate)
        ctx.signals.theme_changed.connect(lambda _: self._apply_theme())

        self._apply_theme()
        self._on_navigate("dashboard", {})

    # ------------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 20, 18, 16)
        layout.setSpacing(2)

        title = QLabel("GradeForge")
        title.setObjectName("sidebarTitle")
        tagline = QLabel("Intelligent, explainable\nexam grading — offline.")
        tagline.setObjectName("sidebarTagline")
        layout.addWidget(title)
        layout.addWidget(tagline)
        layout.addSpacing(14)
        layout.addWidget(hline())
        layout.addSpacing(6)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        self.nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for key, label in _NAV_ITEMS:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setSizeHint(QSize(-1, 38))
            self.nav_list.addItem(item)
        self.nav_list.currentItemChanged.connect(self._on_nav_clicked)
        layout.addWidget(self.nav_list)
        layout.addStretch()

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
        self.stack.setCurrentWidget(page)

        if key in self._nav_keys:
            for i in range(self.nav_list.count()):
                item = self.nav_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == key:
                    self.nav_list.blockSignals(True)
                    self.nav_list.setCurrentItem(item)
                    self.nav_list.blockSignals(False)
                    break

    def _apply_theme(self) -> None:
        palette = palette_for(self.ctx.theme)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(palette))

    def closeEvent(self, event) -> None:  # noqa: N802
        self.ctx.shutdown()
        super().closeEvent(event)
