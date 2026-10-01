"""Cashing main window: two full-window spaces, Capture ⇄ Review, and window-level overlays."""
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import QPoint, QUrl, QTimer, Qt
from PySide6.QtGui import QShortcut, QKeySequence, QDesktopServices, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QToolButton, QMenu, QMessageBox, QFileDialog, QLabel
from draft import DraftStore
from database import DatabaseError
from ledger import Ledger
from ui import theme
from ui.capture_page import CapturePage
from ui.controls import MoreButton
from ui.review_page import ReviewPage, HEADER_LINE
from ui.spaces import (
    SpaceSwitcher, SpaceNavigation, EdgeZone, WheelNavigator, EDGE_WIDTH, FOOTER_HEIGHT, DOTS_HEIGHT,
)
from ui.toast import Toast

CAPTURE, REVIEW = 0, 1
MENU_GAP = 4
DOTS_BOTTOM = (FOOTER_HEIGHT - DOTS_HEIGHT) // 2   # the dots on the footer band's middle line
WINDOW_WIDTH, WINDOW_HEIGHT = 1000, 760


class AnchoredMenu(QMenu):
    """The ⋮ menu hangs from its button: right edges aligned, just below it, so it opens
    inside the window instead of spilling past the window's edge onto the desktop."""

    def showEvent(self, event):
        super().showEvent(event)
        anchor = self.parentWidget()
        if anchor is None:
            return
        corner = anchor.mapToGlobal(QPoint(anchor.width(), anchor.height() + MENU_GAP))
        self.move(corner.x() - self.width(), corner.y())


class MainWindow(QMainWindow):
    def __init__(self, database, data_directory=None):
        super().__init__()
        self.setWindowTitle("Cashing")
        self.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[1] / "assets/cashing-icon.ico")))
        self.ledger = Ledger(database)
        self.drafts = DraftStore(data_directory) if data_directory else None
        screen = QApplication.primaryScreen().availableGeometry()
        self.setMinimumSize(min(640, max(320, screen.width() - 40)), min(440, max(240, screen.height() - 80)))
        self.resize(min(WINDOW_WIDTH, screen.width() - 40), min(WINDOW_HEIGHT, screen.height() - 60))
        QApplication.instance().setFont(theme.font(theme.BASE_PX))
        theme.install(QApplication.instance())

        central = QWidget()
        central.setObjectName("space")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        self.spaces = SpaceSwitcher()
        self.capture = CapturePage(self.ledger, self.notify)
        self.review = ReviewPage(self.ledger, self.notify)
        self.review.capture_requested.connect(lambda: self.switch_to(CAPTURE))
        self.spaces.add_page(self.capture)
        self.spaces.add_page(self.review)
        layout.addWidget(self.spaces)
        self.setCentralWidget(central)

        # Window-level overlays: stable positions regardless of the space shown.
        self.brand = QLabel("Cashing", central)
        self.brand.setFont(theme.font(18, theme.MEDIUM))
        theme.set_style(self.brand, "color: {TEXT_2}; background: transparent;")
        self.brand.adjustSize()
        self.local_note = QLabel("仅存本机 · 无需联网", central)
        self.local_note.setFont(theme.font(12))
        theme.set_style(self.local_note, "color: {TEXT_3}; background: transparent;")
        self.local_note.adjustSize()
        self.navigation = SpaceNavigation(2, central)
        self.navigation.activated.connect(self.switch_to)
        self.left_edge = EdgeZone(-1, central)
        self.left_edge.activated.connect(lambda: self.switch_to(CAPTURE))
        self.right_edge = EdgeZone(+1, central)
        self.right_edge.activated.connect(lambda: self.switch_to(REVIEW))
        self.toast = Toast(central)
        self.utility = MoreButton("更多", central)
        self.utility.setObjectName("utility")
        self.utility.setText("⋮")  # named for assistive technology; the glyph itself is painted
        self.utility.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.utility_menu = AnchoredMenu(self.utility)
        self.open_data_action = self.utility_menu.addAction("打开数据目录")
        self.open_data_action.triggered.connect(self.open_data_directory)
        self.backup_action = self.utility_menu.addAction("备份账本…")
        self.backup_action.triggered.connect(self.backup_ledger)
        self.utility_menu.addSeparator()
        self.about_action = self.utility_menu.addAction("关于 Cashing")
        self.about_action.triggered.connect(self.show_about)
        self.utility.setMenu(self.utility_menu)
        self.data_directory = Path(data_directory) if data_directory else None
        self.database_path = database.path

        self.capture.changed.connect(self._capture_changed)
        QShortcut(QKeySequence("Alt+Right"), self, activated=lambda: self.switch_to(REVIEW))
        QShortcut(QKeySequence("Alt+Left"), self, activated=lambda: self.switch_to(CAPTURE))
        QShortcut(QKeySequence("Ctrl+Alt+Z"), self, activated=self._undo_recent)
        self.wheel = WheelNavigator(self, self.move_by)
        QApplication.instance().installEventFilter(self.wheel)
        self._draft_timer = QTimer(self)
        self._draft_timer.setSingleShot(True)
        self._draft_timer.setInterval(350)
        self._draft_timer.timeout.connect(self._save_draft)
        self.capture.draft_changed.connect(self._draft_timer.start)
        self.capture.changed.connect(self._save_draft)
        self._restore_draft()
        self._update_overlays()

    # ---- spaces ----------------------------------------------------------
    def _capture_changed(self):
        if self.current_index() == REVIEW:
            self.review.refresh()
        # Hidden Review is freshly queried by switch_to; no duplicate monthly work.

    def current_index(self):
        return self.spaces.current_index()

    def focusNextPrevChild(self, next):
        """Clipped sliding pages remain visible to Qt; keep Tab in the active space."""
        current = QApplication.focusWidget() or self
        candidate = current
        inactive = self.spaces.page(1 - self.current_index())
        while True:
            candidate = candidate.nextInFocusChain() if next else candidate.previousInFocusChain()
            if candidate is current:
                return False
            if (candidate.window() is self and candidate.isVisible() and candidate.isEnabled()
                    and candidate.focusPolicy() & Qt.FocusPolicy.TabFocus
                    and candidate is not inactive and not inactive.isAncestorOf(candidate)):
                candidate.setFocus(Qt.FocusReason.TabFocusReason if next else Qt.FocusReason.BacktabFocusReason)
                return True

    def move_by(self, direction):
        self.switch_to(self.spaces.current_index() + direction)

    def switch_to(self, index, animate=True):
        index = max(CAPTURE, min(REVIEW, index))  # no wrap-around
        if index == self.spaces.current_index():
            return False
        if index == CAPTURE and not self.review.prepare_leave():
            return False  # an invalid edit must be fixed or cancelled first
        if index == REVIEW:
            # Bring the destination up to date before it starts moving: the two spaces
            # slide as they are, and nothing re-lays out during the transition.
            self.review.refresh()
        self.spaces.set_index(index, animate)
        self.navigation.set_index(index)
        self._update_overlays()
        if index == CAPTURE:
            self.capture.focus_default()
        else:
            self.review.setFocus()
        return True

    def _undo_recent(self):
        if self.toast.can_undo():
            self.toast._run_undo()

    def notify(self, text, undo=None, *, danger=False):
        self.toast.show_message(text, undo, danger=danger)

    # ---- utility (low-frequency, never a third space) ---------------------
    def open_data_directory(self):
        target = self.data_directory or self.database_path.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def backup_ledger(self):
        suggested = (self.data_directory or self.database_path.parent) / (
            "Cashing-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".sqlite3")
        filename, _ = QFileDialog.getSaveFileName(
            self, "备份账本（未加密；请选择新文件名）", str(suggested), "SQLite 账本 (*.sqlite3)")
        if not filename:
            return
        try:
            target = self.ledger.backup_to(filename)
        except DatabaseError as exc:
            self.notify(str(exc), danger=True)
            return
        self.notify(f"账本已备份到 {target.name}（未加密）")

    def about_text(self):
        version = QApplication.applicationVersion() or ""
        return (f"Cashing {version}".strip() + "\n本地个人消费记录，数据只保存在本机。\n\n"
                f"账单文件：{self.database_path}")

    def show_about(self):
        QMessageBox.about(self, "关于 Cashing", self.about_text())

    # ---- draft -------------------------------------------------------------
    def _restore_draft(self):
        if self.drafts is None:
            return
        draft = self.drafts.load()
        if draft is not None:
            self.capture.restore_draft(draft)

    def _save_draft(self):
        self._draft_timer.stop()
        if self.drafts is not None:
            if not self.drafts.save(self.capture.draft()):
                self.notify("草稿未能保存到本机，请保留窗口并检查磁盘权限。", danger=True)
                return False
        return True

    def closeEvent(self, event):
        if not self.review.prepare_leave():
            event.ignore()
            return
        if not self._save_draft():
            event.ignore()
            return
        QApplication.instance().removeEventFilter(self.wheel)
        super().closeEvent(event)

    # ---- geometry ----------------------------------------------------------
    def _update_overlays(self):
        central = self.centralWidget()
        width, height = central.width(), central.height()
        self.brand.move(28, HEADER_LINE - self.brand.height() // 2)
        self.local_note.move(28, height - (FOOTER_HEIGHT + self.local_note.height()) // 2)
        self.local_note.setVisible(width >= 760)
        self.navigation.move((width - self.navigation.width()) // 2, height - DOTS_BOTTOM - self.navigation.height())
        self.left_edge.setGeometry(0, 56, EDGE_WIDTH, max(0, height - 112))
        self.right_edge.setGeometry(width - EDGE_WIDTH, 56, EDGE_WIDTH, max(0, height - 112))
        index = self.spaces.current_index()
        self.left_edge.setVisible(index > CAPTURE)
        self.right_edge.setVisible(index < REVIEW)
        # On the header's line (month, search) rather than just above it; the same place in both spaces.
        self.utility.move(width - self.utility.width() - 16, HEADER_LINE - self.utility.height() // 2)
        for overlay in (self.left_edge, self.right_edge, self.navigation, self.utility, self.toast, self.brand, self.local_note):
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
