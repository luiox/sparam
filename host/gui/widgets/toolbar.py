from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class Toolbar(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("toolbar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(16)

        brand_wrap = QWidget()
        brand_layout = QHBoxLayout(brand_wrap)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(10)

        self.brand = QLabel("sparam")
        self.brand.setProperty("hero", True)
        self.caption = QLabel("serial tuning monitor")
        self.caption.setProperty("muted", True)

        brand_layout.addWidget(self.brand)
        brand_layout.addWidget(self.caption)
        brand_layout.addStretch(1)

        self.state_chip = QLabel("Idle")
        self.state_chip.setProperty("chip", True)
        self.status_label = QLabel("Pick a symbol file and start a monitor session.")
        self.status_label.setProperty("muted", True)

        layout.addWidget(brand_wrap, 1)
        layout.addWidget(self.state_chip)
        layout.addWidget(self.status_label, 2)

    def set_status_text(self, text: str) -> None:
        self.status_label.setText(text)

    def set_connected(self, connected: bool) -> None:
        self.state_chip.setText("Connected" if connected else "Offline")
        self.state_chip.setProperty("state", "connected" if connected else "idle")
        self.style().unpolish(self.state_chip)
        self.style().polish(self.state_chip)

    def set_paused(self, paused: bool) -> None:
        if paused:
            self.state_chip.setText("Paused")
            self.state_chip.setProperty("state", "warning")
        else:
            current_state = self.state_chip.property("state")
            if current_state == "connected":
                self.state_chip.setText("Connected")
            elif current_state == "idle":
                self.state_chip.setText("Offline")
        self.style().unpolish(self.state_chip)
        self.style().polish(self.state_chip)
