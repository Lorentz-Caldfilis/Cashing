from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QListWidget, QStackedWidget, QScrollArea, QFrame,
)
from ui.input_page import InputPage
from ui.records_page import RecordsPage

STYLE = """
QWidget { font-family: "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
          font-size: 10pt; color: #233347; }
QMainWindow, QDialog { background: #f5f7fa; }
QLabel#title { font-size: 22pt; font-weight: 600; }
QLabel#section { font-size: 12pt; font-weight: 600; }
QLabel#muted { color: #6b7889; }
QLabel#amount { font-size: 15pt; font-weight: 600; color: #087f6b; }
QFrame#card { background: white; border: 1px solid #e3e9ee; border-radius: 10px; }
QPushButton { background: white; border: 1px solid #d9e1e8; border-radius: 6px;
              padding: 9px 14px; }
QPushButton:hover { background: #eaf4f1; border-color: #4aa895; }
QPushButton:pressed { background: #d4ebe4; }
QPushButton#primary { background: #087f6b; color: white; border-color: #087f6b; }
QPushButton#primary:hover { background: #066955; }
QPushButton#danger { color: #b42318; }
QPushButton:disabled, QPushButton#danger:disabled { color: #a3acb7; background: #f1f3f5; border-color: #e3e9ee; }
QLineEdit, QDateTimeEdit, QComboBox, QPlainTextEdit {
    background: white; border: 1px solid #d9e1e8; border-radius: 5px; padding: 9px;
    selection-background-color: #087f6b; }
QLineEdit:focus, QDateTimeEdit:focus, QComboBox:focus { border-color: #087f6b; }
QTableWidget { background: white; alternate-background-color: #f7fafb;
    border: 1px solid #e3e9ee; gridline-color: #edf1f4;
    selection-background-color: #dcefe9; selection-color: #163a30; }
QHeaderView::section { background: #edf2f5; border: none; padding: 10px 5px; }
QListWidget { background: #eaf0f3; border: none; outline: none; }
QListWidget::item { padding: 14px 18px; margin: 4px 8px; border-radius: 6px; }
QListWidget::item:selected { background: #d3e9e1; color: #076753; }
QListWidget::item:hover { background: #dfebe8; }
"""


class MainWindow(QMainWindow):
    def __init__(self, database):
        super().__init__()
        self.setWindowTitle("Cashing · 个人记账")
        screen = QApplication.primaryScreen().availableGeometry()
        self.setMinimumSize(min(900, max(320, screen.width() - 40)),
                            min(600, max(240, screen.height() - 80)))
        self.resize(min(1180, screen.width() - 40), min(780, screen.height() - 60))
        self.setStyleSheet(STYLE)
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QWidget()
        sidebar.setFixedWidth(160)
        side = QVBoxLayout(sidebar)
        brand = QLabel("Cashing")
        brand.setStyleSheet("font-size: 20pt; font-weight: 600; color: #087f6b; padding: 18px 8px")
        side.addWidget(brand)
        self.navigation = QListWidget()
        self.navigation.addItems(["记账", "查看账单"])
        side.addWidget(self.navigation)
        footer = QLabel("个人记账 · v1.0\n数据仅保存在本机")
        footer.setObjectName("muted")
        footer.setStyleSheet("padding: 12px 8px; font-size: 9pt")
        side.addWidget(footer)
        layout.addWidget(sidebar)
        self.pages = QStackedWidget()
        self.input_page = InputPage(database)
        self.records_page = RecordsPage(database)
        self.pages.addWidget(self.input_page)
        self.pages.addWidget(self.records_page)
        self.content_scroll = QScrollArea()
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setWidget(self.pages)
        layout.addWidget(self.content_scroll, 1)
        self.setCentralWidget(central)
        self.navigation.currentRowChanged.connect(self.switch_page)
        self.input_page.saved.connect(self.after_save)
        self.navigation.setCurrentRow(0)
        self.statusBar().showMessage(f"数据文件：{database.path}")
        self.statusBar().setSizeGripEnabled(False)

    def switch_page(self, row):
        self.pages.setCurrentIndex(row)
        if row == 1:
            self.records_page.show_current_month()
        elif row == 0:
            self.input_page.form.amount.setFocus()

    def after_save(self):
        self.records_page.refresh()
