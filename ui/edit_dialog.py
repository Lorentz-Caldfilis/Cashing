from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from database import DatabaseError
from ui.record_form import RecordForm


class EditDialog(QDialog):
    def __init__(self, database, record, parent=None):
        super().__init__(parent)
        self.database = database
        self.record_id = record["id"]
        self.setWindowTitle("编辑消费")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        self.form = RecordForm()
        self.form.set_record(record)
        layout.addWidget(self.form)
        self.error = QLabel()
        self.error.setTextFormat(Qt.TextFormat.PlainText)
        self.error.setWordWrap(True)
        self.error.setStyleSheet("color: #b42318")
        layout.addWidget(self.error)
        buttons = QDialogButtonBox()
        self.save_button = buttons.addButton("保存修改", QDialogButtonBox.ButtonRole.AcceptRole)
        self.save_button.setDefault(True)
        buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        try:
            self.database.update_record(self.record_id, *self.form.values())
        except (ValueError, DatabaseError) as exc:
            self.error.setText(str(exc))
            return
        self.accept()
