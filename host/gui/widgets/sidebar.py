from typing import Iterable

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class Sidebar(QFrame):
    refresh_requested = Signal()
    connect_requested = Signal()
    load_symbols_requested = Signal()
    pause_requested = Signal()
    export_png_requested = Signal()
    export_csv_requested = Signal()
    window_changed = Signal(str)
    rate_changed = Signal(str)
    variable_activated = Signal(str)
    selection_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(258)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(self._build_connection_section())
        layout.addWidget(self._build_monitor_section())
        layout.addWidget(self._build_export_section())
        layout.addWidget(self._build_variable_section(), 1)

    def _build_connection_section(self):
        section = self._section_shell("Transport")
        body = section.layout().itemAt(1).widget().layout()

        self.port_combo = QComboBox()
        self.baud_spin = QSpinBox()
        self.baud_spin.setRange(1200, 2_000_000)
        self.baud_spin.setValue(115200)
        self.device_id_spin = QSpinBox()
        self.device_id_spin.setRange(1, 255)
        self.device_id_spin.setValue(1)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setProperty("accent", True)
        self.refresh_btn = QPushButton("Refresh")
        self.load_symbols_btn = QPushButton("Symbols")

        self.connect_btn.clicked.connect(self.connect_requested.emit)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.load_symbols_btn.clicked.connect(self.load_symbols_requested.emit)

        body.addWidget(self._field("Port", self.port_combo))
        body.addWidget(self._field("Baud", self.baud_spin))
        body.addWidget(self._field("Device", self.device_id_spin))

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.connect_btn, 1)
        row.addWidget(self.refresh_btn, 1)
        body.addLayout(row)
        body.addWidget(self.load_symbols_btn)
        return section

    def _build_monitor_section(self):
        section = self._section_shell("Monitor")
        body = section.layout().itemAt(1).widget().layout()

        self.rate_combo = QComboBox()
        self.rate_combo.addItems(["10 ms", "20 ms", "50 ms", "100 ms", "200 ms", "500 ms"])
        self.rate_combo.setCurrentText("10 ms")
        self.rate_combo.currentTextChanged.connect(self.rate_changed.emit)

        self.window_combo = QComboBox()
        self.window_combo.addItems(["5 s", "10 s", "30 s", "Infinite"])
        self.window_combo.currentTextChanged.connect(self.window_changed.emit)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_requested.emit)

        body.addWidget(self._field("Rate", self.rate_combo))
        body.addWidget(self._field("Window", self.window_combo))
        body.addWidget(self.pause_btn)
        return section

    def _build_export_section(self):
        section = self._section_shell("Capture")
        body = section.layout().itemAt(1).widget().layout()

        self.export_png_btn = QPushButton("PNG Snapshot")
        self.export_csv_btn = QPushButton("CSV Export")
        self.export_png_btn.clicked.connect(self.export_png_requested.emit)
        self.export_csv_btn.clicked.connect(self.export_csv_requested.emit)

        body.addWidget(self.export_png_btn)
        body.addWidget(self.export_csv_btn)
        return section

    def _build_variable_section(self):
        section = self._section_shell("Variables")
        body = section.layout().itemAt(1).widget().layout()

        helper = QLabel("Double-click to pin a symbol into the board.")
        helper.setProperty("muted", True)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Search variables")
        self.filter_edit.textChanged.connect(self._apply_filter)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(
            lambda item: self.variable_activated.emit(item.data(1) or item.text())
        )
        self.list_widget.currentItemChanged.connect(self._on_current_changed)

        body.addWidget(helper)
        body.addWidget(self.filter_edit)
        body.addWidget(self.list_widget, 1)
        return section

    def _section_shell(self, title: str):
        shell = QFrame()
        shell.setObjectName("sectionCard")
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        header = QLabel(title)
        header.setProperty("sectionTitle", True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        outer.addWidget(header)
        outer.addWidget(content)
        return shell

    def _field(self, label: str, control):
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        caption = QLabel(label)
        caption.setProperty("muted", True)
        layout.addWidget(caption)
        layout.addWidget(control)
        return wrap

    def set_variables(self, variables: Iterable):
        self.list_widget.clear()
        for variable in sorted(variables, key=lambda item: item.name):
            item = QListWidgetItem(variable.name)
            item.setData(1, variable.name)
            self.list_widget.addItem(item)

    def set_monitored(self, name: str, monitored: bool):
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.data(1) == name:
                item.setText(name)
                item.setData(1, name)
                font = QFont(item.font())
                font.setBold(monitored)
                item.setFont(font)
                break

    def set_ports(self, ports: Iterable[str]):
        current = self.port_combo.currentText()
        self.port_combo.clear()
        self.port_combo.addItems(list(ports))
        if current:
            index = self.port_combo.findText(current)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)

    def current_port(self) -> str:
        return self.port_combo.currentText().strip()

    def current_baudrate(self) -> int:
        return self.baud_spin.value()

    def current_device_id(self) -> int:
        return self.device_id_spin.value()

    def current_rate_label(self) -> str:
        return self.rate_combo.currentText()

    def set_connected(self, connected: bool):
        self.connect_btn.setText("Disconnect" if connected else "Connect")

    def set_paused(self, paused: bool):
        self.pause_btn.setText("Resume" if paused else "Pause")

    def _apply_filter(self, text: str):
        prefix = text.strip().lower()
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            name = item.data(1) or item.text()
            item.setHidden(bool(prefix) and prefix not in name.lower())

    def _on_current_changed(self, current: QListWidgetItem, _previous: QListWidgetItem):
        if current:
            self.selection_changed.emit(current.data(1) or current.text())
