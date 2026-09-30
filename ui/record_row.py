"""One history record: two quiet lines that turn into editors in place.

Rest → Hover (the faintest tint) → Edit (a thin accent bar beside the two
lines, fields editable, the delete edge appears on the right) → Delete Armed
(the edge expands). Edit says "this record is open", not "this record has been
replaced by a form" — and not "this record is now a card": the bar is what
separates Edit from Hover, and the surface under the record stays only a shade
above Hover's. No field carries a line until it is the focused one, and the one
that does carries a line as wide as its own text. The danger edge on the right
is left to mean the one thing it means.

Edits take effect as soon as a field is left; an invalid field is explained
under the row and blocks leaving. Nothing here floats or casts a shadow.
"""
from PySide6.QtCore import Qt, Signal, QRectF, QSize, QEvent, QVariantAnimation, QDateTime, QDate, QRegularExpression, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFontMetrics, QFontMetricsF, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDateTimeEdit, QComboBox, QSizePolicy,
)
from database import DatabaseError
from domain import CATEGORIES, UNKNOWN_LABEL, format_amount, cents_to_input, parse_amount, MAX_DESCRIPTION
from ledger import UNSET, AUTO
from ui import motion, theme
from ui.capture_page import QuietLineEdit, normalize_amount_text
from ui.controls import QuietDateTimeEdit, DATE_TEXT_NUDGE

EDGE_ROOM = 44          # right-hand room reserved for the delete edge (hit zone)
EDGE_COLLAPSED = 2      # the visible strip at rest: a hint of danger, not an offer
EDGE_EXPANDED = 36
# Where the ink sits inside the row: the text edge ROW_INSET from its left, the value edge
# VALUE_TAIL from its right. The tail is longer because the delete edge lives after the values.
ROW_INSET = 12
VALUE_TAIL = 12 + EDGE_ROOM
ROW_RADIUS = 6
EDIT_BAR = 2            # the accent bar of an open record: a line, not a surface
EDIT_BAR_INSET = 1.5    # from the row's left edge; well clear of the text edge
LINE1_HEIGHT = 21       # includes the 1 px gap to line 2: QGridLayout drops its row spacing once
LINE2_HEIGHT = 24       # hidden editors share the cells, so spacing must not be relied on
ROW_PADDING = 7         # same in Rest and Edit: the list never jumps
ROW_GAP = 12            # carried by the row itself, so a deleted row takes its gap with it
# Edit must not move the record's text. These pull each editor's pen back onto the exact
# x where the resting label drew it: a QLineEdit starts its text 2 px inside its box, and
# the date edit's own line edit sits a further 4 px in. Pull back by exactly that and no
# further — past the box edge the first stroke of a glyph is clipped (晚 lost its left side).
TIME_TEXT_NUDGE = DATE_TEXT_NUDGE
DESCRIPTION_TEXT_NUDGE = -2
# The amount editor ends its digits CARET_ROOM inside its box, where the resting amount ends
# them too, so the caret after the last digit is drawn instead of falling off the edge.
# Qt only right-aligns text that fits its line rect, which is 4 px narrower than the box:
# the equal margin on the left makes the room for that, and moves nothing.
AMOUNT_TEXT_MARGIN = -2
# The time and the amount are one line and must sit on one baseline. Qt centres each of
# them in its own cell, and the smaller font then rides about 1.5 px high; top padding on
# the time gives half of itself back as a drop, which puts the two on the same line again.
TIME_BASELINE_PAD = 3
# A focused field's line sits just under its own text. The two reading lines are tight
# enough that "just under" is the bottom edge of the cell; the category cell is taller
# than its 13 px word, so its line comes up to meet it.
ROW_LINE_LIFT = 0
CATEGORY_LINE_LIFT = 3
# Room after the last digit for the caret. The whole value column keeps it — amount and
# category, at Rest and in Edit — so the value edge is the same line in every state.
CARET_ROOM = 2
TIME_SHORT, TIME_FULL = "HH:mm", "yyyy-MM-dd HH:mm"
AMOUNT_PATTERN = QRegularExpression(r"[0-9]{0,9}(\.[0-9]{0,2})?")


def field_baseline(font, height, top=0):
    """The baseline a QLineEdit puts its text on, ``top`` being its top text margin.

    Qt sets the line's top on a whole pixel (truncating toward zero) and then stands the
    text on the font's exact, fractional ascent. A label centred the ordinary way agrees
    with that at some scales and lands a device pixel away at others (at 200 % the digits
    dropped as the record opened). Labels that an editor replaces in place draw here.
    """
    line_top = top + int((height - top - QFontMetrics(font).height() + 1) / 2)
    return line_top + QFontMetricsF(font).ascent()


class FieldLabel(QLabel):
    """Resting text that an editor replaces in place: left-set on that editor's baseline,
    the label's top contents margin standing in for the editor's top text margin."""

    def shown_text(self):
        return self.text()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QColor(self.palette().color(self.foregroundRole())))
        painter.setFont(self.font())
        margins = self.contentsMargins()
        painter.drawText(QPointF(margins.left(), field_baseline(self.font(), self.height(), margins.top())),
                         self.shown_text())


class ElidedLabel(FieldLabel):
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

    def shown_text(self):
        return QFontMetrics(self.font()).elidedText(self._full, Qt.TextElideMode.ElideRight, self.width())


class DayHeading(QLabel):
    """The day a group of records belongs to. Its inset is two pixels short of the rows'
    so that the ink, not the box, lines up with the times underneath it."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFont(theme.font(14, theme.MEDIUM))
        self.setStyleSheet(f"color: {theme.TEXT_2}; padding-left: 10px;")


class DeleteEdge(QWidget):
    """A thin danger strip on the right of the edited row; near the mouse it opens into 删除."""
    activated = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self._span = EDGE_COLLAPSED
        self._armed = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAccessibleName("删除这条记录")
        self.setToolTip("删除")
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(motion.EDIT)
        self._animation.setEasingCurve(motion.curve())
        self._animation.valueChanged.connect(self._set_span)
        self.hide()

    def armed(self):
        return self._armed

    def span(self):
        return self._span

    def _set_span(self, value):
        self._span = int(value)
        self.update()

    def _animate_to(self, target):
        self._animation.stop()
        if not motion.ENABLED:
            self._set_span(target)
            return
        self._animation.setStartValue(self._span)
        self._animation.setEndValue(target)
        self._animation.start()

    def enterEvent(self, event):
        self._armed = True
        self._animate_to(EDGE_EXPANDED)

    def leaveEvent(self, event):
        self._armed = False
        self._animate_to(EDGE_COLLAPSED)

    def reset(self):
        self._animation.stop()
        self._armed = False
        self._span = EDGE_COLLAPSED
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        # The strip grows leftwards from the right end of the reserved room.
        span = min(self._span, self.width())
        rect = QRectF(self.width() - span, 0, span, self.height())
        strong = span > EDGE_COLLAPSED + 6
        rest = QColor(theme.DANGER)
        rest.setAlphaF(0.55)  # a hint of danger, not a button
        painter.setBrush(QColor(theme.DANGER_TINT) if strong else rest)
        painter.drawRoundedRect(rect, 2, 2)
        if strong:
            painter.setPen(QColor(theme.DANGER))
            painter.setFont(theme.font(12))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "删除")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit()
        event.accept()


class CategoryBox(QComboBox):
    """The category cell, still readable as itself while it is editable.

    It paints the same dot and the same word in the same place as the resting row,
    right-anchored, and adds only a small chevron to its left to say that this is a
    choice. Entering Edit therefore does not move the category sideways.
    """
    DOT = 6
    DOT_GAP = 6
    CHEVRON = 6
    CHEVRON_GAP = 8
    RIGHT_INSET = CARET_ROOM  # the value column's shared room: the word ends on the value edge

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.currentTextChanged.connect(lambda _: self.updateGeometry())
        self._focus = motion.Blend(self, motion.FOCUS, self.update)

    def sizeHint(self):
        metrics = QFontMetrics(self.font())
        width = (self.CHEVRON + self.CHEVRON_GAP + self.DOT + self.DOT_GAP
                 + metrics.horizontalAdvance(self.currentText()) + self.RIGHT_INSET)
        return QSize(width, self.height() or LINE2_HEIGHT)

    def minimumSizeHint(self):
        return self.sizeHint()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._focus.set(True)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._focus.set(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        name = self.currentText()
        metrics = QFontMetrics(self.font())
        right = self.width() - self.RIGHT_INSET
        text_left = right - metrics.horizontalAdvance(name)
        middle = self.height() / 2.0
        known = name in CATEGORIES
        dot_right = text_left - self.DOT_GAP
        if known:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.CATEGORY_COLORS[name]))
            painter.drawEllipse(QRectF(dot_right - self.DOT, middle - self.DOT / 2.0, self.DOT, self.DOT))
        active = self.hasFocus() or self.underMouse()
        painter.setPen(QColor(theme.TEXT_2 if active else theme.TEXT_3))
        painter.setFont(self.font())
        painter.drawText(QRectF(text_left, 0, right - text_left, self.height()),
                         int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), name)
        pen = QPen(QColor(theme.TEXT_3))
        pen.setWidthF(1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        x = dot_right - self.DOT - self.CHEVRON_GAP - self.CHEVRON / 2.0
        painter.drawLine(QPointF(x - 2.8, middle - 1.4), QPointF(x, middle + 1.4))
        painter.drawLine(QPointF(x, middle + 1.4), QPointF(x + 2.8, middle - 1.4))
        weight = self._focus.value()
        if weight > 0.001:
            line = QColor(theme.ACCENT_SOFT)
            line.setAlphaF(weight)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(line)
            # Under the dot and the word only: the chevron is an offer, not part of the value.
            left = dot_right - self.DOT
            painter.drawRect(QRectF(left, self.height() - CATEGORY_LINE_LIFT - 1.0,
                                    right - left, 1.0))


class FittedLineEdit(QuietLineEdit):
    """A line edit as wide as its text, so ¥ and the number stay one right-anchored unit."""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.textChanged.connect(self.updateGeometry)

    def sizeHint(self):
        metrics = QFontMetrics(self.font())
        # Exactly the advance of the digits plus room for the caret: together with the ¥
        # label this unit is as wide as the resting "¥28.50" (which keeps the same room).
        width = max(metrics.horizontalAdvance(self.text()), metrics.horizontalAdvance("0.00")) + CARET_ROOM
        return QSize(width, self.height())

    def minimumSizeHint(self):
        return self.sizeHint()


class RowAmount(QLabel):
    """``¥42.50`` as one right-anchored object.

    The mark is drawn a shade quieter than the digits — it is the unit, not the value —
    and at exactly the strength it has while the row is being edited, so opening the
    record changes nothing about how its amount is set. The box keeps the caret's room
    after the digits, exactly as the editor that replaces it does.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, CARET_ROOM, 0)

    def paintEvent(self, event):
        text = self.text()
        metrics = QFontMetrics(self.font())
        mark, digits = (text[:1], text[1:]) if text[:1] == "¥" else ("", text)
        x = self.width() - CARET_ROOM - metrics.horizontalAdvance(text)
        baseline = field_baseline(self.font(), self.height())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setFont(self.font())
        painter.setPen(QColor(theme.TEXT_2))
        painter.drawText(QPointF(x, baseline), mark)
        painter.setPen(QColor(theme.TEXT))
        painter.drawText(QPointF(x + metrics.horizontalAdvance(mark), baseline), digits)


class RowCurrency(QLabel):
    """The editor's fixed ``¥``, on the same baseline as the digits in the field beside it."""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setFont(self.font())
        painter.setPen(QColor(theme.TEXT_2))
        painter.drawText(QPointF(0, field_baseline(self.font(), self.height())), self.text())


class RecordRow(QWidget):
    """Two lines: time / amount, then description / category. Facts before interpretation."""
    clicked = Signal(object, str)        # row, cell name under the cursor ("" = none)
    changed = Signal(object, dict, dict)  # row, old record, new record
    delete_requested = Signal(object)
    edit_ended = Signal(object)           # the row left Edit (committed or cancelled)

    def __init__(self, record, ledger, parent=None):
        super().__init__(parent)
        self.record = record
        self.ledger = ledger
        self.editing = False
        self.leaving = False  # deleted already; on screen only until it finishes leaving
        self._hover = motion.Blend(self, motion.HOVER, self.update)
        self._edit_weight = motion.Blend(self, motion.EDIT, self.update)
        self._committing = False
        self.last_change = None
        self._editors_built = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.grid = QGridLayout(self)
        # The gap to the next record belongs to this record: deleting it closes exactly
        # the space it held, and the list never has an orphan spacer to snap shut. The value
        # cells reach CARET_ROOM past the value edge; what they draw ends on it.
        self.grid.setContentsMargins(ROW_INSET, ROW_PADDING, VALUE_TAIL - CARET_ROOM, ROW_PADDING + ROW_GAP)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(0)
        self.time = FieldLabel()
        self.time.setFont(theme.font(13, tabular=True))
        self.time.setStyleSheet(f"color: {theme.TEXT_2};")
        self.time.setContentsMargins(0, TIME_BASELINE_PAD, 0, 0)
        self.time.setFixedHeight(LINE1_HEIGHT)
        self.grid.addWidget(self.time, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.amount = RowAmount()
        self.amount.setFont(theme.font(17, theme.MEDIUM, tabular=True))
        self.amount.setFixedHeight(LINE1_HEIGHT)
        self.amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.amount, 0, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.description = ElidedLabel()
        self.description.setFont(theme.font(16))
        self.description.setStyleSheet(f"color: {theme.TEXT};")
        self.description.setFixedHeight(LINE2_HEIGHT)
        self.grid.addWidget(self.description, 1, 0)
        self.category = QWidget()
        self.category.setFixedHeight(LINE2_HEIGHT)
        category_layout = QHBoxLayout(self.category)
        category_layout.setContentsMargins(0, 0, CARET_ROOM, 0)
        category_layout.setSpacing(6)
        category_layout.addStretch()
        self.category_dot = QLabel()
        self.category_dot.setFixedSize(6, 6)
        category_layout.addWidget(self.category_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.category_name = QLabel()
        self.category_name.setFont(theme.font(13))
        self.category_name.setStyleSheet(f"color: {theme.TEXT_3};")
        category_layout.addWidget(self.category_name)
        self.grid.addWidget(self.category, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.hint = QLabel()
        self.hint.setObjectName("error")
        self.hint.setTextFormat(Qt.TextFormat.PlainText)
        self.hint.setWordWrap(True)
        self.hint.hide()
        self.grid.addWidget(self.hint, 2, 0, 1, 2)
        self.grid.setColumnStretch(0, 1)
        self.edge = DeleteEdge(self)
        self.edge.activated.connect(lambda: self.delete_requested.emit(self))
        self.show_record(record)

    # ---- display ----------------------------------------------------------
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
        self.category.setToolTip("你指定的分类，会用于本机学习；可在编辑中恢复自动判断。"
                                 if record.get("category_by_user") else
                                 "本机自动判断，结合你的历史纠正；点击可修改。")
        self.setAccessibleName(f"{record['datetime']} {format_amount(record['amount_cents'])} {record['description']}")

    # ---- editors ----------------------------------------------------------
    def _build_editors(self):
        self._editors_built = True
        self.time_edit = QuietDateTimeEdit(line_lift=ROW_LINE_LIFT)
        self.time_edit.setObjectName("rowEdit")
        self.time_edit.setFont(theme.font(13, tabular=True))
        self.time_edit.setDisplayFormat(TIME_SHORT)  # the day heading already says the date; the full date appears on focus
        self.time_edit.setDateRange(QDate(1900, 1, 1), QDate(9999, 12, 31))
        self.time_edit.setButtonSymbols(QDateTimeEdit.ButtonSymbols.NoButtons)
        self.time_edit.setCalendarPopup(False)
        self.time_edit.setFixedHeight(LINE1_HEIGHT)
        self.time_edit.setAccessibleName("消费时间")
        # The same drop the resting time gets, so the baseline does not move on entering Edit.
        self.time_edit.lineEdit().setTextMargins(TIME_TEXT_NUDGE, TIME_BASELINE_PAD, 0, 0)
        self.grid.addWidget(self.time_edit, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # ¥ is a fixed prefix; the user edits only the number.
        self.amount_unit = QWidget()
        self.amount_unit.setFixedHeight(LINE1_HEIGHT)
        unit = QHBoxLayout(self.amount_unit)
        unit.setContentsMargins(0, 0, 0, 0)
        unit.setSpacing(0)
        self.amount_currency = RowCurrency("¥")
        self.amount_currency.setFont(theme.font(17, theme.MEDIUM))
        # Exactly the mark's advance: with the field's caret room after the digits, the unit
        # is as wide as the resting amount and draws ¥ and digits where it drew them. As tall
        # as the field, so the two share one baseline.
        self.amount_currency.setFixedSize(QFontMetrics(self.amount_currency.font()).horizontalAdvance("¥"),
                                          LINE1_HEIGHT)
        unit.addWidget(self.amount_currency, 0, Qt.AlignmentFlag.AlignVCenter)
        self.amount_edit = FittedLineEdit(line_pad=0, line_lift=ROW_LINE_LIFT)
        self.amount_edit.setObjectName("rowEdit")
        self.amount_edit.setFont(theme.font(17, theme.MEDIUM, tabular=True))
        self.amount_edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.amount_edit.setValidator(QRegularExpressionValidator(AMOUNT_PATTERN, self))
        self.amount_edit.setMaxLength(12)
        self.amount_edit.setFixedHeight(LINE1_HEIGHT)
        self.amount_edit.setAccessibleName("金额")
        self.amount_edit.setTextMargins(AMOUNT_TEXT_MARGIN, 0, AMOUNT_TEXT_MARGIN, 0)
        unit.addWidget(self.amount_edit, 0, Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.amount_unit, 0, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.description_edit = QuietLineEdit(line_pad=4, line_lift=ROW_LINE_LIFT)
        self.description_edit.setObjectName("rowEdit")
        self.description_edit.setFont(theme.font(16))
        self.description_edit.setMaxLength(MAX_DESCRIPTION)
        self.description_edit.setPlaceholderText("做了什么？")
        self.description_edit.setFixedHeight(LINE2_HEIGHT)
        self.description_edit.setProperty("field", "description")  # no line at rest: it is still the record's own text
        self.description_edit.setAccessibleName("说明")
        self.description_edit.setTextMargins(DESCRIPTION_TEXT_NUDGE, 0, 0, 0)
        self.grid.addWidget(self.description_edit, 1, 0)
        self.category_box = CategoryBox()
        self.category_box.setObjectName("rowEdit")
        self.category_box.setFont(theme.font(13))
        self.category_box.addItems([*CATEGORIES, UNKNOWN_LABEL, "自动判断"])
        self.category_box.setToolTip("选择类别会在本机学习；自动判断会移除此条记录的个人标签。")
        self.category_box.setFixedHeight(LINE2_HEIGHT)
        self.category_box.setAccessibleName("分类")
        self.grid.addWidget(self.category_box, 1, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for editor in (self.time_edit, self.amount_unit, self.description_edit, self.category_box):
            editor.hide()
        for editor in (self.time_edit, self.amount_edit, self.description_edit, self.category_box):
            editor.installEventFilter(self)
        QWidget.setTabOrder(self.amount_edit, self.description_edit)
        QWidget.setTabOrder(self.description_edit, self.time_edit)
        QWidget.setTabOrder(self.time_edit, self.category_box)
        self.amount_edit.editingFinished.connect(lambda: self.commit("amount"))
        self.description_edit.editingFinished.connect(lambda: self.commit("description"))
        self.time_edit.editingFinished.connect(lambda: self.commit("time"))
        self.category_box.currentIndexChanged.connect(lambda _: self.commit("category", explicit=True))
        self.category_box.activated.connect(lambda _: self.commit("category", explicit=True))

    def _set_time_format(self, fmt):
        """QDateTimeEdit pins its date range to the current date while only time sections are
        shown; the full format must reopen the range before any other date can be set."""
        self.time_edit.setDisplayFormat(fmt)
        if fmt == TIME_FULL:
            self.time_edit.setDateRange(QDate(1900, 1, 1), QDate(9999, 12, 31))

    def _load_editors(self):
        record = self.record
        for editor in (self.time_edit, self.amount_edit, self.description_edit, self.category_box):
            editor.blockSignals(True)
        self.amount_edit.setText(cents_to_input(record["amount_cents"]))
        self.description_edit.setText(record["description"])
        self._set_time_format(TIME_FULL)
        self.time_edit.setDateTime(QDateTime.fromString(record["datetime"], "yyyy-MM-dd HH:mm"))
        if not self.time_edit.hasFocus():
            self._set_time_format(TIME_SHORT)
        category = record["category"]
        self.category_box.setCurrentIndex(CATEGORIES.index(category) if category in CATEGORIES else len(CATEGORIES))
        for editor in (self.time_edit, self.amount_edit, self.description_edit, self.category_box):
            editor.blockSignals(False)

    def begin_edit(self, cell=""):
        if not self._editors_built:
            self._build_editors()
        self._load_editors()
        self.editing = True
        self.hint.hide()
        for label, editor in ((self.time, self.time_edit), (self.amount, self.amount_unit),
                              (self.description, self.description_edit), (self.category, self.category_box)):
            label.hide()
            editor.show()
        self.edge.reset()
        self.edge.show()
        self.edge.raise_()
        self._place_edge()
        target = {"amount": self.amount_edit, "description": self.description_edit,
                  "time": self.time_edit, "category": self.category_box}.get(cell, self)
        target.setFocus()
        if isinstance(target, QLineEdit):
            target.setCursorPosition(len(target.text()))
        self._edit_weight.set(True)

    def _leave_edit_state(self):
        self.editing = False
        self._committing = True
        for label, editor in ((self.time, self.time_edit), (self.amount, self.amount_unit),
                              (self.description, self.description_edit), (self.category, self.category_box)):
            editor.hide()
            label.show()
        self._committing = False
        self.category_dot.setVisible(self.record["category"] in CATEGORIES)
        self.edge.hide()
        self.hint.hide()
        self._edit_weight.set(False)
        self.edit_ended.emit(self)

    def end_edit(self):
        """Commit every field; return False (and stay in Edit) if one of them is invalid."""
        if not self.editing:
            return True
        if not all(self.commit(name) for name in ("amount", "description", "time", "category")):
            return False
        self._leave_edit_state()
        return True

    def cancel_edit(self):
        """Esc: drop whatever is still uncommitted in the fields and leave Edit."""
        if not self.editing:
            return
        self._load_editors()
        self._leave_edit_state()

    # ---- commits: legal changes take effect immediately -------------------
    def _pending(self, name, *, explicit=False):
        if name == "amount":
            text = normalize_amount_text(self.amount_edit.text())
            if not text:
                raise ValueError("金额格式不正确")
            value = parse_amount(text)
            return UNSET if value == self.record["amount_cents"] else value
        if name == "description":
            value = self.description_edit.text().strip()
            return UNSET if value == self.record["description"] else value
        if name == "time":
            value = self.time_edit.dateTime().toPython().replace(second=0, microsecond=0)
            return UNSET if value.strftime("%Y-%m-%d %H:%M") == self.record["datetime"] else value
        if not explicit:
            return UNSET  # only a category-control interaction may create a label
        index = self.category_box.currentIndex()
        if index == len(CATEGORIES) + 1:
            return AUTO if self.record.get("category_by_user") else UNSET
        value = CATEGORIES[index] if 0 <= index < len(CATEGORIES) else None
        return UNSET if value == self.record["category"] and not (
            explicit and not self.record.get("category_by_user")) else value

    def commit(self, name, *, explicit=False):
        if not self.editing or self._committing:
            return True
        try:
            value = self._pending(name, explicit=explicit)
        except ValueError as exc:
            self.hint.setText(str(exc))
            self.hint.show()
            return False
        if value is UNSET:
            return True
        field = {"amount": "amount_cents", "description": "description", "time": "when", "category": "category"}[name]
        old = dict(self.record)
        self._committing = True
        try:
            new, self.last_change = self.ledger.update_undoable(self.record, **{field: value})
        except ValueError as exc:
            self.hint.setText(str(exc))
            self.hint.show()
            return False
        except DatabaseError as exc:
            self.hint.setText(f"无法保存修改，这条记录保持原样。{exc}")
            self.hint.show()
            if name == "category":
                self._load_editors()
            return False
        finally:
            self._committing = False
        self.hint.hide()
        self.show_record(new)
        if self.editing and name != "category":
            # A description edit may change the derived category. Synchronize the
            # display without treating that automatic change as personal evidence.
            blocked = self.category_box.blockSignals(True)
            category = new["category"]
            self.category_box.setCurrentIndex(CATEGORIES.index(category) if category in CATEGORIES else len(CATEGORIES))
            self.category_box.blockSignals(blocked)
        if self.editing:  # keep the labels hidden while editing
            for label in (self.time, self.amount, self.description, self.category):
                label.hide()
        self.changed.emit(self, old, new)
        return True

    # ---- events ----------------------------------------------------------------
    def eventFilter(self, watched, event):
        if watched is getattr(self, "time_edit", None):
            if event.type() == QEvent.Type.FocusIn and self.time_edit.displayFormat() != TIME_FULL:
                self._set_time_format(TIME_FULL)
                self.time_edit.setCurrentSection(QDateTimeEdit.Section.HourSection)
            elif event.type() == QEvent.Type.FocusOut and self.time_edit.displayFormat() != TIME_SHORT:
                self._set_time_format(TIME_SHORT)
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.cancel_edit()
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.end_edit()
                return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if self.editing:
            key = event.key()
            if key == Qt.Key.Key_Delete:
                self.delete_requested.emit(self)
                return
            if key == Qt.Key.Key_Escape:
                self.cancel_edit()
                return
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.end_edit()
                return
        super().keyPressEvent(event)

    def cell_at(self, pos):
        child = self.childAt(pos)
        for name, widget in (("amount", self.amount), ("description", self.description),
                             ("time", self.time), ("category", self.category)):
            if child is widget or (child is not None and widget.isAncestorOf(child)):
                return name
        return ""

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            cell = self.cell_at(event.position().toPoint())
            if self.editing:
                if not cell:
                    self.setFocus()  # selected: Delete applies to the record, not to text
            else:
                self.clicked.emit(self, cell)
        event.accept()

    def enterEvent(self, event):
        self._hover.set(True)

    def leaveEvent(self, event):
        self._hover.set(False)

    def box(self):
        """The row's own surface: everything above the gap it carries for the next one."""
        return QRectF(0, 0, self.width(), max(0, self.height() - ROW_GAP))

    def _place_edge(self):
        box = self.box()
        self.edge.setGeometry(self.width() - EDGE_ROOM - 4, 8, EDGE_ROOM, max(0, int(box.height()) - 16))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_edge()

    def paintEvent(self, event):
        hover, edit = self._hover.value(), self._edit_weight.value()
        if hover <= 0.001 and edit <= 0.001:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        surface = motion.mix(QColor(theme.BG), QColor(theme.HOVER), hover)
        surface = motion.mix(surface, QColor(theme.ACCENT_TINT), edit)
        box = self.box()
        painter.setBrush(surface)
        painter.drawRoundedRect(box.adjusted(0.5, 0.5, -0.5, -0.5), ROW_RADIUS, ROW_RADIUS)
        if edit > 0.001:
            # As tall as the two lines of text it stands beside, and no taller: it marks the
            # record, not the box around it.
            bar = QColor(theme.ACCENT)
            bar.setAlphaF(edit)
            painter.setBrush(bar)
            top = ROW_PADDING + 3
            painter.drawRoundedRect(QRectF(EDIT_BAR_INSET, top, EDIT_BAR, box.height() - 2 * top),
                                    EDIT_BAR / 2.0, EDIT_BAR / 2.0)
