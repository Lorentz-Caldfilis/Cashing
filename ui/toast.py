"""Bottom-centre overlay for light feedback and Undo. Floats; never moves the layout."""
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect
from ui import motion

DURATION_MS = 5000
ERROR_DURATION_MS = 8000
BOTTOM_GAP = 56  # above the page dots


class Toast(QFrame):
    expired = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 8, 8)
        layout.setSpacing(12)
        self.label = QLabel()
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.label)
        self.undo_button = QPushButton("撤销")
        self.undo_button.setObjectName("undo")
        self.undo_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.undo_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.undo_button.clicked.connect(self._run_undo)
        layout.addWidget(self.undo_button)
        self._action = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.dismiss)
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(motion.TOAST)
        self._fade.setEasingCurve(motion.curve())
        self.hide()

    # ---- API ------------------------------------------------------------
    def show_message(self, text, undo=None, *, danger=False):
        """Replace whatever is showing; a pending undo of the previous toast expires."""
        self._expire_pending()
        self._action = undo
        self.label.setText(text)
        self.label.setObjectName("toastDanger" if danger else "toastText")
        self.label.style().unpolish(self.label)
        self.label.style().polish(self.label)
        self.undo_button.setVisible(undo is not None)
        self.adjustSize()
        self.reposition()
        self.raise_()
        self.show()
        self._fade.stop()
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(1.0)
        self._fade.start()
        self._timer.start(ERROR_DURATION_MS if danger else DURATION_MS)

    def dismiss(self):
        self._timer.stop()
        self._expire_pending()
        self.hide()
        self._opacity.setOpacity(0.0)

    def can_undo(self):
        return self.isVisible() and self._action is not None

    def reposition(self):
        parent = self.parentWidget()
        if parent is None:
            return
        self.adjustSize()
        x = (parent.width() - self.width()) // 2
        y = parent.height() - BOTTOM_GAP - self.height()
        self.move(max(0, x), max(0, y))

    # ---- internals ------------------------------------------------------
    def _expire_pending(self):
        if self._action is not None:
            self._action = None
            self.expired.emit()

    def _run_undo(self):
        action, self._action = self._action, None
        self._timer.stop()
        self.hide()
        self._opacity.setOpacity(0.0)
        if action is not None:
            action()
