from typing import Optional

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..styles.catppuccin import ERROR, MUTED, SUCCESS


class ValueCard(QFrame):
    def __init__(self, name: str, color: str) -> None:
        super().__init__()
        self.setObjectName("valueCard")
        self._last_value: Optional[float] = None
        self.setMinimumWidth(156)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        stripe = QWidget()
        stripe.setFixedWidth(2)
        stripe.setStyleSheet(f"background: {color};")

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(12, 10, 12, 10)
        body_layout.setSpacing(4)

        self.name_label = QLabel(name)
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("font-size: 17px; font-weight: 700;")
        self.delta_label = QLabel("Waiting for data")
        self.delta_label.setProperty("muted", True)
        self.delta_label.setStyleSheet("font-size: 11px;")

        body_layout.addWidget(self.name_label)
        body_layout.addWidget(self.value_label)
        body_layout.addWidget(self.delta_label)

        layout.addWidget(stripe)
        layout.addWidget(body)

    def update_value(self, value: float) -> None:
        self.value_label.setText(f"{value:.3f}")
        if self._last_value is None:
            self.delta_label.setText("First sample")
            self.delta_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        else:
            delta = value - self._last_value
            direction = "up" if delta >= 0 else "down"
            self.delta_label.setText(f"{direction} {delta:+.3f}")
            self.delta_label.setStyleSheet(
                f"color: {SUCCESS if delta >= 0 else ERROR}; font-size: 11px;"
            )
        self._last_value = value
