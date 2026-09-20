from datetime import datetime
from PySide6.QtCore import QDate, QDateTime, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QDateTimeEdit, QComboBox,
)
from domain import CATEGORIES, parse_amount


class RecordForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        layout.setSpacing(22)
        self.amount = QLineEdit()
        self.amount.setPlaceholderText("例如 28.50")
        self.amount.setMaxLength(12)
        self.amount.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"[0-9]{0,9}(\.[0-9]{0,2})?"), self))
        self.amount.setAccessibleName("消费金额")
        money = QHBoxLayout()
        money.addWidget(QLabel("¥"))
        money.addWidget(self.amount)
        layout.addRow("金额 *", money)
        self.when = QDateTimeEdit(QDateTime.currentDateTime())
        self.when.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.when.setDateRange(QDate(1900, 1, 1), QDate(9999, 12, 31))
        self.when.setCalendarPopup(True)
        layout.addRow("消费时间", self.when)
        self.category = QComboBox()
        self.category.addItems(CATEGORIES)
        layout.addRow("用途类别", self.category)
        self.description = QLineEdit()
        self.description.setMaxLength(200)
        self.description.setPlaceholderText("可不填，最多 200 个字符")
        layout.addRow("详细说明", self.description)
        QWidget.setTabOrder(self.amount, self.when)
        QWidget.setTabOrder(self.when, self.category)
        QWidget.setTabOrder(self.category, self.description)

    def values(self):
        cents = parse_amount(self.amount.text())
        when = datetime.strptime(self.when.dateTime().toString("yyyy-MM-dd HH:mm"), "%Y-%m-%d %H:%M")
        return cents, when, self.category.currentText(), self.description.text()

    def reset(self):
        self.amount.clear()
        self.description.clear()
        self.when.setDateTime(QDateTime.currentDateTime())
        self.amount.setFocus()

    def set_record(self, record):
        cents = record["amount_cents"]
        self.amount.setText(f"{cents // 100}.{cents % 100:02d}")
        self.when.setDateTime(QDateTime.fromString(record["datetime"], "yyyy-MM-dd HH:mm"))
        self.category.setCurrentText(record["category"] or CATEGORIES[0])  # interim until in-place edit (M5)
        self.description.setText(record["description"])
