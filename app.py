#!/usr/bin/env python3
"""
GradeForge — desktop entry point.

    python app.py

Starts the PySide6 dashboard. This calls into exactly the same src/
modules main.py's CLI does (src.grading.engine.GradingEngine,
src.database.repository.ExamRepository, src.reports.*, ...) via the
src/services/ layer — no grading logic lives in the UI. See
src/ui/README.md for the original call-mapping this build followed.

    python main.py --answer-key ... --students-dir ...

remains the scriptable/CI-friendly CLI, unchanged.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.ui.app_context import AppContext
from src.ui.main_window import MainWindow
from src.utils.logging_config import configure_logging


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GradeForge desktop app")
    parser.add_argument("--db", default=Path("exam_grader.db"), type=Path, help="SQLite database path")
    parser.add_argument("--output-dir", default=Path("Results"), type=Path, help="Default report output directory")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    configure_logging(args.verbose)

    app = QApplication(sys.argv)
    app.setApplicationName("GradeForge")
    app.setOrganizationName("GradeForge")

    ctx = AppContext(db_path=args.db, output_dir=args.output_dir)
    window = MainWindow(ctx)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
