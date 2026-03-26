import struct
import sys
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
)

from sparam import DataType, Device, SerialConnection, ElfParser


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("sparam GUI (PySide6)")
        self.resize(980, 640)

        self.conn: Optional[SerialConnection] = None
        self.device: Optional[Device] = None
        self.parser = ElfParser()
        self.current_elf_path: Optional[str] = None
        self.monitor_var_name: Optional[str] = None
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.poll_monitored_var)

        self._build_ui()
        self.refresh_ports()

    def _build_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        conn_box = QWidget()
        conn_layout = QGridLayout(conn_box)

        self.port_combo = QComboBox()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_ports)

        self.baud_spin = QSpinBox()
        self.baud_spin.setRange(1200, 2000000)
        self.baud_spin.setValue(115200)

        self.device_id_spin = QSpinBox()
        self.device_id_spin.setRange(1, 255)
        self.device_id_spin.setValue(1)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connect)

        conn_layout.addWidget(QLabel("Port"), 0, 0)
        conn_layout.addWidget(self.port_combo, 0, 1)
        conn_layout.addWidget(self.refresh_btn, 0, 2)
        conn_layout.addWidget(QLabel("Baud"), 0, 3)
        conn_layout.addWidget(self.baud_spin, 0, 4)
        conn_layout.addWidget(QLabel("Device ID"), 0, 5)
        conn_layout.addWidget(self.device_id_spin, 0, 6)
        conn_layout.addWidget(self.connect_btn, 0, 7)

        elf_box = QWidget()
        elf_layout = QHBoxLayout(elf_box)
        self.elf_path_edit = QLineEdit()
        self.elf_path_edit.setPlaceholderText("Select .elf / .out / .map")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_elf)
        self.load_elf_btn = QPushButton("Load Symbols")
        self.load_elf_btn.clicked.connect(self.load_elf)

        elf_layout.addWidget(QLabel("ELF/MAP"))
        elf_layout.addWidget(self.elf_path_edit, 1)
        elf_layout.addWidget(self.browse_btn)
        elf_layout.addWidget(self.load_elf_btn)

        body = QWidget()
        body_layout = QHBoxLayout(body)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        self.var_filter_edit = QLineEdit()
        self.var_filter_edit.setPlaceholderText("Filter variable name prefix")
        self.var_filter_edit.textChanged.connect(self.filter_variables)
        self.var_list = QListWidget()
        self.var_list.currentTextChanged.connect(self.on_var_selected)

        left_layout.addWidget(QLabel("Variables"))
        left_layout.addWidget(self.var_filter_edit)
        left_layout.addWidget(self.var_list, 1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        form_host = QWidget()
        form = QFormLayout(form_host)
        self.var_name_label = QLabel("-")
        self.var_addr_label = QLabel("-")
        self.var_type_label = QLabel("-")

        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Value")
        self.dtype_combo = QComboBox()
        self.dtype_combo.addItems([dt.name.lower() for dt in DataType])

        form.addRow("Name", self.var_name_label)
        form.addRow("Address", self.var_addr_label)
        form.addRow("Detected Type", self.var_type_label)
        form.addRow("Write Type", self.dtype_combo)
        form.addRow("Value", self.value_edit)

        action_row = QWidget()
        action_layout = QHBoxLayout(action_row)
        self.read_btn = QPushButton("Read")
        self.write_btn = QPushButton("Write")
        self.monitor_btn = QPushButton("Start Periodic")
        self.stop_monitor_btn = QPushButton("Stop")
        self.monitor_interval_ms = QSpinBox()
        self.monitor_interval_ms.setRange(50, 5000)
        self.monitor_interval_ms.setValue(200)
        self.monitor_interval_ms.setSuffix(" ms")
        self.read_btn.clicked.connect(self.read_selected)
        self.write_btn.clicked.connect(self.write_selected)
        self.monitor_btn.clicked.connect(self.start_periodic_read)
        self.stop_monitor_btn.clicked.connect(self.stop_periodic_read)
        action_layout.addWidget(self.read_btn)
        action_layout.addWidget(self.write_btn)
        action_layout.addWidget(self.monitor_interval_ms)
        action_layout.addWidget(self.monitor_btn)
        action_layout.addWidget(self.stop_monitor_btn)

        self.monitor_table = QTableWidget(0, 3)
        self.monitor_table.setHorizontalHeaderLabels(["Time", "Variable", "Value"])

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        right_layout.addWidget(QLabel("Selected Variable"))
        right_layout.addWidget(form_host)
        right_layout.addWidget(action_row)
        right_layout.addWidget(QLabel("Periodic Read List"))
        right_layout.addWidget(self.monitor_table, 1)
        right_layout.addWidget(QLabel("Log"))
        right_layout.addWidget(self.log_view, 1)

        body_layout.addWidget(left_panel, 1)
        body_layout.addWidget(right_panel, 1)

        layout.addWidget(conn_box)
        layout.addWidget(elf_box)
        layout.addWidget(body, 1)

    def _log(self, text: str):
        self.log_view.append(text)

    def refresh_ports(self):
        self.port_combo.clear()
        for port in SerialConnection.list_ports():
            self.port_combo.addItem(port)
        if self.port_combo.count() == 0:
            self._log("No serial ports found.")

    def toggle_connect(self):
        if self.conn and self.conn.is_open():
            self.conn.close()
            self.conn = None
            self.device = None
            self.connect_btn.setText("Connect")
            self._log("Disconnected.")
            return

        port = self.port_combo.currentText().strip()
        if not port:
            QMessageBox.warning(self, "Connection", "Please select a serial port.")
            return

        conn = SerialConnection(port, self.baud_spin.value(), timeout=1.0)
        if not conn.open():
            reason = conn.last_error or "port busy or unavailable"
            self._log(f"CONNECT FAIL: unable to open {port} ({reason})")
            QMessageBox.critical(self, "Connection", f"Failed to open {port}.")
            return

        device = Device(conn, self.device_id_spin.value(), elf_parser=self.parser)
        if not device.ping(timeout=1.0):
            conn.close()
            reason = device.last_error or "ping timeout"
            self._log(f"CONNECT FAIL: {reason}")
            QMessageBox.warning(self, "Connection", "Ping failed. Check device id and cable.")
            return

        self.conn = conn
        self.device = device
        self.connect_btn.setText("Disconnect")
        self._log(f"Connected to {port} (baud={self.baud_spin.value()}).")

    def browse_elf(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open ELF or MAP",
            str(Path.cwd()),
            "ELF/MAP Files (*.elf *.out *.map);;All Files (*)",
        )
        if path:
            self.elf_path_edit.setText(path)

    def load_elf(self):
        filepath = self.elf_path_edit.text().strip()
        if not filepath:
            QMessageBox.warning(self, "Load Symbols", "Please choose an ELF/MAP file.")
            return

        try:
            if filepath.endswith((".elf", ".out")):
                variables = self.parser.parse_elf(filepath)
            elif filepath.endswith(".map"):
                variables = self.parser.parse_map(filepath)
            else:
                variables = self.parser.parse(filepath)
        except Exception as exc:
            QMessageBox.critical(self, "Load Symbols", f"Failed to parse file: {exc}")
            return

        self.current_elf_path = filepath
        self.var_list.clear()
        for v in variables:
            self.var_list.addItem(v.name)

        self._log(f"Loaded {len(variables)} variables from {Path(filepath).name}.")
        if not self.device:
            self._log("Symbol-only mode: connect a device to enable Read/Write.")

    def filter_variables(self, text: str):
        prefix = text.strip()
        for i in range(self.var_list.count()):
            item = self.var_list.item(i)
            item.setHidden(bool(prefix) and not item.text().startswith(prefix))

    def on_var_selected(self, name: str):
        if not name:
            return

        var = self.parser.get_variable(name)
        if not var:
            return

        self.var_name_label.setText(var.name)
        self.var_addr_label.setText(f"0x{var.address:08X}")
        self.var_type_label.setText(var.var_type)
        self.dtype_combo.setCurrentText(self._dtype_to_name(var.dtype_code))

    @staticmethod
    def _dtype_to_name(dtype_code: int) -> str:
        try:
            return DataType(dtype_code).name.lower()
        except ValueError:
            return DataType.UINT32.name.lower()

    def _selected_variable(self):
        name = self.var_list.currentItem().text() if self.var_list.currentItem() else ""
        return self.parser.get_variable(name) if name else None

    def read_selected(self):
        var = self._selected_variable()
        if not var:
            self._log("READ FAIL: no variable selected")
            QMessageBox.warning(self, "Read", "Please select a variable first.")
            return
        if not self.device:
            self._log("READ FAIL: no device connected")
            QMessageBox.warning(self, "Read", "No device connected. Load symbols works offline, Read needs a serial device.")
            return

        self.device.stop_monitor()

        value = self.device.read_value(var, timeout=1.0)
        if value is None:
            self._log(f"READ FAIL {var.name}: {self.device.last_error or 'unknown error'}")
            QMessageBox.warning(self, "Read", "Read failed.")
            return

        dtype = DataType(var.dtype_code) if var.dtype_code in [d.value for d in DataType] else DataType.UINT32
        try:
            decoded = struct.unpack(dtype.format_char, value[: dtype.size])[0]
            self.value_edit.setText(str(decoded))
            self._log(f"READ {var.name} = {decoded}")
        except Exception:
            hex_value = value.hex()
            self.value_edit.setText(hex_value)
            self._log(f"READ {var.name} = 0x{hex_value}")

    def write_selected(self):
        var = self._selected_variable()
        if not var:
            self._log("WRITE FAIL: no variable selected")
            QMessageBox.warning(self, "Write", "Please select a variable first.")
            return
        if not self.device:
            self._log("WRITE FAIL: no device connected")
            QMessageBox.warning(self, "Write", "No device connected. Load symbols works offline, Write needs a serial device.")
            return

        self.device.stop_monitor()

        raw_text = self.value_edit.text().strip()
        if not raw_text:
            self._log("WRITE FAIL: empty value")
            QMessageBox.warning(self, "Write", "Please input a value.")
            return

        dtype_name = self.dtype_combo.currentText().upper()
        dtype = DataType[dtype_name]

        try:
            if dtype == DataType.FLOAT:
                payload = struct.pack(dtype.format_char, float(raw_text))
            else:
                payload = struct.pack(dtype.format_char, int(raw_text, 0))
        except Exception as exc:
            self._log(f"WRITE FAIL {var.name}: invalid value {raw_text} ({exc})")
            QMessageBox.warning(self, "Write", f"Invalid value: {exc}")
            return

        if self.device.write_single(var, payload, timeout=1.0, dtype_override=dtype):
            self._log(f"WRITE {var.name} <= {raw_text} ({dtype.name})")
        else:
            self._log(f"WRITE FAIL {var.name}: {self.device.last_error or 'unknown error'}")
            QMessageBox.warning(self, "Write", "Write failed.")

    def start_periodic_read(self):
        var = self._selected_variable()
        if not var:
            self._log("MONITOR FAIL: no variable selected")
            return
        if not self.device:
            self._log("MONITOR FAIL: no device connected")
            return

        self.monitor_var_name = var.name
        self.monitor_timer.start(self.monitor_interval_ms.value())
        self._log(
            f"MONITOR START {var.name} every {self.monitor_interval_ms.value()} ms"
        )

    def stop_periodic_read(self):
        if self.monitor_timer.isActive():
            self.monitor_timer.stop()
            self._log("MONITOR STOP")

    def poll_monitored_var(self):
        if not self.monitor_var_name or not self.device:
            return

        var = self.parser.get_variable(self.monitor_var_name)
        if not var:
            self._log("MONITOR FAIL: variable not found in parser")
            self.stop_periodic_read()
            return

        value = self.device.read_value(var, timeout=0.5)
        if value is None:
            self._log(f"MONITOR FAIL {var.name}: {self.device.last_error or 'unknown error'}")
            return

        dtype = DataType(var.dtype_code) if var.dtype_code in [d.value for d in DataType] else DataType.UINT32
        try:
            decoded = struct.unpack(dtype.format_char, value[: dtype.size])[0]
            shown = str(decoded)
        except Exception:
            shown = "0x" + value.hex()

        row = self.monitor_table.rowCount()
        self.monitor_table.insertRow(row)
        self.monitor_table.setItem(row, 0, QTableWidgetItem(time.strftime("%H:%M:%S")))
        self.monitor_table.setItem(row, 1, QTableWidgetItem(var.name))
        self.monitor_table.setItem(row, 2, QTableWidgetItem(shown))
        self.monitor_table.scrollToBottom()

    def closeEvent(self, event):
        self.monitor_timer.stop()
        if self.conn and self.conn.is_open():
            self.conn.close()
        super().closeEvent(event)


def run_gui():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()