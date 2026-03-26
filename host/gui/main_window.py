import csv
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from sparam import DataType, Device, DeviceManager, ElfParser, MonitorStore, SerialConnection

from .styles.catppuccin import SERIES_COLORS
from .widgets.log_panel import LogPanel
from .widgets.sidebar import Sidebar
from .widgets.toolbar import Toolbar
from .widgets.value_card import ValueCard
from .widgets.waveform_plot import WaveformPlot


class DeviceBridge(QObject):
    sample_received = Signal(str, float, float)

    def emit_sample(self, sample):
        self.sample_received.emit(sample.name, sample.timestamp, sample.value)


class MainWindow(QMainWindow):
    RATE_OPTIONS = {
        "1 ms": 1,
        "5 ms": 2,
        "10 ms": 3,
        "20 ms": 4,
        "50 ms": 5,
        "100 ms": 6,
        "200 ms": 7,
        "500 ms": 8,
    }
    WINDOW_OPTIONS = {
        "5 s": 5.0,
        "10 s": 10.0,
        "30 s": 30.0,
        "Infinite": None,
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("sparam")
        self.resize(1360, 860)

        self.parser = ElfParser()
        self.current_symbol_path: Optional[str] = None
        self.conn: Optional[SerialConnection] = None
        self.device: Optional[Device] = None
        self.device_manager: Optional[DeviceManager] = None
        self.bridge: Optional[DeviceBridge] = None
        self.store = MonitorStore(max_points=1200)
        self.monitored_names: List[str] = []
        self.cards: Dict[str, ValueCard] = {}
        self.monitor_active = False
        self.monitor_paused = False
        self.connection_fields: Dict[str, QLabel] = {}
        self.monitor_fields: Dict[str, QLabel] = {}

        self._build_ui()
        self._refresh_ports()

    def _build_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        self.toolbar = Toolbar()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.sidebar = Sidebar()
        self.sidebar.refresh_requested.connect(self._refresh_ports)
        self.sidebar.connect_requested.connect(self._toggle_connection)
        self.sidebar.load_symbols_requested.connect(self._browse_symbols)
        self.sidebar.pause_requested.connect(self._toggle_pause)
        self.sidebar.export_png_requested.connect(self._export_png)
        self.sidebar.export_csv_requested.connect(self._export_csv)
        self.sidebar.window_changed.connect(self._set_time_window)
        self.sidebar.rate_changed.connect(self._handle_rate_change)
        self.sidebar.variable_activated.connect(self._toggle_variable_monitor)
        self.sidebar.selection_changed.connect(self._preview_variable)

        main_panel = QWidget()
        main_layout = QGridLayout(main_panel)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setHorizontalSpacing(14)
        main_layout.setVerticalSpacing(14)

        self.waveform = WaveformPlot()
        connection_card, self.connection_fields = self._create_summary_card(
            "Connection Overview",
            "Current transport and symbol source",
            ["Port", "Baud", "Device", "Symbols"],
        )
        monitor_card, self.monitor_fields = self._create_summary_card(
            "Monitor Session",
            "Live sampling session information",
            ["Variables", "Rate", "Window", "Mode"],
        )

        cards_shell = QFrame()
        cards_shell.setObjectName("cardShelf")
        cards_layout = QVBoxLayout(cards_shell)
        cards_layout.setContentsMargins(12, 12, 12, 12)
        cards_layout.setSpacing(10)
        cards_title = QLabel("Live Values")
        cards_title.setProperty("muted", True)
        cards_layout.addWidget(cards_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_contents = QWidget()
        self.cards_layout = QHBoxLayout(scroll_contents)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch(1)
        scroll.setWidget(scroll_contents)
        cards_layout.addWidget(scroll)

        self.log_panel = LogPanel()

        main_layout.addWidget(self.waveform, 0, 0, 2, 2)
        main_layout.addWidget(connection_card, 0, 2)
        main_layout.addWidget(monitor_card, 1, 2)
        main_layout.addWidget(cards_shell, 2, 0, 1, 2)
        main_layout.addWidget(self.log_panel, 2, 2)
        main_layout.setColumnStretch(0, 3)
        main_layout.setColumnStretch(1, 2)
        main_layout.setColumnStretch(2, 2)
        main_layout.setRowStretch(0, 4)
        main_layout.setRowStretch(1, 3)
        main_layout.setRowStretch(2, 2)

        splitter.addWidget(self.sidebar)
        splitter.addWidget(main_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        layout.addWidget(self.toolbar)
        layout.addWidget(splitter, 1)
        self._refresh_summary_cards()

    def _create_summary_card(self, title: str, subtitle: str, field_names: List[str]):
        card = QFrame()
        card.setObjectName("summaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setProperty("sectionTitle", True)
        subtitle_label = QLabel(subtitle)
        subtitle_label.setProperty("muted", True)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        fields: Dict[str, QLabel] = {}
        for name in field_names:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            key = QLabel(name)
            key.setProperty("muted", True)
            value = QLabel("--")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(key)
            row.addWidget(value, 1)
            layout.addLayout(row)
            fields[name] = value

        layout.addStretch(1)
        return card, fields

    def _log(self, message: str):
        self.log_panel.append_line(message)

    def _refresh_ports(self):
        ports = SerialConnection.list_ports()
        self.sidebar.set_ports(ports)
        if not ports:
            self._log("No serial ports found.")
        self._refresh_summary_cards()

    def _browse_symbols(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open ELF or MAP",
            str(Path.cwd()),
            "ELF/MAP Files (*.elf *.out *.map);;All Files (*)",
        )
        if path:
            self._load_symbols(path)

    def _load_symbols(self, filepath: str):
        try:
            variables = self.parser.parse(filepath)
        except Exception as exc:
            QMessageBox.critical(self, "Load Symbols", f"Failed to parse file: {exc}")
            return

        self.current_symbol_path = filepath
        self.sidebar.set_variables(variables)
        self._log(f"Loaded {len(variables)} variables from {Path(filepath).name}.")
        self._refresh_summary_cards()

    def _toggle_connection(self):
        if self.conn and self.conn.is_open():
            self._disconnect_device()
            return

        port = self.sidebar.current_port()
        if not port:
            QMessageBox.warning(self, "Connection", "Please select a serial port.")
            return

        conn = SerialConnection(
            port,
            self.sidebar.current_baudrate(),
            timeout=1.0,
        )
        if not conn.open():
            reason = conn.last_error or "port busy or unavailable"
            self._log(f"CONNECT FAIL: unable to open {port} ({reason})")
            QMessageBox.critical(self, "Connection", f"Failed to open {port}.")
            return

        device = Device(conn, self.sidebar.current_device_id(), elf_parser=self.parser)
        if not device.ping(timeout=1.0):
            conn.close()
            reason = device.last_error or "ping timeout"
            self._log(f"CONNECT FAIL: {reason}")
            QMessageBox.warning(self, "Connection", "Ping failed. Check device id and cable.")
            return

        self.conn = conn
        self.device = device
        self.device_manager = DeviceManager(device)
        self.bridge = DeviceBridge()
        self.device_manager.add_callback(self.bridge.emit_sample)
        self.bridge.sample_received.connect(self._on_sample_received)
        self.toolbar.set_connected(True)
        self.sidebar.set_connected(True)
        self._log(f"Connected to {port} (baud={self.sidebar.current_baudrate()}).")
        self._refresh_summary_cards()
        self._restart_monitoring_if_needed()

    def _disconnect_device(self):
        if self.device_manager:
            self.device_manager.stop_monitor()
        if self.conn and self.conn.is_open():
            self.conn.close()
        self.conn = None
        self.device = None
        self.device_manager = None
        self.bridge = None
        self.monitor_active = False
        self.toolbar.set_connected(False)
        self.sidebar.set_connected(False)
        self._log("Disconnected.")
        self._refresh_summary_cards()

    def _preview_variable(self, name: str):
        variable = self.parser.get_variable(name)
        if not variable:
            return
        self.toolbar.set_status_text(
            f"{variable.name}  0x{variable.address:08X}  {variable.var_type}"
        )

    def _toggle_variable_monitor(self, name: str):
        variable = self.parser.get_variable(name)
        if not variable:
            return

        if name in self.monitored_names:
            self.monitored_names = [item for item in self.monitored_names if item != name]
            self.sidebar.set_monitored(name, False)
            self.waveform.remove_variable(name)
            self._remove_card(name)
            self._log(f"Removed {name} from monitor.")
        else:
            self.monitored_names.append(name)
            color = self._series_color_for(name)
            self.sidebar.set_monitored(name, True)
            self.waveform.add_variable(name, color)
            self._ensure_card(name, color)
            self._log(f"Added {name} to monitor.")

        self._refresh_summary_cards()
        self._restart_monitoring_if_needed()

    def _series_color_for(self, name: str) -> str:
        if name in self.monitored_names:
            index = self.monitored_names.index(name)
        else:
            index = len(self.monitored_names)
        return SERIES_COLORS[index % len(SERIES_COLORS)]

    def _ensure_card(self, name: str, color: str):
        if name in self.cards:
            return
        card = ValueCard(name, color)
        self.cards[name] = card
        self.cards_layout.insertWidget(max(0, self.cards_layout.count() - 1), card)

    def _remove_card(self, name: str):
        card = self.cards.pop(name, None)
        if card is None:
            return
        card.setParent(None)
        card.deleteLater()

    def _toggle_pause(self):
        self.monitor_paused = not self.monitor_paused
        self.waveform.set_paused(self.monitor_paused)
        self.toolbar.set_paused(self.monitor_paused)
        self.sidebar.set_paused(self.monitor_paused)
        self._log("Monitor paused." if self.monitor_paused else "Monitor resumed.")
        self._refresh_summary_cards()

    def _set_time_window(self, label: str):
        self.waveform.set_time_window(self.WINDOW_OPTIONS[label])
        self._refresh_summary_cards()

    def _handle_rate_change(self, _label: str):
        self._refresh_summary_cards()
        self._restart_monitoring_if_needed()

    def _restart_monitoring_if_needed(self):
        if not self.device_manager or not self.monitored_names:
            if self.device_manager:
                self.device_manager.stop_monitor()
            self.monitor_active = False
            self._refresh_summary_cards()
            return

        variables = [
            self.parser.get_variable(name)
            for name in self.monitored_names
            if self.parser.get_variable(name)
        ]
        if not variables:
            return

        self.device_manager.stop_monitor()
        self.monitor_active = self.device_manager.start_monitor(
            variables,
            self.RATE_OPTIONS[self.sidebar.current_rate_label()],
        )
        if self.monitor_active:
            self._log(
                f"Streaming {len(variables)} variable(s) at {self.sidebar.current_rate_label()}."
            )
        elif self.device:
            self._log(f"MONITOR FAIL: {self.device.last_error or 'unknown error'}")
        self._refresh_summary_cards()

    def _on_sample_received(self, name: str, timestamp: float, value: float):
        if self.monitor_paused:
            return
        self.store.append(name, timestamp, value)
        card = self.cards.get(name)
        if card:
            card.update_value(value)
        self.waveform.update_data(name, timestamp, value)
        self._refresh_summary_cards()

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Waveform PNG",
            str(Path.cwd() / "waveform.png"),
            "PNG Files (*.png)",
        )
        if not path:
            return
        try:
            self.waveform.export_png(path)
            self._log(f"Exported waveform PNG to {path}.")
        except Exception as exc:
            QMessageBox.warning(self, "Export PNG", f"Failed to export PNG: {exc}")

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Waveform CSV",
            str(Path.cwd() / "waveform.csv"),
            "CSV Files (*.csv)",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["timestamp", "name", "value"])
                writer.writerows(self.store.export_rows())
            self._log(f"Exported waveform CSV to {path}.")
        except Exception as exc:
            QMessageBox.warning(self, "Export CSV", f"Failed to export CSV: {exc}")

    def closeEvent(self, event):
        if self.device_manager:
            self.device_manager.stop_monitor()
        if self.conn and self.conn.is_open():
            self.conn.close()
        super().closeEvent(event)

    def _refresh_summary_cards(self):
        self.connection_fields["Port"].setText(
            self.sidebar.current_port() or "Not selected"
        )
        self.connection_fields["Baud"].setText(str(self.sidebar.current_baudrate()))
        self.connection_fields["Device"].setText(str(self.sidebar.current_device_id()))
        self.connection_fields["Symbols"].setText(
            Path(self.current_symbol_path).name if self.current_symbol_path else "None"
        )

        self.monitor_fields["Variables"].setText(str(len(self.monitored_names)))
        self.monitor_fields["Rate"].setText(self.sidebar.current_rate_label())
        self.monitor_fields["Window"].setText(self.sidebar.window_combo.currentText())
        if self.monitor_paused:
            mode = "Paused"
        elif self.monitor_active:
            mode = "Streaming"
        elif self.device:
            mode = "Armed"
        else:
            mode = "Offline"
        self.monitor_fields["Mode"].setText(mode)
