from datetime import datetime
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView, QMessageBox, QMenu,
    QFrame, QPlainTextEdit, QSplitter,
)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from database import DatabaseError
from domain import CATEGORIES, format_amount, shift_month, summarize_records
from ui.edit_dialog import EditDialog

COLORS = ("#219e8f", "#5983d3", "#e2a24d")


class PieChart(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        heading = QLabel("消费构成")
        heading.setObjectName("section")
        layout.addWidget(heading)
        self.figure = Figure(figsize=(3, 3), facecolor="#f5f7fa")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumSize(180, 180)
        self.canvas.setMaximumHeight(320)
        self.axes = self.figure.add_axes((0.06, 0.06, 0.88, 0.88))
        layout.addWidget(self.canvas, 1)
        self.empty = QLabel("本月暂无消费记录")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setObjectName("muted")
        layout.addWidget(self.empty)
        self.legend = {}
        for category, color in zip(CATEGORIES, COLORS):
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}")
            row.addWidget(dot)
            row.addWidget(QLabel(category))
            row.addStretch()
            label = QLabel("0.0%")
            row.addWidget(label)
            self.legend[category] = label
            layout.addLayout(row)
        layout.addStretch()

    def refresh(self, totals):
        # Reuse the one Figure, Axes and Qt canvas; never call pyplot.figure().
        self.axes.clear()
        self.axes.set_axis_off()
        total = totals["total"]
        self.empty.setVisible(total == 0)
        self.canvas.setVisible(total > 0)
        for category in CATEGORIES:
            percent = totals[category] * 100 / total if total else 0
            self.legend[category].setText(
                "<0.1%" if 0 < percent < 0.1 else f"{percent:.1f}%")
        if total:
            active = [(totals[c], color) for c, color in zip(CATEGORIES, COLORS) if totals[c]]
            self.axes.pie(
                [amount for amount, _ in active], colors=[color for _, color in active],
                startangle=90, counterclock=False,
                wedgeprops={"width": 0.48, "edgecolor": "white", "linewidth": 2},
            )
            self.axes.set_aspect("equal")
        self.canvas.draw_idle()


class RecordsPage(QWidget):
    def __init__(self, database):
        super().__init__()
        self.database = database
        now = datetime.now()
        self.year, self.month = now.year, now.month
        self.records = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(18)
        top = QHBoxLayout()
        title = QLabel("查看账单")
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch()
        self.previous = QPushButton("‹")
        self.previous.setAccessibleName("上一个月")
        self.previous.setFixedWidth(40)
        self.previous.clicked.connect(lambda: self.change_month(-1))
        top.addWidget(self.previous)
        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_label.setMinimumWidth(150)
        top.addWidget(self.month_label)
        self.next = QPushButton("›")
        self.next.setAccessibleName("下一个月")
        self.next.setFixedWidth(40)
        self.next.clicked.connect(lambda: self.change_month(1))
        top.addWidget(self.next)
        self.today = QPushButton("本月")
        self.today.clicked.connect(self.show_current_month)
        top.addWidget(self.today)
        layout.addLayout(top)
        cards = QHBoxLayout()
        self.stat_labels = {}
        for key, title in [("total", "总消费"), *[(c, c) for c in CATEGORIES]]:
            card = QFrame()
            card.setObjectName("card")
            inner = QVBoxLayout(card)
            label = QLabel(title)
            label.setObjectName("muted")
            inner.addWidget(label)
            amount = QLabel("¥0.00")
            amount.setObjectName("amount")
            amount.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            inner.addWidget(amount)
            self.stat_labels[key] = amount
            cards.addWidget(card)
        layout.addLayout(cards)
        self.message = QLabel()
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color: #b42318")
        self.message.hide()
        layout.addWidget(self.message)
        splitter = QSplitter()
        self.chart = PieChart()
        self.chart.setMinimumWidth(200)
        splitter.addWidget(self.chart)
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(12, 0, 0, 0)
        self.count_label = QLabel("消费明细")
        self.count_label.setObjectName("section")
        detail_layout.addWidget(self.count_label)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["时间", "类别", "金额", "详细说明"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.row_resize_timer = QTimer(self)
        self.row_resize_timer.setSingleShot(True)
        self.row_resize_timer.setInterval(80)
        self.row_resize_timer.timeout.connect(self.table.resizeRowsToContents)
        self.table.horizontalHeader().sectionResized.connect(lambda *_: self.row_resize_timer.start())
        self.table.verticalHeader().hide()
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(2, 140)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit_selected())
        self.table.itemSelectionChanged.connect(self.selection_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu)
        detail_layout.addWidget(self.table, 1)
        hint = QLabel("双击记录可编辑；选中后可查看完整说明。")
        hint.setObjectName("muted")
        detail_layout.addWidget(hint)
        self.description = QPlainTextEdit()
        self.description.setReadOnly(True)
        self.description.setPlaceholderText("选中一条记录，查看详细说明")
        self.description.setMaximumHeight(90)
        detail_layout.addWidget(self.description)
        buttons = QHBoxLayout()
        self.edit_button = QPushButton("编辑")
        self.edit_button.clicked.connect(self.edit_selected)
        self.delete_button = QPushButton("删除")
        self.delete_button.setObjectName("danger")
        self.delete_button.clicked.connect(self.delete_selected)
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        buttons.addWidget(self.edit_button)
        buttons.addWidget(self.delete_button)
        buttons.addStretch()
        buttons.addWidget(self.refresh_button)
        detail_layout.addLayout(buttons)
        splitter.addWidget(detail)
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([240, 640])
        layout.addWidget(splitter, 1)
        self.selection_changed()

    def show_current_month(self):
        now = datetime.now()
        self.year, self.month = now.year, now.month
        self.refresh()

    def change_month(self, delta):
        try:
            self.year, self.month = shift_month(self.year, self.month, delta)
        except ValueError:
            return
        self.refresh()

    def refresh(self):
        self.month_label.setText(f"{self.year} 年 {self.month} 月")
        self.previous.setEnabled((self.year, self.month) != (1900, 1))
        self.next.setEnabled((self.year, self.month) != (9999, 12))
        try:
            # One read snapshot drives the table, statistics and chart.
            records = self.database.get_records_by_month(self.year, self.month)
        except DatabaseError as exc:
            self.records = []
            self.table.setRowCount(0)
            self.description.clear()
            self.chart.hide()
            for label in self.stat_labels.values():
                label.setText("—")
            self.count_label.setText("消费明细 · 读取失败")
            self.message.setText(str(exc))
            self.message.show()
            self.selection_changed()
            return
        self.message.hide()
        self.chart.show()
        self.records = records
        totals = summarize_records(records)
        for key, label in self.stat_labels.items():
            label.setText(format_amount(totals[key]))
        self.table.setRowCount(0)
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            values = [record["datetime"], record["category"],
                      format_amount(record["amount_cents"]), record["description"]]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)
        self.table.resizeRowsToContents()
        self.count_label.setText(f"消费明细 · {len(records)} 笔")
        self.description.clear()
        self.chart.refresh(totals)
        self.selection_changed()

    def selected_record(self):
        row = self.table.currentRow()
        if not self.table.selectedItems() or not 0 <= row < len(self.records):
            return None
        return self.records[row]

    def selection_changed(self):
        record = self.selected_record()
        self.edit_button.setEnabled(record is not None)
        self.delete_button.setEnabled(record is not None)
        self.description.setPlainText(record["description"] if record else "")

    def context_menu(self, position):
        index = self.table.indexAt(position)
        if not index.isValid():
            return
        self.table.selectRow(index.row())
        menu = QMenu(self)
        edit_action = menu.addAction("编辑")
        delete_action = menu.addAction("删除")
        action = menu.exec(self.table.viewport().mapToGlobal(position))
        if action == edit_action:
            self.edit_selected()
        elif action == delete_action:
            self.delete_selected()
        menu.deleteLater()

    def edit_selected(self):
        record = self.selected_record()
        if record is None:
            return
        dialog = EditDialog(self.database, record, self)
        accepted = dialog.exec() == EditDialog.DialogCode.Accepted
        dialog.deleteLater()
        if accepted:
            self.refresh()

    def delete_selected(self):
        record = self.selected_record()
        if record is None:
            return
        confirm = QMessageBox(self)
        confirm.setWindowTitle("删除消费")
        confirm.setText("确定删除这条记录吗？")
        confirm.setInformativeText(f'{record["datetime"]} · {record["category"]} · {format_amount(record["amount_cents"])}')
        confirm.setIcon(QMessageBox.Icon.Question)
        yes = confirm.addButton("删除", QMessageBox.ButtonRole.AcceptRole)
        no = confirm.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        confirm.setDefaultButton(no)
        confirm.setEscapeButton(no)
        confirm.exec()
        accepted = confirm.clickedButton() == yes
        confirm.deleteLater()
        if not accepted:
            return
        try:
            self.database.delete_record(record["id"])
        except DatabaseError as exc:
            self.message.setText(str(exc))
            self.message.show()
            return
        self.refresh()
