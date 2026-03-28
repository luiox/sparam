from typing import Dict, Iterable, List, Optional, cast

from PySide6.QtCore import Qt, Signal
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

from sparam.elf_parser import Variable


class Sidebar(QFrame):
    refresh_requested = Signal()
    connect_requested = Signal()
    load_symbols_requested = Signal()
    pause_requested = Signal()
    read_once_requested = Signal()
    write_once_requested = Signal()
    export_png_requested = Signal()
    export_csv_requested = Signal()
    window_changed = Signal(str)
    rate_changed = Signal(str)
    variable_activated = Signal(str)
    variable_remove_requested = Signal(str)
    selection_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("sidebar")

        self._sections: List[QFrame] = []
        self._section_content_widgets: Dict[QFrame, QWidget] = {}
        self._section_toggle_buttons: Dict[QFrame, QPushButton] = {}

        self._connection_section = self._build_connection_section()
        self._monitor_section = self._build_monitor_section()
        self._export_section = self._build_export_section()
        self._io_section = self._build_io_section()
        self._variable_section = self._build_variable_section()

        self._control_panel = self._build_dock_panel()
        control_layout = cast(QVBoxLayout, self._control_panel.layout())
        self.toggle_all_btn = QPushButton("Collapse All")
        self.toggle_all_btn.setProperty("micro", True)
        self.toggle_all_btn.clicked.connect(self.toggle_all_sections)
        control_layout.addWidget(self.toggle_all_btn)
        control_layout.addWidget(self._connection_section)
        control_layout.addWidget(self._monitor_section)
        control_layout.addWidget(self._export_section)
        control_layout.addStretch(1)

        self._io_panel = self._build_dock_panel()
        io_layout = cast(QVBoxLayout, self._io_panel.layout())
        io_layout.addWidget(self._io_section)
        io_layout.addStretch(1)

        self._variable_panel = self._build_dock_panel()
        variable_layout = cast(QVBoxLayout, self._variable_panel.layout())
        variable_layout.addWidget(self._variable_section, 1)

        self._sync_toggle_all_button_text()

    def control_panel_widget(self) -> QFrame:
        return self._control_panel

    def io_panel_widget(self) -> QFrame:
        return self._io_panel

    def variable_panel_widget(self) -> QFrame:
        return self._variable_panel

    def toggle_all_sections(self) -> None:
        target_expanded = not self.all_sections_expanded()
        for section in self._sections:
            self._set_section_expanded(section, target_expanded)
        self._sync_toggle_all_button_text()

    def all_sections_expanded(self) -> bool:
        return all(self._is_section_expanded(section) for section in self._sections)

    def _build_dock_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("sidebar")
        panel.setMinimumWidth(220)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        return panel

    def _build_connection_section(self) -> QFrame:
        section = self._section_shell("Transport")
        body = self._section_body(section)

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
        self.load_symbols_btn = QPushButton("Load Symbols")

        self.connect_btn.clicked.connect(self.connect_requested.emit)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.load_symbols_btn.clicked.connect(self.load_symbols_requested.emit)

        body.addWidget(self._field("Port", self.port_combo))
        body.addWidget(self._field("Baud", self.baud_spin))
        body.addWidget(self._field("Device", self.device_id_spin))

        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(self.connect_btn, 1)
        row.addWidget(self.refresh_btn, 1)
        body.addLayout(row)
        body.addWidget(self.load_symbols_btn)
        return section

    def _build_monitor_section(self) -> QFrame:
        section = self._section_shell("Monitor")
        body = self._section_body(section)

        self.rate_combo = QComboBox()
        self.rate_combo.addItems(
            ["10 ms", "20 ms", "50 ms", "100 ms", "200 ms", "500 ms"]
        )
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

    def _build_export_section(self) -> QFrame:
        section = self._section_shell("Capture")
        body = self._section_body(section)

        self.export_png_btn = QPushButton("PNG Snapshot")
        self.export_csv_btn = QPushButton("CSV Export")
        self.export_png_btn.clicked.connect(self.export_png_requested.emit)
        self.export_csv_btn.clicked.connect(self.export_csv_requested.emit)

        body.addWidget(self.export_png_btn)
        body.addWidget(self.export_csv_btn)
        return section

    def _build_io_section(self) -> QFrame:
        section = self._section_shell("Single Read/Write")
        body = self._section_body(section)

        self.dtype_combo = QComboBox()
        self.dtype_combo.addItems(
            ["float", "uint8", "int8", "uint16", "int16", "uint32", "int32"]
        )
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Value for write")

        self.read_once_btn = QPushButton("Read Once")
        self.write_once_btn = QPushButton("Write Once")

        self.read_once_btn.clicked.connect(self.read_once_requested.emit)
        self.write_once_btn.clicked.connect(self.write_once_requested.emit)

        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(self.read_once_btn, 1)
        row.addWidget(self.write_once_btn, 1)

        body.addWidget(self._field("Type", self.dtype_combo))
        body.addWidget(self._field("Value", self.value_edit))
        body.addLayout(row)
        return section

    def _build_variable_section(self) -> QFrame:
        section = self._section_shell("Variables")
        body = self._section_body(section)

        helper = QLabel("Double-click adds monitor; remove with button below.")
        helper.setProperty("muted", True)
        helper.setWordWrap(True)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Search variables")
        self.filter_edit.textChanged.connect(self._apply_filter)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.currentItemChanged.connect(self._on_current_changed)

        self.remove_var_btn = QPushButton("Remove Selected")
        self.remove_var_btn.clicked.connect(self._emit_remove_selected)

        body.addWidget(helper)
        body.addWidget(self.filter_edit)
        body.addWidget(self.list_widget, 1)
        body.addWidget(self.remove_var_btn)
        return section

    def _section_shell(self, title: str) -> QFrame:
        shell = QFrame()
        shell.setObjectName("sectionCard")
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        header = QLabel(title)
        header.setProperty("sectionTitle", True)
        toggle_btn = QPushButton("-")
        toggle_btn.setProperty("micro", True)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(5)

        header_row.addWidget(header)
        header_row.addStretch(1)
        header_row.addWidget(toggle_btn)
        outer.addLayout(header_row)
        outer.addWidget(content)

        self._sections.append(shell)
        self._section_content_widgets[shell] = content
        self._section_toggle_buttons[shell] = toggle_btn
        toggle_btn.clicked.connect(
            lambda _checked=False, section=shell: self._toggle_section(section)
        )
        return shell

    def _is_section_expanded(self, section: QFrame) -> bool:
        content = self._section_content_widgets[section]
        return not content.isHidden()

    def _set_section_expanded(self, section: QFrame, expanded: bool) -> None:
        content = self._section_content_widgets[section]
        content.setVisible(expanded)
        button = self._section_toggle_buttons[section]
        button.setText("-" if expanded else "+")

    def _toggle_section(self, section: QFrame) -> None:
        self._set_section_expanded(section, not self._is_section_expanded(section))
        self._sync_toggle_all_button_text()

    def _sync_toggle_all_button_text(self) -> None:
        self.toggle_all_btn.setText(
            "Collapse All" if self.all_sections_expanded() else "Expand All"
        )

    def _section_body(self, section: QFrame) -> QVBoxLayout:
        section_layout = cast(QVBoxLayout, section.layout())
        item = section_layout.itemAt(1)
        assert item is not None
        body_widget = item.widget()
        assert body_widget is not None
        body_layout = body_widget.layout()
        assert isinstance(body_layout, QVBoxLayout)
        return body_layout

    def _field(self, label: str, control: QWidget) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        caption = QLabel(label)
        caption.setProperty("muted", True)
        layout.addWidget(caption)
        layout.addWidget(control)
        return wrap

    def set_variables(self, variables: Iterable[Variable]) -> None:
        self.list_widget.clear()
        for variable in sorted(variables, key=lambda item: item.name):
            item = QListWidgetItem(variable.name)
            item.setData(Qt.ItemDataRole.UserRole, variable.name)
            item.setData(Qt.ItemDataRole.UserRole + 1, False)
            self.list_widget.addItem(item)

    def set_monitored(self, name: str, monitored: bool) -> None:
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            base_name = item.data(Qt.ItemDataRole.UserRole) or item.text()
            if base_name == name:
                item.setData(Qt.ItemDataRole.UserRole + 1, monitored)
                item.setText(f"[M] {name}" if monitored else name)
                break

    def set_ports(self, ports: Iterable[str]) -> None:
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

    def current_variable_name(self) -> str:
        item = self.list_widget.currentItem()
        if item is None:
            return ""
        return (item.data(Qt.ItemDataRole.UserRole) or item.text()).strip()

    def current_dtype_label(self) -> str:
        return self.dtype_combo.currentText().strip()

    def set_dtype_label(self, label: str) -> None:
        index = self.dtype_combo.findText(label)
        if index >= 0:
            self.dtype_combo.setCurrentIndex(index)

    def current_write_value(self) -> str:
        return self.value_edit.text().strip()

    def set_rw_value(self, value: str) -> None:
        self.value_edit.setText(value)

    def set_connected(self, connected: bool) -> None:
        self.connect_btn.setText("Disconnect" if connected else "Connect")

    def set_paused(self, paused: bool) -> None:
        self.pause_btn.setText("Resume" if paused else "Pause")

    def _apply_filter(self, text: str) -> None:
        prefix = text.strip().lower()
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            name = item.data(Qt.ItemDataRole.UserRole) or item.text()
            item.setHidden(bool(prefix) and prefix not in name.lower())

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        name = item.data(Qt.ItemDataRole.UserRole) or item.text()
        if name:
            self.variable_activated.emit(name)

    def _emit_remove_selected(self) -> None:
        name = self.current_variable_name()
        if name:
            self.variable_remove_requested.emit(name)

    def _on_current_changed(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        if current:
            self.selection_changed.emit(
                current.data(Qt.ItemDataRole.UserRole) or current.text()
            )
