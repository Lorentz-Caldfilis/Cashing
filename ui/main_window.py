"""Cashing main window: two full-window spaces, Capture ⇄ Review, and window-level overlays."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from draft import DraftStore
from ledger import Ledger
from ui import theme
from ui.capture_page import CapturePage
from ui.review_page import ReviewPage
from ui.spaces import SpaceSwitcher, PageDots, EdgeZone, WheelNavigator, EDGE_WIDTH
from ui.toast import Toast

CAPTURE, REVIEW = 0, 1
DOTS_BOTTOM = 20


class MainWindow(QMainWindow):
    def __init__(self, database, data_directory=None):
        super().__init__()
        self.setWindowTitle("Cashing")
        self.ledger = Ledger(database)
        self.drafts = DraftStore(data_directory) if data_directory else None
        screen = QApplication.primaryScreen().availableGeometry()
        self.setMinimumSize(min(640, max(320, screen.width() - 40)), min(480, max(240, screen.height() - 80)))
        self.resize(min(900, screen.width() - 40), min(720, screen.height() - 60))
        QApplication.instance().setFont(theme.font(theme.BASE_PX))
        self.setStyleSheet(theme.STYLE)

        central = QWidget()
        central.setObjectName("space")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        self.spaces = SpaceSwitcher()
        self.capture = CapturePage(self.ledger, self.notify)
        self.review = ReviewPage(self.ledger, self.notify)
        self.spaces.add_page(self.capture)
        self.spaces.add_page(self.review)
        layout.addWidget(self.spaces)
        self.setCentralWidget(central)

        # Window-level overlays: stable positions regardless of the space shown.
        self.dots = PageDots(2, central)
        self.dots.activated.connect(self.switch_to)
        self.left_edge = EdgeZone(-1, central)
        self.left_edge.activated.connect(lambda: self.switch_to(CAPTURE))
        self.right_edge = EdgeZone(+1, central)
        self.right_edge.activated.connect(lambda: self.switch_to(REVIEW))
        self.toast = Toast(central)

        self.capture.changed.connect(self.review.refresh)
        QShortcut(QKeySequence("Alt+Right"), self, activated=lambda: self.switch_to(REVIEW))
        QShortcut(QKeySequence("Alt+Left"), self, activated=lambda: self.switch_to(CAPTURE))
        self.wheel = WheelNavigator(self, self.move_by)
        QApplication.instance().installEventFilter(self.wheel)
        self._restore_draft()
        self._update_overlays()

    # ---- spaces ----------------------------------------------------------
    def current_index(self):
        return self.spaces.current_index()

    def move_by(self, direction):
        self.switch_to(self.spaces.current_index() + direction)

    def switch_to(self, index, animate=True):
        index = max(CAPTURE, min(REVIEW, index))  # no wrap-around
        if index == self.spaces.current_index():
            return False
        self.spaces.set_index(index, animate)
        self.dots.set_index(index)
        self._update_overlays()
        if index == CAPTURE:
            self.capture.focus_default()
        else:
            self.review.refresh()
            self.review.setFocus()
        return True

    def notify(self, text, undo=None, *, danger=False):
        self.toast.show_message(text, undo, danger=danger)

    # ---- draft -------------------------------------------------------------
    def _restore_draft(self):
        if self.drafts is None:
            return
        draft = self.drafts.load()
        if draft is not None:
            self.capture.restore_draft(draft)

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self.wheel)
        if self.drafts is not None:
            self.drafts.save(self.capture.draft())
        super().closeEvent(event)

    # ---- geometry ----------------------------------------------------------
    def _update_overlays(self):
        central = self.centralWidget()
        width, height = central.width(), central.height()
        self.dots.move((width - self.dots.width()) // 2, height - DOTS_BOTTOM - self.dots.height())
        self.left_edge.setGeometry(0, 56, EDGE_WIDTH, max(0, height - 112))
        self.right_edge.setGeometry(width - EDGE_WIDTH, 56, EDGE_WIDTH, max(0, height - 112))
        index = self.spaces.current_index()
        self.left_edge.setVisible(index > CAPTURE)
        self.right_edge.setVisible(index < REVIEW)
        for overlay in (self.left_edge, self.right_edge, self.dots, self.toast):
            overlay.raise_()
        self.toast.reposition()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_overlays()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_overlays()
        if self.spaces.current_index() == CAPTURE:
            self.capture.focus_default()
