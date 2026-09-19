from PySide6.QtCore import Signal, QTimer, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from database import DatabaseError
from domain import format_amount
from ui.record_form import RecordForm


class InputPage(QWidget):
    saved = Signal()

    def __init__(self, database):
        super().__init__()
        self.database = database
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        title = QLabel("记一笔消费")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("记录当下，每一笔都清楚。")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)
        layout.addSpacing(28)
        self.form = RecordForm()
        self.form.setMaximumWidth(680)
        layout.addWidget(self.form)
        layout.addSpacing(18)
        self.save_button = QPushButton("保存消费")
        self.save_button.setObjectName("primary")
        self.save_button.setFixedWidth(180)
        self.save_button.clicked.connect(self.save)
        layout.addWidget(self.save_button)
        QWidget.setTabOrder(self.form.description, self.save_button)
        self.feedback = QLabel()
        self.feedback.setTextFormat(Qt.TextFormat.PlainText)
        self.feedback.setWordWrap(True)
        self.feedback.setMinimumHeight(48)
        layout.addWidget(self.feedback)
        layout.addStretch()
        self.feedback_timer = QTimer(self)
        self.feedback_timer.setSingleShot(True)
        self.feedback_timer.timeout.connect(self.feedback.clear)
        self.form.amount.returnPressed.connect(self.save)
        self.form.description.returnPressed.connect(self.save)

    def save(self):
        self.feedback_timer.stop()
        try:
            values = self.form.values()
            self.database.add_record(*values)
        except (ValueError, DatabaseError) as exc:
            self.feedback.setStyleSheet("color: #b42318")
            self.feedback.setText(str(exc))
            return
        self.feedback.setStyleSheet("color: #087f6b")
        self.feedback.setText(f"已保存 {format_amount(values[0])} · {values[2]}")
        self.form.reset()
        self.feedback_timer.start(6000)
        self.saved.emit()
