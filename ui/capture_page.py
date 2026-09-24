"""Capture: amount, one line of description, a weak time, one action. Nothing else.

Composition: a narrow column, centred and slightly above the middle, with a
lot of air. No form chrome — the amount is a number, the description is a
sentence, the time is a hint. Errors appear where they happen.
"""
from datetime import datetime
from PySide6.QtCore import (
    Qt, Signal, QTimer, QRegularExpression, QPoint, QPointF, QSize, QDateTime, QDate, QRectF, QEvent,
)
from PySide6.QtGui import QRegularExpressionValidator, QFontMetrics, QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame,
    QDateTimeEdit, QSizePolicy,
)
from database import DatabaseError
from domain import parse_amount, format_amount, cents_to_input, describe_time, MAX_DESCRIPTION
from draft import Draft
from ui import motion, theme
from ui.controls import QuietDateTimeEdit, DATE_TEXT_NUDGE

AMOUNT_PATTERN = QRegularExpression(r"[0-9]{0,9}(\.[0-9]{0,2})?")
COLUMN_WIDTH = 400          # the window may grow; the content column does not
AMOUNT_PX = 54
CURRENCY_PX = 30
AMOUNT_PLACEHOLDER = "0.00"  # a shape, never a value: it is never read back as input
AMOUNT_SLACK = 6            # room for the caret past the last digit, and no more
AMOUNT_BOTTOM_PAD = 2       # must match the #amount rule in the style sheet
# ¥ and the digits are one object, not two widgets that happen to be adjacent: the mark
# sits on the digits' baseline, a fifth of its own height away from the first digit.
CURRENCY_GAP = 4
# A light mark on the left and heavy digits on the right put the pair's visual weight to
# the right of the box that holds it. On top of the caret's own room the pair is set this
# far further left, so that what the eye weighs as the number lands on the axis.
CURRENCY_OPTICAL = 2
RECORD_WIDTH, RECORD_HEIGHT = 96, 34
RECORD_RADIUS = 5
RECORD_TEXT_LIFT = 1     # CJK has no descender: centring the line box sets the word a touch low
# The time layer speaks the app's date language (the same words as the time it edits) and is
# one object: the layer is the frame, the date inside it is written, not boxed again.
POPOVER_FORMAT = "yyyy年M月d日 HH:mm"
# One record is one movement: amount, then (what + when), then the action. The gaps say so:
# the break after the amount is the largest, what and when are a pair, the action stands apart.
ERROR_SLOT = 20          # always reserved, so an error never moves the column
AMOUNT_TO_TEXT = 10      # + ERROR_SLOT: the one real group break
TEXT_TO_TIME = 2
TIME_TO_ACTION = 36
# The column keeps a reserved error slot under the button, so its box is taller than what
# is on screen. These two numbers place the visible group — a little above the middle —
# not the widget: read them together with that slot, never as the composition itself.
ABOVE, BELOW = 9, 10


def normalize_amount_text(text: str) -> str:
    """Forgive the two harmless intermediate shapes the validator allows: '.5' and '5.'."""
    text = text.strip()
    if text.startswith("."):
        text = "0" + text
    if text.endswith("."):
        text = text[:-1]
    return text


class QuietLineEdit(QLineEdit):
    """Text with no box around it.

    Focus is a hairline that fades in under the text: painted inside the widget, so
    nothing resizes and nothing else moves. It is deliberately not a field underline —
    it is as wide as the text and it sits close under the baseline, near enough to
    belong to the word rather than to a box around it (``line_lift`` is measured from
    the widget's bottom edge, which is the one place a caller can reach the baseline
    from). It says "this is live", not "this is an input".
    """

    def __init__(self, parent=None, *, line_width=1.2, line_pad=4, line_min=0, line_lift=0):
        super().__init__(parent)
        self._line_width = line_width
        self._line_pad = line_pad
        self._line_min = line_min
        self._line_lift = line_lift
        self._focus = motion.Blend(self, motion.FOCUS, self.update)
        self.textChanged.connect(self.update)  # the line follows the text, not a box

    def underline_rect(self):
        """As wide as the text it underlines — a box is exactly what this is not."""
        metrics = QFontMetrics(self.font())
        shown = self.text() or self.placeholderText()
        width = max(metrics.horizontalAdvance(shown) + self._line_pad, self._line_min)
        width = min(width, self.width() - 4)
        alignment = self.alignment()
        if alignment & Qt.AlignmentFlag.AlignHCenter:
            x = (self.width() - width) / 2.0
        elif alignment & Qt.AlignmentFlag.AlignRight:
            x = self.width() - 2 - width
        else:
            x = 2
        y = self.height() - self._line_lift - self._line_width
        return QRectF(x, y, width, self._line_width)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._focus.set(True)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._focus.set(False)

    def paintEvent(self, event):
        super().paintEvent(event)
        weight = self._focus.value()
        if weight <= 0.001:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(theme.ACCENT_SOFT)
        color.setAlphaF(weight)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRect(self.underline_rect())


class AmountEdit(QuietLineEdit):
    """A line edit that is exactly as wide as its number, so the amount stays centred."""

    def __init__(self, parent=None):
        super().__init__(parent, line_width=1.5, line_pad=2, line_lift=8)
        self.setObjectName("amount")
        self.setFont(theme.font(AMOUNT_PX, theme.MEDIUM, tabular=True))
        self.setMaxLength(12)
        self.setValidator(QRegularExpressionValidator(AMOUNT_PATTERN, self))
        self.setAccessibleName("金额")
        self.setPlaceholderText(AMOUNT_PLACEHOLDER)
        self.textChanged.connect(self._follow_emptiness)
        self._follow_emptiness("")
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setFrame(False)
        self.textChanged.connect(self.updateGeometry)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))

    def _follow_emptiness(self, text):
        self.setProperty("empty", "true" if not text else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def sizeHint(self):
        metrics = QFontMetrics(self.font())
        # Only the digits plus the caret's room: slack on the right of the number would
        # quietly push the whole amount off the axis it is centred on.
        width = max(metrics.horizontalAdvance(self.text()),
                    metrics.horizontalAdvance(AMOUNT_PLACEHOLDER)) + AMOUNT_SLACK
        return QSize(width, metrics.height() + 6)

    def minimumSizeHint(self):
        return self.sizeHint()

    def baseline_from_bottom(self):
        """Where QLineEdit puts the digits' baseline: the text is centred in the box that
        sizeHint asks for, minus this widget's own bottom padding."""
        metrics = QFontMetrics(self.font())
        height = self.sizeHint().height()
        top = (height - AMOUNT_BOTTOM_PAD - metrics.height()) / 2.0
        return height - (top + metrics.ascent())


class CurrencyMark(QWidget):
    """The ¥ of a headline amount.

    Painted rather than laid out, because a currency mark belongs to the number: it
    stands on the digits' baseline (bottom alignment alone leaves it floating above,
    the two fonts having different descents) and it keeps one small optical gap to the
    first digit instead of a layout spacing. Its box is exactly its ink plus that gap,
    so the pair is as wide as what it draws.
    """

    MARK = "¥"

    def __init__(self, px, height, baseline_from_bottom, parent=None):
        super().__init__(parent)
        self._font = theme.font(px)
        metrics = QFontMetrics(self._font)
        ink = metrics.tightBoundingRect(self.MARK)
        self._ink_left = ink.left()
        self._baseline = height - baseline_from_bottom
        self._muted = False
        self.setFixedSize(ink.width() + CURRENCY_GAP, height)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAccessibleName(self.MARK)

    def text(self):
        return self.MARK

    def set_muted(self, muted):
        """An amount that is only waiting for input is waiting as a whole: the mark steps
        down with the digits, keeping the same relation to them that it has when they are real."""
        if muted != self._muted:
            self._muted = muted
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setFont(self._font)
        painter.setPen(QColor(theme.TEXT_3 if self._muted else theme.TEXT_2))
        painter.drawText(QPointF(-self._ink_left, self._baseline), self.MARK)


class RecordButton(QPushButton):
    """Cashing's single primary action. It paints itself so hover settles softly and a
    press reads as a press: the surface darkens and the word moves down one pixel.
    Nothing scales, nothing springs, nothing casts a shadow."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("record")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._hover = motion.Blend(self, motion.HOVER, self.update)
        self._press = motion.Blend(self, motion.PRESS, self.update)

    def enterEvent(self, event):
        super().enterEvent(event)
        self._hover.set(self.isEnabled())

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hover.set(False)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self._press.set(True)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._press.set(False)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._press.set(True)

    def keyReleaseEvent(self, event):
        super().keyReleaseEvent(event)
        self._press.set(False)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self._hover.jump_to(0.0)
            self._press.jump_to(0.0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if not self.isEnabled():
            surface, edge, ink, drop = (QColor(theme.DISABLED_SURFACE), QColor(theme.DISABLED_BORDER),
                                        QColor(theme.DISABLED_TEXT), 0.0)
        else:
            surface = motion.mix(QColor(theme.ACTION), QColor(theme.ACCENT), self._hover.value())
            surface = motion.mix(surface, QColor(theme.ACCENT_HOVER), self._press.value())
            edge, ink = surface, QColor("#ffffff")
            drop = self._press.value()
        painter.setPen(QPen(edge, 1.0))
        painter.setBrush(surface)
        painter.drawRoundedRect(rect, RECORD_RADIUS, RECORD_RADIUS)
        if self.hasFocus():
            ring = QColor(theme.TEXT)
            ring.setAlphaF(0.55)
            painter.setPen(QPen(ring, 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1.5, 1.5, -1.5, -1.5), RECORD_RADIUS - 1.5, RECORD_RADIUS - 1.5)
        painter.setPen(ink)
        painter.setFont(self.font())
        shift = int(round(drop)) - RECORD_TEXT_LIFT
        painter.drawText(self.rect().adjusted(0, shift, 0, shift),
                         Qt.AlignmentFlag.AlignCenter, self.text())


class TimePopover(QFrame):
    """Light editing layer for the record time; closes on Esc or a click outside.

    The date inside is the same quiet field a record's time becomes in Edit — no second
    box inside the layer's own edge — and it is written as the rest of Cashing writes a
    date. The hour is selected when it opens: the part most often corrected."""
    changed = Signal(datetime)
    reset = Signal()

    def __init__(self, parent):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("popover")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 8, 8)
        layout.setSpacing(12)
        self.edit = QuietDateTimeEdit()
        self.edit.setFont(theme.font(15, tabular=True))
        self.edit.lineEdit().setTextMargins(DATE_TEXT_NUDGE, 0, 0, 0)
        self.edit.setDisplayFormat(POPOVER_FORMAT)
        self.edit.setDateRange(QDate(1900, 1, 1), QDate(9999, 12, 31))
        self.edit.setButtonSymbols(QDateTimeEdit.ButtonSymbols.NoButtons)
        self.edit.setCalendarPopup(False)
        self.edit.setAccessibleName("消费时间")
        self.edit.dateTimeChanged.connect(self._emit)
        layout.addWidget(self.edit)
        self.now_button = QPushButton("现在")
        self.now_button.setObjectName("quiet")
        self.now_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.now_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.now_button.clicked.connect(self._reset)
        layout.addWidget(self.now_button)

    def open_at(self, anchor: QWidget, when: datetime):
        self.edit.blockSignals(True)
        self.edit.setDateTime(QDateTime(when))
        self.edit.blockSignals(False)
        self.adjustSize()
        below = anchor.mapToGlobal(QPoint(0, anchor.height() + 4))
        x = below.x() + (anchor.width() - self.width()) // 2
        screen = anchor.screen().availableGeometry() if anchor.screen() else None
        if screen is not None:
            x = min(max(x, screen.left() + 8), screen.right() - self.width() - 8)
        self.move(x, below.y())
        self.show()
        self.edit.setFocus()
        self.edit.setCurrentSectionIndex(self.edit.sectionCount() - 2 if self.edit.sectionCount() > 1 else 0)

    def _emit(self, value: QDateTime):
        self.changed.emit(value.toPython().replace(second=0, microsecond=0))

    def _reset(self):
        self.reset.emit()
        self.close()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.close()
            return
        super().keyPressEvent(event)


class CapturePage(QWidget):
    changed = Signal()  # the ledger changed (record stored or undone)

    def __init__(self, ledger, notify, parent=None):
        super().__init__(parent)
        self.setObjectName("space")
        self.ledger = ledger
        self.notify = notify
        self._when = None  # None = automatic (now)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 24, 48, 64)
        outer.setSpacing(0)
        outer.addStretch(ABOVE)
        column = QWidget()
        column.setObjectName("column")
        column.setMaximumWidth(COLUMN_WIDTH)
        column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        centred = QHBoxLayout()
        centred.setContentsMargins(0, 0, 0, 0)
        centred.addStretch(1)
        centred.addWidget(column, 100)  # takes all it may (max width), margins share the rest
        centred.addStretch(1)
        outer.addLayout(centred)
        outer.addStretch(BELOW)
        body = QVBoxLayout(column)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Amount ---------------------------------------------------------
        amount_row = QHBoxLayout()
        amount_row.setContentsMargins(0, 0, 0, 0)
        amount_row.setSpacing(0)  # the gap belongs to the mark, not to the layout
        amount_row.addStretch()
        self.amount = AmountEdit()
        self.currency = CurrencyMark(CURRENCY_PX, self.amount.sizeHint().height(),
                                     self.amount.baseline_from_bottom())
        amount_row.addWidget(self.currency, 0, Qt.AlignmentFlag.AlignBottom)
        self.amount.textChanged.connect(lambda text: self.currency.set_muted(not text))
        self.currency.set_muted(True)
        amount_row.addWidget(self.amount, 0, Qt.AlignmentFlag.AlignBottom)
        # Two equal stretches would centre the pair's box; this much room on the right
        # instead leaves the digits where the eye expects the number to be.
        amount_row.addSpacing(2 * CURRENCY_OPTICAL)
        amount_row.addStretch()
        body.addLayout(amount_row)
        self.amount_error = QLabel()
        self.amount_error.setObjectName("error")
        self.amount_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.amount_error.setFixedHeight(ERROR_SLOT)
        body.addWidget(self.amount_error)
        body.addSpacing(AMOUNT_TO_TEXT)

        # Description ----------------------------------------------------
        self.description = QuietLineEdit(line_pad=6, line_lift=1)  # CJK fills its em box: the line clears the strokes
        self.description.setObjectName("description")
        self.description.setFont(theme.font(17))
        self.description.setMaxLength(MAX_DESCRIPTION)
        self.description.setPlaceholderText("做了什么")  # a prompt, not a question the software asks
        self.description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description.setAccessibleName("说明")
        self.description.setFrame(False)
        self.description.setMaximumWidth(320)
        self.description.textChanged.connect(self._description_emptiness)
        self._description_emptiness("")
        body.addWidget(self.description, 0, Qt.AlignmentFlag.AlignHCenter)
        body.addSpacing(TEXT_TO_TIME)

        # Time -----------------------------------------------------------
        self.time_button = QPushButton()
        self.time_button.setObjectName("time")
        # Keyboard focus only: after the layer closes, typing continues where it was, and no
        # frame is left around the time.
        self.time_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.time_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.time_button.setAccessibleName("消费时间")
        self.time_button.setToolTip("点击修改时间")
        self.time_button.clicked.connect(self.open_time_editor)
        body.addWidget(self.time_button, 0, Qt.AlignmentFlag.AlignHCenter)
        body.addSpacing(TIME_TO_ACTION)

        # Action ---------------------------------------------------------
        self.record_button = RecordButton("记录")
        self.record_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)  # a failed click leaves the input focused
        self.record_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_button.setFixedSize(RECORD_WIDTH, RECORD_HEIGHT)
        self.record_button.setFont(theme.font(15))
        self.record_button.setEnabled(False)
        self.record_button.clicked.connect(self.record)
        body.addWidget(self.record_button, 0, Qt.AlignmentFlag.AlignHCenter)
        body.addSpacing(12)
        self.save_error = QLabel()
        self.save_error.setObjectName("error")
        self.save_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.save_error.setWordWrap(True)
        self.save_error.setTextFormat(Qt.TextFormat.PlainText)
        body.addWidget(self.save_error)
        self.save_error_detail = QLabel()
        self.save_error_detail.setObjectName("errorDetail")
        self.save_error_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.save_error_detail.setWordWrap(True)
        self.save_error_detail.setTextFormat(Qt.TextFormat.PlainText)
        body.addWidget(self.save_error_detail)
        body.addSpacing(12)

        self.popover = TimePopover(self)
        self.popover.changed.connect(self.set_time)
        self.popover.reset.connect(self.reset_time)

        QWidget.setTabOrder(self.amount, self.description)
        QWidget.setTabOrder(self.description, self.time_button)
        QWidget.setTabOrder(self.time_button, self.record_button)
        self.amount.returnPressed.connect(self.amount_entered)
        self.amount.textChanged.connect(self._amount_changed)
        self.amount.editingFinished.connect(self._amount_finished)
        self.description.returnPressed.connect(self.record)
        self.description.textChanged.connect(lambda: self._clear_save_error())

        self._clock = QTimer(self)
        self._clock.setInterval(20_000)
        self._clock.timeout.connect(self._refresh_time_label)
        self._clock.start()
        self._refresh_time_label()

    def _description_emptiness(self, text):
        """The prompt waits for input at the placeholder level, exactly as the amount does."""
        self.description.setProperty("empty", "true" if not text else "false")
        self.description.style().unpolish(self.description)
        self.description.style().polish(self.description)

    # ---- state ------------------------------------------------------------
    def current_time(self) -> datetime:
        return self._when if self._when is not None else self.ledger.now()

    def time_is_auto(self) -> bool:
        return self._when is None

    def set_time(self, when: datetime):
        self._when = when.replace(second=0, microsecond=0)
        self._refresh_time_label()

    def reset_time(self):
        self._when = None
        self._refresh_time_label()

    def has_input(self) -> bool:
        return bool(self.amount.text().strip() or self.description.text().strip())

    def draft(self) -> Draft:
        when = "" if self._when is None else self._when.strftime("%Y-%m-%d %H:%M")
        return Draft(self.amount.text(), self.description.text(), when)

    def restore_draft(self, draft: Draft):
        self.amount.setText(draft.amount_text)
        self.description.setText(draft.description)
        when = draft.when_as_datetime()
        if when is None:
            self.reset_time()
        else:
            self.set_time(when)
        self._clear_save_error()
        self.amount_error.clear()

    def focus_default(self):
        """Amount unless the amount is already there — then continue with the description."""
        if self.amount.text().strip():
            self.description.setFocus()
            self.description.setCursorPosition(len(self.description.text()))
        else:
            self.amount.setFocus()

    # ---- amount ------------------------------------------------------------
    def _amount_changed(self, text):
        self.record_button.setEnabled(bool(text.strip()))
        self.amount_error.clear()
        self._clear_save_error()

    def _amount_finished(self):
        """Static shape once the user leaves the field: 28.5 -> 28.50. Never while typing."""
        text = normalize_amount_text(self.amount.text())
        if not text:
            return
        try:
            cents = parse_amount(text)
        except ValueError as exc:
            self.amount_error.setText(str(exc))
            return
        shown = cents_to_input(cents)
        if shown != self.amount.text():
            self.amount.setText(shown)

    def parsed_amount(self):
        text = normalize_amount_text(self.amount.text())
        if not text:
            return None
        return parse_amount(text)

    def amount_entered(self):
        try:
            cents = self.parsed_amount()
        except ValueError as exc:
            self.amount_error.setText(str(exc))
            return
        if cents is None:
            return
        self.description.setFocus()
        self.description.setCursorPosition(len(self.description.text()))

    # ---- time ----------------------------------------------------------------
    def _refresh_time_label(self):
        self.time_button.setText(describe_time(self.current_time(), self.ledger.now()))

    def open_time_editor(self):
        self.popover.open_at(self.time_button, self.current_time())

    # ---- record ----------------------------------------------------------------
    def record(self):
        try:
            cents = self.parsed_amount()
        except ValueError as exc:
            self.amount_error.setText(str(exc))
            self.amount.setFocus()
            return
        if cents is None:
            self.amount.setFocus()
            return
        when = self.current_time()
        description = self.description.text().strip()
        previous = (self.amount.text(), self.description.text(), self._when)
        try:
            stored = self.ledger.create(cents, when, description)
        except (ValueError, DatabaseError) as exc:
            self.save_error.setText("无法保存，这笔记录尚未写入。")
            self.save_error_detail.setText(str(exc))
            return
        # Only after the database confirmed the write.
        self._reset_inputs()
        summary = f"已记录 {format_amount(cents)}" + (f" · {description}" if description else "")
        self.notify(summary, undo=lambda: self.undo(stored, previous))
        self.changed.emit()

    def undo(self, stored, previous):
        try:
            self.ledger.undo_create(stored["id"])
        except DatabaseError as exc:
            self.notify(f"无法撤销，这笔记录仍然保留。{exc}", danger=True)
            return
        amount_text, description, when = previous
        self.amount.setText(amount_text)
        self.description.setText(description)
        self._when = when
        self._refresh_time_label()
        self.amount.setFocus()
        self.amount.setCursorPosition(len(amount_text))
        self.changed.emit()

    def _reset_inputs(self):
        self.amount.clear()
        self.description.clear()
        self._when = None
        self._refresh_time_label()
        self.amount_error.clear()
        self._clear_save_error()
        self.amount.setFocus()

    def _clear_save_error(self):
        self.save_error.clear()
        self.save_error_detail.clear()

    # ---- keys ----------------------------------------------------------------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.popover.isVisible():
            self.popover.close()
            return
        super().keyPressEvent(event)
