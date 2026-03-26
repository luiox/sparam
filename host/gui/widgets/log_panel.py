from time import strftime

from PySide6.QtWidgets import QFrame, QLabel, QTextEdit, QVBoxLayout


class LogPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("logPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Activity")
        title.setProperty("sectionTitle", True)
        subtitle = QLabel("Recent device, monitor and export events")
        subtitle.setProperty("muted", True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

    def append_line(self, message: str) -> None:
        self.text_edit.append(f"{strftime('%H:%M:%S')}  {message}")
