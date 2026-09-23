"""Review: one vertical reading — month, total, three categories, a small ring, history by day.

Summary and history are one thought, not two tabs. Structure comes from
spacing, alignment and day headings; there are no cards, no per-row lines.
"""
from datetime import datetime
from PySide6.QtCore import Qt, QObject, Signal, QRectF, QEvent, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QShortcut, QKeySequence, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton, QScrollArea, QFrame, QApplication,
    QSizePolicy, QLineEdit, QStackedWidget, QSpacerItem,
)
from database import DatabaseError
from domain import (
    CATEGORIES, format_cents, format_amount, describe_day, describe_month, shift_month,
    MIN_YEAR, group_by_day,
)
from ui import motion, theme
from ui.capture_page import CurrencyMark, CURRENCY_OPTICAL
from ui.record_row import (  # noqa: F401  (RecordRow, DayHeading, ROW_GAP re-exported for tests)
    RecordRow, DayHeading, ROW_GAP, EDGE_ROOM, VALUE_TAIL,
)

# One sheet of paper, read straight down: month, total, the month's shape, then the days.
# Everything under the total hangs off one grid of two edges. Text starts at the text
# edge — category names, day headings, times, descriptions — and values end at the value
# edge — the ring and every record amount. The edges are MEASURE apart and sit evenly about
# the centre line the month and the total are set on, so summary and history are one
# column, not two blocks that happen to be stacked. The measure is short on purpose: a
# record is read as one thing — what, and how much — not as a word at one side of the
# window and a number at the other.
MEASURE = 400             # text edge to value edge; the same width as Capture's column
# The column is even about the centre line. A row carries the delete edge's room after its
# values, so the list starts that much further in than the column does.
COLUMN_WIDTH = MEASURE + 2 * VALUE_TAIL
HISTORY_LEAD = EDGE_ROOM
GUTTER = 10               # always reserved for the scroll bar, so the axis never shifts
BODY_SIDE = 24            # minimum breathing room beside the axis
HEADER_SIDE = 56
HEADER_HEIGHT, HEADER_TOP, HEADER_BOTTOM = 76, 26, 4
# The one line the header's controls are centred on: the month, the search glyph — and the
# window's ⋮, which sits on it too rather than a little above, as a near miss.
HEADER_LINE = HEADER_TOP + (HEADER_HEIGHT - HEADER_TOP - HEADER_BOTTOM) // 2
SEARCH_SLOT = 32          # the search glyph's room, mirrored on the left so the month is centred
# The search field is set on the grid: what is typed starts on the text edge, directly above
# the descriptions it finds. Its text sits 1 (border) + 12 (padding) + 2 (Qt's margin) in.
SEARCH_TEXT_INSET = 15
SEARCH_WIDTH = MEASURE + 2 * SEARCH_TEXT_INSET
SEARCH_MIN_WIDTH = 280    # a narrow window gives up the alignment before the field
DONUT_SIZE = 98
RING_WIDTH = 7
STRUCTURE_GAP = 52        # the ring is a separate object; it needs its own air
DOT_LEAD = 16             # a category's dot and its gap hang in the margin, before the text edge
CATEGORY_WIDTH = MEASURE - STRUCTURE_GAP - DONUT_SIZE  # names to amounts
MONTH_ARROW_WIDTH = 26
TOTAL_CURRENCY_PX = 26
TOTAL_TO_STRUCTURE = 32
SUMMARY_TO_HISTORY = 72   # the overview closes, the records open
MONTH_SHIFT = 10          # a second-order move: the month changed, not the space
DAY_GAP = 36              # between two day groups
HEADING_GAP = 12          # a day heading to its first record


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
        """Without a classified share there is no proportion to show, so there is no ring:
        a grey circle over nothing but unjudged records would be decoration."""
        self.segments = [(theme.CATEGORY_COLORS[c], totals[c]) for c in CATEGORIES if totals[c] > 0]
        if self.segments and totals.get("unknown", 0) > 0:
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
        self.dot.setFixedSize(6, 6)  # integer radius only: Qt squares off a fractional one
        self.dot.setStyleSheet(f"background: {color}; border-radius: 3px;" if color else "background: transparent;")
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
    """Month total, then the three categories as one compact group beside the ring.

    With a ring, the group spans the page's grid: the names start at the text edge, their
    dots hanging in the margin before it, and the ring ends at the value edge — the two
    edges the records below hang off. Without one (nothing classified yet, so no proportion
    to draw) there is no reason to hold its room: an empty slot would pull the three lines
    off the centre line for an object that is not there. The group then moves onto the
    centre line itself. Two states, each balanced; nothing in between.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        total_row = QHBoxLayout()
        total_row.setSpacing(0)  # the gap belongs to the mark, not to the layout
        total_row.addStretch()
        self.total = QLabel("0.00")
        self.total.setFont(theme.font(44, theme.MEDIUM, tabular=True))
        self.total.setStyleSheet(f"color: {theme.TEXT};")
        self.total.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.total.setAccessibleName("本月总支出")
        metrics = QFontMetrics(self.total.font())
        self.currency = CurrencyMark(TOTAL_CURRENCY_PX, metrics.height(), metrics.descent())
        total_row.addWidget(self.currency, 0, Qt.AlignmentFlag.AlignBottom)
        total_row.addWidget(self.total, 0, Qt.AlignmentFlag.AlignBottom)
        total_row.addSpacing(2 * CURRENCY_OPTICAL)  # see CurrencyMark: the pair, not its box
        total_row.addStretch()
        layout.addLayout(total_row)
        layout.addSpacing(TOTAL_TO_STRUCTURE)

        self.structure = QWidget()
        structure = QHBoxLayout(self.structure)
        structure.setContentsMargins(0, 0, 0, 0)
        structure.setSpacing(0)
        structure.addStretch()
        lines = QWidget()
        lines.setFixedWidth(DOT_LEAD + CATEGORY_WIDTH)
        lines_layout = QVBoxLayout(lines)
        lines_layout.setContentsMargins(0, 0, 0, 0)
        lines_layout.setSpacing(10)
        self.lines = {c: CategoryLine(c, theme.CATEGORY_COLORS[c]) for c in CATEGORIES}
        for line in self.lines.values():
            lines_layout.addWidget(line)
        # Not a fourth category: a quiet sentence that explains the remainder, with no dot,
        # no warning colour and nothing to act on. It disappears entirely at zero.
        self.unknown_note = QLabel()
        self.unknown_note.setFont(theme.font(12))
        self.unknown_note.setStyleSheet(f"color: {theme.TEXT_3};")
        self.unknown_note.setTextFormat(Qt.TextFormat.PlainText)
        self.unknown_note.setFixedHeight(16)  # a reserved line: appearing must not move the ring
        self.unknown_note.setContentsMargins(DOT_LEAD, 0, 0, 0)  # on the text edge, like the names
        self.unknown_note.setAccessibleName("尚未分类的金额")
        lines_layout.addSpacing(6)
        lines_layout.addWidget(self.unknown_note)
        structure.addWidget(lines, 0, Qt.AlignmentFlag.AlignVCenter)
        # The ring and the air before it are one slot: a month without a ring gives both back.
        self.chart_slot = QWidget()
        self.chart_slot.setFixedSize(STRUCTURE_GAP + DONUT_SIZE, DONUT_SIZE)
        slot_layout = QHBoxLayout(self.chart_slot)
        slot_layout.setContentsMargins(STRUCTURE_GAP, 0, 0, 0)
        self.donut = DonutChart()
        slot_layout.addWidget(self.donut)
        structure.addWidget(self.chart_slot, 0, Qt.AlignmentFlag.AlignVCenter)
        # Mirrors the hanging dots, so what the two stretches centre is the text and the ring
        # (or the text alone): the dots stay in the margin in both states.
        structure.addSpacing(DOT_LEAD)
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
        unknown = totals["unknown"]
        self.unknown_note.setText(f"另有 {format_amount(unknown)} 尚未分类" if unknown else "")
        self.donut.set_totals(totals)
        ring = bool(self.donut.segments)
        self.donut.setVisible(ring)
        self.chart_slot.setVisible(ring)  # no ring, no room kept for one

    def show_failure(self):
        self.total.setText("—")
        self.structure.hide()
        self.empty.hide()


class DayGroup(QWidget):
    """One day: its heading and its records. Keeping a day together means a record
    leaving can close its own space, and the last record of a day can take the
    heading with it — without the rest of the list snapping into place afterwards."""

    def __init__(self, day, heading, parent=None):
        super().__init__(parent)
        self.day = day
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.heading = DayHeading(heading)
        layout.addWidget(self.heading)
        layout.addSpacing(HEADING_GAP)
        self._layout = layout
        self.rows = []

    def add_row(self, row):
        self._layout.addWidget(row)  # each row carries the gap to the next one
        self.rows.append(row)

    def live_rows(self):
        return [row for row in self.rows if not row.leaving]


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
        self._layout.setSpacing(DAY_GAP - ROW_GAP)  # the last row of a day carries the rest
        self.rows = []
        self._showing = None  # what the rows on screen currently say
        self._with_year = False

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
        self._showing = None

    @staticmethod
    def _state(groups, headings_with_year):
        return (headings_with_year, tuple(
            (day, tuple((r["id"], r["datetime"], r["amount_cents"], r["description"], r["category"])
                        for r in records)) for day, records in groups))

    def show_groups(self, groups, *, headings_with_year=False):
        state = self._state(groups, headings_with_year)
        if state == self._showing:
            return  # the same records, already on screen: rebuilding would only cost time
        self.clear()
        self._showing = state
        self._with_year = headings_with_year
        for day, records in groups:
            group = DayGroup(day, describe_day(day, with_year=headings_with_year))
            for record in records:
                row = RecordRow(record, self.ledger)
                row.clicked.connect(self.row_clicked)
                row.changed.connect(self.row_changed)
                row.delete_requested.connect(self.row_delete)
                row.edit_ended.connect(self.row_edit_ended)
                group.add_row(row)
                self.rows.append(row)
            self._layout.addWidget(group)

    def live_rows(self):
        """Rows the reader can still act on: a deleted record is gone from here the
        moment it is deleted, even while it is still finishing its way off screen."""
        return [row for row in self.rows if not row.leaving]

    def start_leaving(self, row):
        """Mark a deleted record as gone and hand back the widget that should leave —
        the row, or the whole day if that was its last record."""
        leaving = self.leaving_widget(row)
        row.leaving = True
        self._showing = None  # what is on screen no longer matches the ledger
        return leaving

    def forget(self, row):
        """Take a record that has finished leaving out of the list — without rebuilding
        the rest of it. What is on screen already matches the ledger."""
        group = self.group_of(row)
        target = group if group is not None and not group.live_rows() else row
        self._layout.removeWidget(target) if target is group else None
        target.setParent(None)
        target.deleteLater()
        if row in self.rows:
            self.rows.remove(row)
        self._recompute_showing()  # what is left already matches the ledger

    def _recompute_showing(self):
        groups = [(group.day, [row.record for row in group.live_rows()])
                  for group in self.findChildren(DayGroup) if group.live_rows()]
        groups.sort(key=lambda pair: pair[0], reverse=True)
        self._showing = self._state(groups, self._with_year)

    def group_of(self, row):
        parent = row.parentWidget()
        return parent if isinstance(parent, DayGroup) else None

    def leaving_widget(self, row):
        """The row, or the whole day when this was its last record."""
        group = self.group_of(row)
        if group is not None and group.live_rows() == [row]:
            return group
        return row

    def row_for(self, record_id):
        return next((row for row in self.live_rows() if row.record["id"] == record_id), None)


class MonthArrow(QToolButton):
    """One half of the month's navigation, painted rather than set in type.

    A ‹ from the text font is four pixels of ink at this size and reads as a speck, so
    the arrow is drawn: a chevron with the weight of a hairline, on the month's own
    optical centre, close enough to the words to belong to them. It stays quiet — this
    is how the month moves, not something to look at.
    """
    ARM = 3.4
    REACH = 5.2

    def __init__(self, direction, parent=None):
        super().__init__(parent)
        self.setObjectName("monthArrow")
        self.direction = direction
        self.setFixedSize(MONTH_ARROW_WIDTH, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def ink_inset(self):
        """How far the chevron's ink stays from the edge that faces the month."""
        return (self.width() - 2 * self.ARM) / 2.0

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            color = QColor(theme.DISABLED_ARROW)
        elif self.underMouse() or self.hasFocus():
            color = QColor(theme.TEXT)
        else:
            color = QColor(theme.TEXT_2)
        pen = QPen(color)
        pen.setWidthF(1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        tip = cx + self.ARM * self.direction      # the point leads the way the month moves
        back = cx - self.ARM * self.direction
        painter.drawLine(QPointF(back, cy - self.REACH), QPointF(tip, cy))
        painter.drawLine(QPointF(tip, cy), QPointF(back, cy + self.REACH))


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
        self.header.setFixedHeight(HEADER_HEIGHT)
        header_layout = QHBoxLayout(self.header)
        # + GUTTER on the right so the month sits on the same centre line as the body below it.
        header_layout.setContentsMargins(HEADER_SIDE, HEADER_TOP, HEADER_SIDE + GUTTER, HEADER_BOTTOM)
        header_layout.setSpacing(0)
        header_layout.addSpacing(SEARCH_SLOT)  # balances the search glyph on the right
        self.header_stack = QStackedWidget()
        self.header_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        month_row = QWidget()
        month_row.setObjectName("space")
        header = QHBoxLayout(month_row)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(0)  # the distance to the month is the chevron's, not the layout's
        header.addStretch()
        self.previous = MonthArrow(-1)
        self.previous.setAccessibleName("上一个月")
        self.previous.setToolTip("上一个月")
        self.previous.clicked.connect(lambda: self.change_month(-1))
        header.addWidget(self.previous)
        self.month_label = QPushButton()
        self.month_label.setObjectName("monthLabel")
        self.month_label.setFont(theme.font(22, theme.MEDIUM))
        self.month_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.month_label.setToolTip("回到本月")
        self.month_label.setAccessibleName("当前月份")
        self.month_label.clicked.connect(self.show_current_month)
        header.addWidget(self.month_label)
        self.next = MonthArrow(1)
        self.next.setAccessibleName("下一个月")
        self.next.setToolTip("下一个月")
        self.next.clicked.connect(lambda: self.change_month(1))
        header.addWidget(self.next)
        header.addStretch()
        self.header_stack.addWidget(month_row)
        search_row = QWidget()
        search_row.setObjectName("space")
        search_layout = QHBoxLayout(search_row)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(0)
        search_layout.addStretch(1)
        # Mirrors × and its gap, measured rather than assumed, so the search field keeps
        # exactly the centre line the month label had.
        self._search_mirror = QSpacerItem(SEARCH_SLOT + 4, 0, QSizePolicy.Policy.Fixed,
                                          QSizePolicy.Policy.Minimum)
        search_layout.addSpacerItem(self._search_mirror)
        self.search_field = QLineEdit()
        self.search_field.setObjectName("search")
        self.search_field.setPlaceholderText("搜索记录…")
        self.search_field.setClearButtonEnabled(False)
        self.search_field.setMinimumWidth(SEARCH_MIN_WIDTH)
        self.search_field.setMaximumWidth(SEARCH_WIDTH)
        self.search_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.search_field.setAccessibleName("搜索记录")
        self.search_field.textChanged.connect(lambda _: self._search_timer.start())
        search_layout.addWidget(self.search_field, 100)  # takes all it may; the stretches share the rest
        search_layout.addSpacing(4)
        self.search_close = QToolButton()
        self.search_close.setObjectName("searchClose")
        self.search_close.setText("×")
        self.search_close.setAccessibleName("退出搜索")
        self.search_close.setToolTip("退出搜索")
        self.search_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_close.setFixedSize(32, 30)  # mirrored by _search_mirror, so Search keeps the centre line
        self.search_close.clicked.connect(self.exit_search)
        search_layout.addWidget(self.search_close)
        search_layout.addStretch(1)
        self._search_layout = search_layout
        self.header_stack.addWidget(search_row)
        header_layout.addWidget(self.header_stack, 1)
        self.search_button = SearchGlyph()
        self.search_button.clicked.connect(self.enter_search)
        # Its room is kept while it is hidden, so entering Search moves nothing.
        policy = self.search_button.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self.search_button.setSizePolicy(policy)
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
        self.body_layout = body_layout = QVBoxLayout(body)
        # The month and the total are one statement, so the gap between them is the
        # smallest of the three the page reads down through.
        body_layout.setContentsMargins(BODY_SIDE, 8, BODY_SIDE + GUTTER, 76)
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
        column.addSpacing(SUMMARY_TO_HISTORY)
        self.history = HistoryList(ledger)
        # Rows keep the delete edge's room after their values; starting the list that much
        # further in puts their text and value edges exactly on the summary's.
        self.history.layout().setContentsMargins(HISTORY_LEAD, 0, 0, 0)
        self.history.row_clicked.connect(self._row_clicked)
        self.history.row_changed.connect(self._row_changed)
        self.history.row_delete.connect(self._delete_row)
        self.history.row_edit_ended.connect(self._row_edit_ended)
        column.addWidget(self.history)  # one grid for the whole column: no second measure here
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
        # The scroll bar's room is reserved on both sides of its appearance, so the
        # reading axis sits at the same x whether a month scrolls or not.
        self.scroll.verticalScrollBar().rangeChanged.connect(lambda *_: self._sync_axis())
        self.refresh()

    # ---- the axis ------------------------------------------------------------
    def _sync_axis(self):
        """Give back the gutter exactly when the scroll bar takes it."""
        bar = self.scroll.verticalScrollBar()
        reserved = 0 if bar.maximum() > bar.minimum() else GUTTER
        margins = self.body_layout.contentsMargins()
        if margins.right() != BODY_SIDE + reserved:
            self.body_layout.setContentsMargins(BODY_SIDE, margins.top(),
                                                BODY_SIDE + reserved, margins.bottom())

    # ---- month ---------------------------------------------------------------
    def at_current_month(self):
        return month_is_current(self.year, self.month)

    def show_current_month(self):
        now = datetime.now()
        if (self.year, self.month) == (now.year, now.month) or not self.leave():
            return
        direction = 1 if (now.year, now.month) > (self.year, self.month) else -1
        self.year, self.month = now.year, now.month
        self._show_month(direction)

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
        self._show_month(1 if delta > 0 else -1)

    def _show_month(self, direction):
        """A second-order change: the content of the same page moves a little, in the
        direction the month moved. It must never read like a change of space."""
        self.refresh()
        self.scroll.verticalScrollBar().setValue(0)
        self.animate_month(direction)

    def animate_month(self, direction):
        if not self.isVisible() or not motion.ENABLED:
            return
        self.body_layout.activate()  # settle the new month before taking its origin
        motion.slide_home(self.column, MONTH_SHIFT * direction, motion.MONTH)
        motion.fade_in(self.scroll.viewport(), 0.55, motion.MONTH)

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
        return self.history.live_rows()

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
        self._turn_header(1)
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
        self._turn_header(0)
        self.search_button.show()
        self.no_results.hide()
        self.summary.show()
        self.search_field.clear()
        self.refresh()
        self.scroll.verticalScrollBar().setValue(self._saved_scroll)
        self.setFocus()

    def _turn_header(self, index):
        """The month area turns into the search area in place: same header, same height,
        same centre line. Review changes state; it does not open a page."""
        self.header_stack.setCurrentIndex(index)
        self._balance_search_row()
        motion.fade_in(self.header_stack, 0.0, motion.SEARCH)
        motion.fade_in(self.scroll.viewport(), 0.55, motion.SEARCH)

    def _balance_search_row(self):
        # The width × actually gets (it is fixed), not its size hint: the hint depends on the
        # font and can exceed the fixed box, which would push the field off the centre line.
        width = self.search_close.width() + 4
        if self._search_mirror.sizeHint().width() != width:
            self._search_mirror.changeSize(width, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
            self._search_layout.invalidate()

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
        # The ledger is already correct. The record leaves its own space, the totals
        # follow at once, and nothing else in the list is rebuilt or moved.
        self._drop_edit_state()
        self._refresh_totals()
        text = f"已删除 {format_amount(snapshot['amount_cents'])}"
        if snapshot["description"]:
            text += f" · {snapshot['description']}"
        self.notify(text, undo=lambda: self._restore(snapshot))
        motion.collapse(self.history.start_leaving(row), motion.RECORD,
                        lambda: self.history.forget(row))

    def _refresh_totals(self):
        if self.searching:
            return
        try:
            self.summary.set_totals(self.ledger.month(self.year, self.month).totals)
        except DatabaseError:
            pass  # the next full refresh reports it

    def _restore(self, snapshot):
        try:
            self.ledger.restore(snapshot)
        except DatabaseError as exc:
            self.notify(f"无法恢复，这条记录仍处于已删除状态。{exc}", danger=True)
            return
        self.refresh(keep_scroll=True)
        row = self.history.row_for(snapshot["id"])
        if row is not None:
            motion.fade_in(row, 0.0, motion.RECORD)

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
