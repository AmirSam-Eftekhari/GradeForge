from __future__ import annotations

from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter

from src.ui.theme import Palette


def bar_chart(
    categories: list[str], values: list[float], palette: Palette,
    bar_color: str | None = None, y_title: str = "", max_y: float | None = None,
) -> QChartView:
    series = QBarSeries()
    bar_set = QBarSet("")
    bar_set.append(values)
    bar_set.setColor(QColor(bar_color or palette.accent))
    bar_set.setBorderColor(QColor(bar_color or palette.accent))
    series.append(bar_set)
    series.setLabelsVisible(False)

    chart = QChart()
    chart.addSeries(series)
    chart.legend().setVisible(False)
    chart.setBackgroundVisible(False)
    chart.setMargins(chart.margins().__class__(4, 4, 4, 4))
    chart.layout().setContentsMargins(0, 0, 0, 0)

    axis_x = QBarCategoryAxis()
    axis_x.append(categories)
    axis_x.setLabelsColor(QColor(palette.text_secondary))
    axis_x.setGridLineColor(QColor(palette.border))
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    series.attachAxis(axis_x)

    axis_y = QValueAxis()
    if max_y is not None:
        axis_y.setRange(0, max_y)
    axis_y.setLabelsColor(QColor(palette.text_secondary))
    axis_y.setGridLineColor(QColor(palette.border))
    if y_title:
        axis_y.setTitleText(y_title)
        axis_y.setTitleBrush(QColor(palette.text_muted))
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_y)

    for axis in (axis_x, axis_y):
        font = QFont()
        font.setPointSize(9)
        axis.setLabelsFont(font)

    view = QChartView(chart)
    view.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.setStyleSheet(f"background-color: {palette.bg_elevated}; border-radius: 10px;")
    view.setMinimumHeight(220)
    return view


def multi_color_bar_chart(
    categories: list[str], values: list[float], colors: list[str], palette: Palette, y_title: str = "",
) -> QChartView:
    """Like bar_chart, but each bar gets its own color (used for question
    difficulty, where bars are colored by pass/warn/fail band)."""
    chart = QChart()
    chart.legend().setVisible(False)
    chart.setBackgroundVisible(False)
    chart.layout().setContentsMargins(0, 0, 0, 0)

    series = QBarSeries()
    for i, (cat, val, color) in enumerate(zip(categories, values, colors)):
        bar_set = QBarSet(cat)
        bar_set.append([val])
        bar_set.setColor(QColor(color))
        series.append(bar_set)
    chart.addSeries(series)

    axis_x = QBarCategoryAxis()
    axis_x.append([""])
    axis_x.setLabelsColor(QColor(palette.text_secondary))
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    series.attachAxis(axis_x)

    axis_y = QValueAxis()
    axis_y.setRange(0, 100)
    axis_y.setLabelsColor(QColor(palette.text_secondary))
    axis_y.setGridLineColor(QColor(palette.border))
    if y_title:
        axis_y.setTitleText(y_title)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_y)

    view = QChartView(chart)
    view.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.setStyleSheet(f"background-color: {palette.bg_elevated}; border-radius: 10px;")
    view.setMinimumHeight(220)
    return view
