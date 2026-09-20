"""Cashing main window: two full-window spaces, Capture ⇄ Review, and window-level overlays."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QStackedWidget, QVBoxLayout
from draft import DraftStore
from ledger import Ledger
from ui import theme
from ui.capture_page import CapturePage
from ui.records_page import RecordsPage
from ui.toast import Toast


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
        self.spaces = QStackedWidget()
        self.capture = CapturePage(self.ledger, self.notify)
        self.review = RecordsPage(database)
        self.spaces.addWidget(self.capture)
        self.spaces.addWidget(self.review)
        layout.addWidget(self.spaces)
        self.setCentralWidget(central)
        self.toast = Toast(central)

        self.capture.changed.connect(self.review.refresh)
        QShortcut(QKeySequence("Alt+Right"), self, activated=lambda: self.switch_to(1))
        QShortcut(QKeySequence("Alt+Left"), self, activated=lambda: self.switch_to(0))
        self._restore_draft()

    # ---- spaces ----------------------------------------------------------
    def switch_to(self, index):
        if index == self.spaces.currentIndex():
            return
        self.spaces.setCurrentIndex(index)
        if index == 0:
            self.capture.focus_default()
        else:
            self.review.refresh()

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
        if self.drafts is not None:
            self.drafts.save(self.capture.draft())
        super().closeEvent(event)

    # ---- geometry ----------------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.toast.reposition()

    def showEvent(self, event):
        super().showEvent(event)
        if self.spaces.currentIndex() == 0:
            self.capture.focus_default()
