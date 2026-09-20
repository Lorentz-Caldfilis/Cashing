"""Capture: amount, one line of description, a weak time, one action. Nothing else.

Composition: a narrow column, centred and slightly above the middle, with a
lot of air. No form chrome — the amount is a number, the description is a
sentence, the time is a hint. Errors appear where they happen.
"""
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QTimer, QRegularExpression, QPoint, QSize, QDateTime, QDate
from PySide6.QtGui import QRegularExpressionValidator, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame,
    QDateTimeEdit, QSizePolicy,
)
from database import DatabaseError
from domain import parse_amount, format_amount, cents_to_input, describe_time, MAX_DESCRIPTION
from draft import Draft
from ui import theme

AMOUNT_PATTERN = QRegularExpression(r"[0-9]{0,9}(\.[0-9]{0,2})?")
COLUMN_WIDTH = 480


def normalize_amount_text(text: str) -> str:
    """Forgive the two harmless intermediate shapes the validator allows: '.5' and '5.'."""
    text = text.strip()
    if text.startswith("."):
        text = "0" + text
    if text.endswith("."):
        text = text[:-1]
    return text


class AmountEdit(QLineEdit):
    """A line edit that is exactly as wide as its number, so the amount stays centred."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("amount")
        self.setFont(theme.font(52, theme.MEDIUM, tabular=True))
        self.setMaxLength(12)
        self.setValidator(QRegularExpressionValidator(AMOUNT_PATTERN, self))
        self.setAccessibleName("金额")
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setFrame(False)
        self.textChanged.connect(self.updateGeometry)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))

    def sizeHint(self):
        metrics = QFontMetrics(self.font())
        # QLineEdit keeps ~2px internal margins per side plus padding, border and the caret.
        width = max(metrics.horizontalAdvance(self.text()), metrics.horizontalAdvance("0")) + 20
        return QSize(width, metrics.height() + 6)

    def minimumSizeHint(self):
        return self.sizeHint()


class TimePopover(QFrame):
    """Light editing layer for the record time; closes on Esc or a click outside."""
    changed = Signal(datetime)
    reset = Signal()

    def __init__(self, parent):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("popover")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        self.edit = QDateTimeEdit()
        self.edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.edit.setDateRange(QDate(1900, 1, 1), QDate(9999, 12, 31))
        self.edit.setButtonSymbols(QDateTimeEdit.ButtonSymbols.NoButtons)
        self.edit.setCalendarPopup(False)
        self.edit.setAccessibleName("消费时间")
        self.edit.dateTimeChanged.connect(self._emit)
        layout.addWidget(self.edit)
        self.now_button = QPushButton("现在")
        self.now_button.setObjectName("quiet")
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
        outer.addStretch(5)
        column = QWidget()
        column.setObjectName("column")
        column.setMaximumWidth(COLUMN_WIDTH)
        outer.addWidget(column, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(7)
        body = QVBoxLayout(column)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Amount ---------------------------------------------------------
        amount_row = QHBoxLayout()
        amount_row.setContentsMargins(0, 0, 0, 0)
        amount_row.setSpacing(10)
        amount_row.addStretch()
        self.currency = QLabel("¥")
        self.currency.setFont(theme.font(30))
        self.currency.setStyleSheet(f"color: {theme.TEXT_2}; padding-bottom: 12px;")
        amount_row.addWidget(self.currency, 0, Qt.AlignmentFlag.AlignBottom)
        self.amount = AmountEdit()
        amount_row.addWidget(self.amount, 0, Qt.AlignmentFlag.AlignBottom)
        amount_row.addStretch()
        body.addLayout(amount_row)
        self.amount_error = QLabel()
        self.amount_error.setObjectName("error")
        self.amount_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.amount_error.setFixedHeight(22)
        body.addWidget(self.amount_error)
        body.addSpacing(8)

        # Description ----------------------------------------------------
        self.description = QLineEdit()
        self.description.setObjectName("description")
        self.description.setFont(theme.font(17))
        self.description.setMaxLength(MAX_DESCRIPTION)
        self.description.setPlaceholderText("做了什么？")
        self.description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description.setAccessibleName("说明")
        self.description.setFrame(False)
        self.description.setMaximumWidth(360)
        body.addWidget(self.description, 0, Qt.AlignmentFlag.AlignHCenter)
        body.addSpacing(16)

        # Time -----------------------------------------------------------
        self.time_button = QPushButton()
        self.time_button.setObjectName("time")
        self.time_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.time_button.setAccessibleName("消费时间")
        self.time_button.setToolTip("点击修改时间")
        self.time_button.clicked.connect(self.open_time_editor)
        body.addWidget(self.time_button, 0, Qt.AlignmentFlag.AlignHCenter)
        body.addSpacing(32)

        # Action ---------------------------------------------------------
        self.record_button = QPushButton("记录")
        self.record_button.setObjectName("record")
        self.record_button.setCursor(Qt.CursorShape.PointingHandCursor)
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
