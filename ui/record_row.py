"""One history record: two quiet lines that turn into editors in place.

Rest → Hover (faint tint) → Edit (accent bar + tint, fields editable, the
delete edge appears on the right) → Delete Armed (the edge expands). Edits
take effect as soon as a field is left; an invalid field is explained under
the row and blocks leaving. Nothing here floats or casts a shadow.
"""
from PySide6.QtCore import Qt, Signal, QRectF, QSize, QEvent, QVariantAnimation, QEasingCurve, QDateTime, QDate, QRegularExpression, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFontMetrics, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QDateTimeEdit, QComboBox, QSizePolicy,
)
from database import DatabaseError
from domain import CATEGORIES, UNKNOWN_LABEL, format_amount, cents_to_input, parse_amount, MAX_DESCRIPTION
from ledger import UNSET
from ui import theme
from ui.capture_page import normalize_amount_text

EDGE_ROOM = 44          # right-hand room reserved for the delete edge (hit zone)
EDGE_COLLAPSED = 2      # the visible strip at rest: a hint, weaker than the left bar
EDGE_EXPANDED = 36
ROW_RADIUS = 6
LINE1_HEIGHT = 21       # includes the 1 px gap to line 2: QGridLayout drops its row spacing once
LINE2_HEIGHT = 24       # hidden editors share the cells, so spacing must not be relied on
ROW_PADDING = 7         # same in Rest and Edit: the list never jumps
TIME_SHORT, TIME_FULL = "HH:mm", "yyyy-MM-dd HH:mm"
AMOUNT_PATTERN = QRegularExpression(r"[0-9]{0,9}(\.[0-9]{0,2})?")


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


class DayHeading(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFont(theme.font(14, theme.MEDIUM))
        self.setStyleSheet(f"color: {theme.TEXT_2}; padding-left: 12px;")


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
        self._animation.setDuration(120)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
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
    """Flat combo with a small painted chevron, so the field still reads as a choice."""

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(theme.TEXT_3))
        pen.setWidthF(1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        x, y = self.width() - 7.0, self.height() / 2.0 - 0.5
        painter.drawLine(QPointF(x - 2.8, y - 1.4), QPointF(x, y + 1.4))
        painter.drawLine(QPointF(x, y + 1.4), QPointF(x + 2.8, y - 1.4))


class FittedLineEdit(QLineEdit):
    """A line edit as wide as its text, so ¥ and the number stay one right-anchored unit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.textChanged.connect(self.updateGeometry)

    def sizeHint(self):
        metrics = QFontMetrics(self.font())
        # 2 px padding per side, QLineEdit's own 2 px margins, one caret: keep ¥ tight against the digits
        width = max(metrics.horizontalAdvance(self.text()), metrics.horizontalAdvance("0.00")) + 9
        return QSize(width, self.height())

    def minimumSizeHint(self):
        return self.sizeHint()


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
        self._hover = False
        self.editing = False
        self._committing = False
        self._editors_built = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(12, ROW_PADDING, 12 + EDGE_ROOM, ROW_PADDING)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(0)
        self.time = QLabel()
        self.time.setFont(theme.font(13, tabular=True))
        self.time.setStyleSheet(f"color: {theme.TEXT_3};")
        self.time.setFixedHeight(LINE1_HEIGHT)
        self.grid.addWidget(self.time, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.amount = QLabel()
        self.amount.setFont(theme.font(17, theme.MEDIUM, tabular=True))
        self.amount.setStyleSheet(f"color: {theme.TEXT};")
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
        self.setAccessibleName(f"{record['datetime']} {format_amount(record['amount_cents'])} {record['description']}")

    # ---- editors ----------------------------------------------------------
    def _build_editors(self):
        self._editors_built = True
        self.time_edit = QDateTimeEdit()
        self.time_edit.setObjectName("rowEdit")
        self.time_edit.setFont(theme.font(13, tabular=True))
        self.time_edit.setDisplayFormat(TIME_SHORT)  # the day heading already says the date; the full date appears on focus
        self.time_edit.setDateRange(QDate(1900, 1, 1), QDate(9999, 12, 31))
        self.time_edit.setButtonSymbols(QDateTimeEdit.ButtonSymbols.NoButtons)
        self.time_edit.setCalendarPopup(False)
        self.time_edit.setFixedHeight(LINE1_HEIGHT)
        self.time_edit.setAccessibleName("消费时间")
        self.grid.addWidget(self.time_edit, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # ¥ is a fixed prefix; the user edits only the number.
        self.amount_unit = QWidget()
        self.amount_unit.setFixedHeight(LINE1_HEIGHT)
        unit = QHBoxLayout(self.amount_unit)
        unit.setContentsMargins(0, 0, 0, 0)
        unit.setSpacing(0)
        self.amount_currency = QLabel("¥")
        self.amount_currency.setFont(theme.font(17, theme.MEDIUM))
        self.amount_currency.setStyleSheet(f"color: {theme.TEXT_2};")
        unit.addWidget(self.amount_currency, 0, Qt.AlignmentFlag.AlignVCenter)
        self.amount_edit = FittedLineEdit()
        self.amount_edit.setObjectName("rowEdit")
        self.amount_edit.setFont(theme.font(17, theme.MEDIUM, tabular=True))
        self.amount_edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.amount_edit.setValidator(QRegularExpressionValidator(AMOUNT_PATTERN, self))
        self.amount_edit.setMaxLength(12)
        self.amount_edit.setFixedHeight(LINE1_HEIGHT)
        self.amount_edit.setAccessibleName("金额")
        unit.addWidget(self.amount_edit, 0, Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.amount_unit, 0, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.description_edit = QLineEdit()
        self.description_edit.setObjectName("rowEdit")
        self.description_edit.setFont(theme.font(16))
        self.description_edit.setMaxLength(MAX_DESCRIPTION)
        self.description_edit.setPlaceholderText("做了什么？")
        self.description_edit.setFixedHeight(LINE2_HEIGHT)
        self.description_edit.setProperty("field", "description")  # the one field with a faint rest hint
        self.description_edit.setAccessibleName("说明")
        self.grid.addWidget(self.description_edit, 1, 0)
        self.category_box = CategoryBox()
        self.category_box.setObjectName("rowEdit")
        self.category_box.setFont(theme.font(13))
        self.category_box.addItems([*CATEGORIES, UNKNOWN_LABEL])
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
        self.category_box.currentIndexChanged.connect(lambda _: self.commit("category"))

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
        self.update()

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
        self.update()
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
    def _pending(self, name):
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
        index = self.category_box.currentIndex()
        value = CATEGORIES[index] if 0 <= index < len(CATEGORIES) else None
        return UNSET if value == self.record["category"] else value

    def commit(self, name):
        if not self.editing or self._committing:
            return True
        try:
            value = self._pending(name)
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
            new = self.ledger.update(self.record, **{field: value})
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
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def _place_edge(self):
        self.edge.setGeometry(self.width() - EDGE_ROOM - 4, 8, EDGE_ROOM, max(0, self.height() - 16))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_edge()

    def paintEvent(self, event):
        if not (self._hover or self.editing):
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.ACCENT_TINT if self.editing else theme.HOVER))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), ROW_RADIUS, ROW_RADIUS)
        if self.editing:
            painter.setBrush(QColor(theme.ACCENT))
            painter.drawRoundedRect(QRectF(0, 5, 3, self.height() - 10), 1.5, 1.5)
