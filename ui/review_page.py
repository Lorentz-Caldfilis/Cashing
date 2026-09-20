"""Review: one vertical reading — month, total, three categories, a small ring, history by day.

Summary and history are one thought, not two tabs. Structure comes from
spacing, alignment and day headings; there are no cards, no per-row lines.
"""
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QRectF, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QToolButton,
    QScrollArea, QFrame, QSizePolicy,
)
from database import DatabaseError
from domain import (
    CATEGORIES, UNKNOWN_LABEL, format_cents, format_amount, describe_day, describe_month, shift_month,
    MIN_YEAR,
)
from ui import theme

COLUMN_WIDTH = 600
EDGE_ROOM = 44          # right-hand room reserved for the delete edge (M5)
ROW_RADIUS = 6
DONUT_SIZE = 112
RING_WIDTH = 14


def month_is_current(year, month, now=None):
    now = now or datetime.now()
    return (year, month) == (now.year, now.month)


class ElidedLabel(QLabel):
    """Single line; long text is cut with an ellipsis instead of growing the row."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full = text
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def setText(self, text):
        self._full = text
        super().setText(text)
        self.setToolTip(text if len(text) > 40 else "")

    def full_text(self):
        return self._full

    def minimumSizeHint(self):
        return QSize(40, super().minimumSizeHint().height())

    def paintEvent(self, event):
        metrics = QFontMetrics(self.font())
        painter = QPainter(self)
        painter.setPen(QColor(self.palette().color(self.foregroundRole())))
        painter.setFont(self.font())
        text = metrics.elidedText(self._full, Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), int(self.alignment()) | Qt.AlignmentFlag.AlignVCenter, text)


class DonutChart(QWidget):
    """Proportion by intuition only: three low-saturation arcs, nothing in the centre."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(DONUT_SIZE, DONUT_SIZE)
        self.segments = []  # [(color, cents)]
        self.setAccessibleName("消费结构环形图")

    def set_totals(self, totals):
        self.segments = [(theme.CATEGORY_COLORS[c], totals[c]) for c in CATEGORIES if totals[c] > 0]
        if totals.get("unknown", 0) > 0:
            self.segments.append((theme.UNKNOWN_COLOR, totals["unknown"]))
        self.update()

    def paintEvent(self, event):
        total = sum(cents for _, cents in self.segments)
        if total <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(RING_WIDTH / 2, RING_WIDTH / 2, self.width() - RING_WIDTH, self.height() - RING_WIDTH)
        gap = 2.5 if len(self.segments) > 1 else 0.0  # degrees of breathing room between arcs
        start = 90.0
        for color, cents in self.segments:
            span = 360.0 * cents / total
            pen = QPen(QColor(color))
            pen.setWidthF(RING_WIDTH)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)
            visible = max(span - gap, 0.6)
            painter.drawArc(rect, int((start - gap / 2) * 16), int(-visible * 16))
            start -= span


class CategoryLine(QWidget):
    def __init__(self, name, color, *, weak=False, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.dot = QLabel()
        self.dot.setFixedSize(8, 8)
        self.dot.setStyleSheet(f"background: {color}; border-radius: 4px;" if color else "background: transparent;")
        layout.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.name = QLabel(name)
        self.name.setFont(theme.font(13 if weak else 14))
        self.name.setStyleSheet(f"color: {theme.TEXT_3 if weak else theme.TEXT_2};")
        layout.addWidget(self.name)
        layout.addStretch()
        self.amount = QLabel("¥0.00")
        self.amount.setFont(theme.font(13 if weak else 15, tabular=True))
        self.amount.setStyleSheet(f"color: {theme.TEXT_3 if weak else theme.TEXT};")
        self.amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.amount)

    def set_cents(self, cents):
        self.amount.setText(format_amount(cents))


class SummaryBlock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        total_row = QHBoxLayout()
        total_row.setSpacing(8)
        total_row.addStretch()
        self.currency = QLabel("¥")
        self.currency.setFont(theme.font(22))
        self.currency.setStyleSheet(f"color: {theme.TEXT_2}; padding-bottom: 6px;")
        total_row.addWidget(self.currency, 0, Qt.AlignmentFlag.AlignBottom)
        self.total = QLabel("0.00")
        self.total.setFont(theme.font(40, theme.MEDIUM, tabular=True))
        self.total.setStyleSheet(f"color: {theme.TEXT};")
        self.total.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.total.setAccessibleName("本月总支出")
        total_row.addWidget(self.total, 0, Qt.AlignmentFlag.AlignBottom)
        total_row.addStretch()
        layout.addLayout(total_row)
        layout.addSpacing(24)

        self.structure = QWidget()
        structure = QHBoxLayout(self.structure)
        structure.setContentsMargins(0, 0, 0, 0)
        structure.setSpacing(40)
        structure.addStretch()
        lines = QWidget()
        lines.setFixedWidth(220)
        lines_layout = QVBoxLayout(lines)
        lines_layout.setContentsMargins(0, 0, 0, 0)
        lines_layout.setSpacing(10)
        self.lines = {c: CategoryLine(c, theme.CATEGORY_COLORS[c]) for c in CATEGORIES}
        for line in self.lines.values():
            lines_layout.addWidget(line)
        self.unknown_line = CategoryLine(UNKNOWN_LABEL, None, weak=True)
        lines_layout.addWidget(self.unknown_line)
        structure.addWidget(lines, 0, Qt.AlignmentFlag.AlignVCenter)
        self.donut = DonutChart()
        structure.addWidget(self.donut, 0, Qt.AlignmentFlag.AlignVCenter)
        structure.addStretch()
        layout.addWidget(self.structure)

        self.empty = QLabel("本月暂无记录")
        self.empty.setFont(theme.font(14))
        self.empty.setStyleSheet(f"color: {theme.TEXT_3};")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty)

    def set_totals(self, totals):
        self.total.setText(format_cents(totals["total"]))
        empty = totals["total"] == 0
        self.structure.setVisible(not empty)
        self.empty.setVisible(empty)
        for name, line in self.lines.items():
            line.set_cents(totals[name])
        self.unknown_line.set_cents(totals["unknown"])
        self.unknown_line.setVisible(totals["unknown"] > 0)
        self.donut.set_totals(totals)

    def show_failure(self):
        self.total.setText("—")
        self.structure.hide()
        self.empty.hide()


class RecordRow(QWidget):
    """Two lines: time / amount, then description / category. Facts before interpretation."""
    clicked = Signal(object)

    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self._hover = False
        self.editing = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        grid = QGridLayout(self)
        grid.setContentsMargins(12, 9, 12 + EDGE_ROOM, 9)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(2)
        self.time = QLabel()
        self.time.setFont(theme.font(13, tabular=True))
        self.time.setStyleSheet(f"color: {theme.TEXT_3};")
        grid.addWidget(self.time, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.amount = QLabel()
        self.amount.setFont(theme.font(17, theme.MEDIUM, tabular=True))
        self.amount.setStyleSheet(f"color: {theme.TEXT};")
        self.amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(self.amount, 0, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.description = ElidedLabel()
        self.description.setFont(theme.font(16))
        self.description.setStyleSheet(f"color: {theme.TEXT};")
        grid.addWidget(self.description, 1, 0)
        self.category = QWidget()
        category_layout = QHBoxLayout(self.category)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(6)
        category_layout.addStretch()
        self.category_dot = QLabel()
        self.category_dot.setFixedSize(6, 6)
        category_layout.addWidget(self.category_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.category_name = QLabel()
        self.category_name.setFont(theme.font(13))
        self.category_name.setStyleSheet(f"color: {theme.TEXT_3};")
        category_layout.addWidget(self.category_name)
        grid.addWidget(self.category, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.setColumnStretch(0, 1)
        self.show_record(record)

    def show_record(self, record):
        self.record = record
        self.time.setText(record["datetime"][11:16])
        self.amount.setText(format_amount(record["amount_cents"]))
        self.description.setText(record["description"])
        category = record["category"]
        known = category in CATEGORIES
        self.category_name.setText(category if known else "")
        self.category_dot.setStyleSheet(
            f"background: {theme.CATEGORY_COLORS[category]}; border-radius: 3px;" if known else "background: transparent;")
        self.category_dot.setVisible(known)
        self.setAccessibleName(f"{record['datetime']} {format_amount(record['amount_cents'])} {record['description']}")

    # ---- states ----------------------------------------------------------
    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def paintEvent(self, event):
        if not (self._hover or self.editing):
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.ACCENT_TINT if self.editing else theme.HOVER))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), ROW_RADIUS, ROW_RADIUS)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self)
        event.accept()


class DayHeading(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFont(theme.font(14, theme.MEDIUM))
        self.setStyleSheet(f"color: {theme.TEXT_2}; padding-left: 12px;")


class HistoryList(QWidget):
    row_clicked = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.rows = []

    def clear(self):
        """Old rows must vanish now, not when the event loop gets to deleteLater:
        a month must never show a mix of old and new data."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.rows = []

    def show_groups(self, groups, *, headings_with_year=False):
        self.clear()
        for index, (day, records) in enumerate(groups):
            if index:
                self._layout.addSpacing(24)
            self._layout.addWidget(DayHeading(describe_day(day, with_year=headings_with_year)))
            self._layout.addSpacing(6)
            for record in records:
                row = RecordRow(record)
                row.clicked.connect(self.row_clicked)
                self._layout.addWidget(row)
                self.rows.append(row)

    def row_for(self, record_id):
        return next((row for row in self.rows if row.record["id"] == record_id), None)


class ReviewPage(QWidget):
    def __init__(self, ledger, notify, parent=None):
        super().__init__(parent)
        self.setObjectName("space")
        self.ledger = ledger
        self.notify = notify
        now = datetime.now()
        self.year, self.month = now.year, now.month
        self.view = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header: the month is the context of everything below it.
        self.header = QWidget()
        self.header.setObjectName("space")
        self.header.setFixedHeight(64)
        header = QHBoxLayout(self.header)
        header.setContentsMargins(56, 12, 56, 4)
        header.setSpacing(4)
        header.addStretch()
        self.previous = QToolButton()
        self.previous.setObjectName("monthArrow")
        self.previous.setText("‹")
        self.previous.setAccessibleName("上一个月")
        self.previous.setToolTip("上一个月")
        self.previous.setCursor(Qt.CursorShape.PointingHandCursor)
        self.previous.clicked.connect(lambda: self.change_month(-1))
        header.addWidget(self.previous)
        self.month_label = QPushButton()
        self.month_label.setObjectName("monthLabel")
        self.month_label.setFont(theme.font(20, theme.MEDIUM))
        self.month_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.month_label.setToolTip("回到本月")
        self.month_label.setAccessibleName("当前月份")
        self.month_label.clicked.connect(self.show_current_month)
        header.addWidget(self.month_label)
        self.next = QToolButton()
        self.next.setObjectName("monthArrow")
        self.next.setText("›")
        self.next.setAccessibleName("下一个月")
        self.next.setToolTip("下一个月")
        self.next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next.clicked.connect(lambda: self.change_month(1))
        header.addWidget(self.next)
        header.addStretch()
        outer.addWidget(self.header)

        # Body: summary then history, one scroll.
        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        body = QWidget()
        body.setObjectName("scrollBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 8, 24, 72)
        body_layout.setSpacing(0)
        self.column = QWidget()
        self.column.setObjectName("scrollBody")
        self.column.setMaximumWidth(COLUMN_WIDTH)
        column = QVBoxLayout(self.column)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        self.summary = SummaryBlock()
        column.addWidget(self.summary)
        self.failure = QLabel()
        self.failure.setObjectName("error")
        self.failure.setWordWrap(True)
        self.failure.setTextFormat(Qt.TextFormat.PlainText)
        self.failure.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.failure.hide()
        column.addWidget(self.failure)
        column.addSpacing(40)
        self.history = HistoryList()
        column.addWidget(self.history)
        column.addStretch()
        body_layout.addWidget(self.column, 0, Qt.AlignmentFlag.AlignHCenter)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll, 1)
        self.refresh()

    # ---- month ---------------------------------------------------------------
    def at_current_month(self):
        return month_is_current(self.year, self.month)

    def show_current_month(self):
        now = datetime.now()
        if (self.year, self.month) == (now.year, now.month):
            return
        self.year, self.month = now.year, now.month
        self.refresh()
        self.scroll.verticalScrollBar().setValue(0)

    def change_month(self, delta):
        try:
            year, month = shift_month(self.year, self.month, delta)
        except ValueError:
            return
        now = datetime.now()
        if (year, month) > (now.year, now.month):
            return  # the future has no records
        self.year, self.month = year, month
        self.refresh()
        self.scroll.verticalScrollBar().setValue(0)

    # ---- data -------------------------------------------------------------------
    def refresh(self):
        self.month_label.setText(describe_month(self.year, self.month))
        self.previous.setEnabled((self.year, self.month) != (MIN_YEAR, 1))
        self.next.setEnabled(not self.at_current_month())
        try:
            view = self.ledger.month(self.year, self.month)
        except DatabaseError as exc:
            self.view = None
            self.summary.show_failure()
            self.history.clear()
            self.failure.setText(f"无法读取账单，当前显示可能不完整。{exc}")
            self.failure.show()
            return
        self.failure.hide()
        self.view = view
        self.summary.set_totals(view.totals)
        self.history.show_groups(view.groups)

    def rows(self):
        return self.history.rows
