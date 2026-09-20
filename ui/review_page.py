"""Review: one vertical reading — month, total, three categories, a small ring, history by day.

Summary and history are one thought, not two tabs. Structure comes from
spacing, alignment and day headings; there are no cards, no per-row lines.
"""
from datetime import datetime
from PySide6.QtCore import Qt, QObject, Signal, QRectF, QEvent, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton, QScrollArea, QFrame, QApplication,
    QSizePolicy, QLineEdit, QStackedWidget,
)
from database import DatabaseError
from domain import (
    CATEGORIES, UNKNOWN_LABEL, format_cents, format_amount, describe_day, describe_month, shift_month,
    MIN_YEAR, group_by_day,
)
from ui import theme
from ui.record_row import RecordRow, DayHeading  # noqa: F401  (DayHeading re-exported for tests)

COLUMN_WIDTH = 600
DONUT_SIZE = 112
RING_WIDTH = 14


def month_is_current(year, month, now=None):
    now = now or datetime.now()
    return (year, month) == (now.year, now.month)


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


class HistoryList(QWidget):
    row_clicked = Signal(object, str)
    row_changed = Signal(object, dict, dict)
    row_delete = Signal(object)
    row_edit_ended = Signal(object)

    def __init__(self, ledger, parent=None):
        super().__init__(parent)
        self.ledger = ledger
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
                row = RecordRow(record, self.ledger)
                row.clicked.connect(self.row_clicked)
                row.changed.connect(self.row_changed)
                row.delete_requested.connect(self.row_delete)
                row.edit_ended.connect(self.row_edit_ended)
                self._layout.addWidget(row)
                self.rows.append(row)

    def row_for(self, record_id):
        return next((row for row in self.rows if row.record["id"] == record_id), None)


class SearchGlyph(QToolButton):
    """A small painted magnifier — one of the few icons the system allows."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("searchGlyph")
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("搜索记录")
        self.setToolTip("搜索记录")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(theme.TEXT_2 if self.underMouse() or self.hasFocus() else theme.TEXT_3))
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = self.width() / 2 - 1.5, self.height() / 2 - 1.5
        painter.drawEllipse(QPointF(cx, cy), 5.5, 5.5)
        painter.drawLine(QPointF(cx + 4.2, cy + 4.2), QPointF(cx + 8.5, cy + 8.5))


class ReviewPage(QWidget):
    def __init__(self, ledger, notify, parent=None):
        super().__init__(parent)
        self.setObjectName("space")
        self.ledger = ledger
        self.notify = notify
        now = datetime.now()
        self.year, self.month = now.year, now.month
        self.view = None
        self.editing_row = None
        self._rebuild_after_edit = False
        self._guard = ClickOutsideGuard(self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header: the month is the context of everything below it; Search temporarily takes its place.
        self.searching = False
        self._saved_scroll = 0
        self.header = QWidget()
        self.header.setObjectName("space")
        self.header.setFixedHeight(64)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(56, 12, 56, 4)
        header_layout.setSpacing(0)
        self.header_stack = QStackedWidget()
        self.header_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        month_row = QWidget()
        month_row.setObjectName("space")
        header = QHBoxLayout(month_row)
        header.setContentsMargins(0, 0, 0, 0)
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
        self.header_stack.addWidget(month_row)
        search_row = QWidget()
        search_row.setObjectName("space")
        search_layout = QHBoxLayout(search_row)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)
        search_layout.addStretch()
        self.search_field = QLineEdit()
        self.search_field.setObjectName("search")
        self.search_field.setPlaceholderText("搜索记录…")
        self.search_field.setClearButtonEnabled(False)
        self.search_field.setFixedWidth(320)
        self.search_field.setAccessibleName("搜索记录")
        self.search_field.textChanged.connect(lambda _: self._search_timer.start())
        search_layout.addWidget(self.search_field)
        self.search_close = QToolButton()
        self.search_close.setObjectName("monthArrow")
        self.search_close.setText("×")
        self.search_close.setAccessibleName("退出搜索")
        self.search_close.setToolTip("退出搜索")
        self.search_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_close.clicked.connect(self.exit_search)
        search_layout.addWidget(self.search_close)
        search_layout.addStretch()
        self.header_stack.addWidget(search_row)
        header_layout.addWidget(self.header_stack, 1)
        self.search_button = SearchGlyph()
        self.search_button.clicked.connect(self.enter_search)
        header_layout.addWidget(self.search_button, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addWidget(self.header)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)
        self._search_timer.timeout.connect(self._run_search)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self,
                  context=Qt.ShortcutContext.WidgetWithChildrenShortcut, activated=self.enter_search)

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
        self.column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
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
        self.no_results = QLabel()
        self.no_results.setFont(theme.font(14))
        self.no_results.setStyleSheet(f"color: {theme.TEXT_3};")
        self.no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_results.setTextFormat(Qt.TextFormat.PlainText)
        self.no_results.hide()
        column.addWidget(self.no_results)
        column.addSpacing(40)
        self.history = HistoryList(ledger)
        self.history.row_clicked.connect(self._row_clicked)
        self.history.row_changed.connect(self._row_changed)
        self.history.row_delete.connect(self._delete_row)
        self.history.row_edit_ended.connect(self._row_edit_ended)
        column.addWidget(self.history)
        column.addStretch()
        # Centre with stretches, not with an alignment flag: an aligned widget only gets its
        # size hint, which would make the whole list jump when a row builds its editors.
        centred = QHBoxLayout()
        centred.setContentsMargins(0, 0, 0, 0)
        centred.addStretch(1)
        centred.addWidget(self.column, 100)  # takes all it may (max width), margins share the rest
        centred.addStretch(1)
        body_layout.addLayout(centred)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll, 1)
        self.refresh()

    # ---- month ---------------------------------------------------------------
    def at_current_month(self):
        return month_is_current(self.year, self.month)

    def show_current_month(self):
        now = datetime.now()
        if (self.year, self.month) == (now.year, now.month) or not self.leave():
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
        if not self.leave():
            return  # an invalid edit keeps the context until fixed or cancelled
        self.year, self.month = year, month
        self.refresh()
        self.scroll.verticalScrollBar().setValue(0)

    # ---- data -------------------------------------------------------------------
    def refresh(self, *, keep_scroll=False):
        if self.searching:
            self._run_search(keep_scroll=keep_scroll)
            return
        position = self.scroll.verticalScrollBar().value() if keep_scroll else 0
        self._drop_edit_state()
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
        if keep_scroll:
            self.scroll.verticalScrollBar().setValue(position)

    def rows(self):
        return self.history.rows

    # ---- search (a temporary Review state, never a third space) -------------
    def enter_search(self):
        if self.searching:
            self.search_field.setFocus()
            self.search_field.selectAll()
            return
        if not self.leave():
            return
        self.searching = True
        self._saved_scroll = self.scroll.verticalScrollBar().value()
        self.header_stack.setCurrentIndex(1)
        self.search_button.hide()
        self.summary.hide()
        self.failure.hide()
        self.history.clear()
        self.no_results.hide()
        self.search_field.clear()
        self.search_field.setFocus()

    def exit_search(self):
        if not self.searching:
            return
        self.cancel_edit()
        self.searching = False
        self._search_timer.stop()
        self.header_stack.setCurrentIndex(0)
        self.search_button.show()
        self.no_results.hide()
        self.summary.show()
        self.search_field.clear()
        self.refresh()
        self.scroll.verticalScrollBar().setValue(self._saved_scroll)
        self.setFocus()

    def _run_search(self, *, keep_scroll=False):
        if not self.searching:
            return
        position = self.scroll.verticalScrollBar().value() if keep_scroll else 0
        self._drop_edit_state()
        query = self.search_field.text().strip()
        try:
            records = self.ledger.search(query) if query else []
        except DatabaseError as exc:
            self.history.clear()
            self.failure.setText(f"无法读取账单，当前显示可能不完整。{exc}")
            self.failure.show()
            return
        self.failure.hide()
        self.history.show_groups(group_by_day(records), headings_with_year=True)
        self.no_results.setText(f"没有找到“{query}”相关记录" if query and not records else "")
        self.no_results.setVisible(bool(query) and not records)
        if keep_scroll:
            self.scroll.verticalScrollBar().setValue(position)

    def prepare_leave(self):
        """Before the space is left: a valid edit ends, search closes; an invalid edit refuses."""
        if not self.leave():
            return False
        self.exit_search()
        return True

    # ---- edit state (Browse → Edit → Browse) --------------------------------
    def leave(self):
        """Finish the current edit if it is valid; False means the user must fix or cancel it first.
        The row reports back through edit_ended, which is what actually clears the state."""
        if self.editing_row is None:
            return True
        return self.editing_row.end_edit()

    def cancel_edit(self):
        if self.editing_row is not None:
            self.editing_row.cancel_edit()

    def _row_edit_ended(self, row):
        if row is self.editing_row:
            self._finished_edit()

    def _drop_edit_state(self):
        self.editing_row = None
        self._rebuild_after_edit = False
        self._guard.disarm()

    def _finished_edit(self):
        rebuild = self._rebuild_after_edit
        self._drop_edit_state()
        self.setFocus()
        if rebuild:
            self.refresh(keep_scroll=True)

    def _row_clicked(self, row, cell):
        if row is self.editing_row:
            return
        if not self.leave():
            return
        self.editing_row = row
        row.begin_edit(cell)
        self._guard.arm()

    def _row_changed(self, row, old, new):
        """A legal change already reached the ledger: keep the summary honest right away."""
        if not self.searching:
            try:
                totals = self.ledger.month(self.year, self.month).totals
            except DatabaseError:
                return
            self.summary.set_totals(totals)
        if old["datetime"] != new["datetime"]:
            self._rebuild_after_edit = True  # order or month membership changed; re-sort once the edit ends

    # ---- delete + undo -------------------------------------------------------
    def _delete_row(self, row):
        record = row.record
        try:
            snapshot = self.ledger.delete(record)
        except DatabaseError as exc:
            self.notify(f"删除失败，这条记录仍然保留。{exc}", danger=True)
            return
        self.refresh(keep_scroll=True)
        text = f"已删除 {format_amount(snapshot['amount_cents'])}"
        if snapshot["description"]:
            text += f" · {snapshot['description']}"
        self.notify(text, undo=lambda: self._restore(snapshot))

    def _restore(self, snapshot):
        try:
            self.ledger.restore(snapshot)
        except DatabaseError as exc:
            self.notify(f"无法恢复，这条记录仍处于已删除状态。{exc}", danger=True)
            return
        self.refresh(keep_scroll=True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.editing_row is not None:
                self.cancel_edit()
                return
            if self.searching:
                self.exit_search()
                return
        super().keyPressEvent(event)


class ClickOutsideGuard(QObject):
    """While a row is being edited, a press anywhere else ends the edit — or, if the
    edit is invalid, is swallowed so the user stays with the field that needs fixing."""

    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self._armed = False

    def arm(self):
        if not self._armed:
            QApplication.instance().installEventFilter(self)
            self._armed = True

    def disarm(self):
        if self._armed:
            QApplication.instance().removeEventFilter(self)
            self._armed = False

    def eventFilter(self, watched, event):
        if event.type() != QEvent.Type.MouseButtonPress or not isinstance(watched, QWidget):
            return False
        row = self.page.editing_row
        if row is None or watched.window() is not self.page.window():
            return False  # popups (combo lists, menus) belong to the edit
        if watched is row or row.isAncestorOf(watched):
            return False
        if self.page.leave():
            return False
        return True
