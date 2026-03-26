from time import strftime

from PySide6.QtWidgets import QFrame, QTextEdit, QVBoxLayout


class LogPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("logPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

    def append_line(self, message: str):
        self.text_edit.append(f"{strftime('%H:%M:%S')}  {message}")
