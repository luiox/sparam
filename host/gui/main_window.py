import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sparam import (
    DataType,
    Device,
    DeviceManager,
    ElfParser,
    MonitorState,
    MonitorStore,
    SamplePoint,
    SerialConnection,
    Variable,
)

from .styles.catppuccin import SERIES_COLORS
from .widgets.log_panel import LogPanel
from .widgets.sidebar import Sidebar
from .widgets.toolbar import Toolbar
from .widgets.value_card import ValueCard
from .widgets.waveform_plot import WaveformPlot


class DeviceBridge(QObject):
    sample_received = Signal(str, float, float)

    def emit_sample(self, sample: SamplePoint) -> None:
        self.sample_received.emit(sample.name, sample.timestamp, sample.value)


class MainWindow(QMainWindow):
    DTYPE_OPTIONS = {
        "uint8": DataType.UINT8,
        "int8": DataType.INT8,
        "uint16": DataType.UINT16,
        "int16": DataType.INT16,
        "uint32": DataType.UINT32,
        "int32": DataType.INT32,
        "float": DataType.FLOAT,
    }
    DTYPE_TYPE_HINTS = {
        "uint8_t": "uint8",
        "unsigned char": "uint8",
        "int8_t": "int8",
        "signed char": "int8",
        "uint16_t": "uint16",
        "unsigned short": "uint16",
        "int16_t": "int16",
        "short": "int16",
        "uint32_t": "uint32",
        "unsigned int": "uint32",
        "int32_t": "int32",
        "int": "int32",
        "float": "float",
    }
    DTYPE_SUBSTRING_HINTS = (
        ("uint8", "uint8"),
        ("int8", "int8"),
        ("uint16", "uint16"),
        ("int16", "int16"),
        ("uint32", "uint32"),
        ("int32", "int32"),
        ("float", "float"),
    )

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
    SETTINGS_ORG = "luiox"
    SETTINGS_APP = "sparam-gui"
    SETTINGS_GEOMETRY_KEY = "window/geometry"
    SETTINGS_STATE_KEY = "window/state"
    SETTINGS_LAYOUT_VERSION_KEY = "window/layout_version"
    SETTINGS_STATE_VERSION = 3

    def __init__(self, settings: Optional[QSettings] = None) -> None:
        super().__init__()
        self.setWindowTitle("sparam")
        self.resize(1360, 860)
        # Keep a conservative explicit minimum size so dock minimum hints do not
        # force the top-level window beyond the available monitor area.
        self.setMinimumSize(960, 620)

        self.parser = ElfParser()
        self.current_symbol_path: Optional[str] = None
        self.conn: Optional[SerialConnection] = None
        self.device: Optional[Device] = None
        self.device_manager: Optional[DeviceManager] = None
        self.bridge: Optional[DeviceBridge] = None
        self.store = MonitorStore(max_points=1200)
        self.monitor_state = MonitorState()
        self.cards: Dict[str, ValueCard] = {}
        self.connection_fields: Dict[str, QLabel] = {}
        self.monitor_fields: Dict[str, QLabel] = {}
        self.settings = settings or QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)
        self.restart_monitor_timer = QTimer(self)
        self.restart_monitor_timer.setSingleShot(True)
        self.restart_monitor_timer.timeout.connect(self._restart_monitoring_if_needed)

        self._build_ui()
        self._restore_window_layout()
        self._refresh_ports()

    @property
    def monitored_names(self) -> List[str]:
        # Keep compatibility for tests and existing callers.
        return self.monitor_state.monitored_names

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("workspaceShell")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.toolbar = Toolbar()
        self.sidebar = Sidebar()
        self.sidebar.refresh_requested.connect(self._refresh_ports)
        self.sidebar.connect_requested.connect(self._toggle_connection)
        self.sidebar.load_symbols_requested.connect(self._browse_symbols)
        self.sidebar.pause_requested.connect(self._toggle_pause)
        self.sidebar.read_once_requested.connect(self._read_once_variable)
        self.sidebar.write_once_requested.connect(self._write_once_variable)
        self.sidebar.export_png_requested.connect(self._export_png)
        self.sidebar.export_csv_requested.connect(self._export_csv)
        self.sidebar.window_changed.connect(self._set_time_window)
        self.sidebar.rate_changed.connect(self._handle_rate_change)
        self.sidebar.variable_activated.connect(self._add_variable_monitor)
        self.sidebar.variable_remove_requested.connect(self._remove_variable_monitor)
        self.sidebar.selection_changed.connect(self._preview_variable)

        center_column = QWidget()
        center_layout = QVBoxLayout(center_column)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)

        self.waveform = WaveformPlot()
        center_layout.addWidget(self.waveform, 1)

        self.stats_strip = QFrame()
        self.stats_strip.setObjectName("signalStatsStrip")
        cards_layout = QVBoxLayout(self.stats_strip)
        cards_layout.setContentsMargins(8, 8, 8, 8)
        cards_layout.setSpacing(6)

        stats_title_row = QHBoxLayout()
        stats_title_row.setContentsMargins(0, 0, 0, 0)
        stats_title = QLabel("Pinned Signals")
        stats_title.setProperty("sectionTitle", True)
        stats_caption = QLabel("Live sample snapshot from the active monitor stream")
        stats_caption.setProperty("muted", True)
        stats_title_row.addWidget(stats_title)
        stats_title_row.addStretch(1)
        stats_title_row.addWidget(stats_caption)
        cards_layout.addLayout(stats_title_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_contents = QWidget()
        self.cards_layout = QHBoxLayout(scroll_contents)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch(1)
        scroll.setWidget(scroll_contents)
        cards_layout.addWidget(scroll)
        center_layout.addWidget(self.stats_strip)

        layout.addWidget(self.toolbar)
        layout.addWidget(center_column, 1)

        self._setup_docks()
        self._refresh_summary_cards()

    def _setup_docks(self) -> None:
        self.setDockNestingEnabled(True)

        self.sidebar_control_dock = QDockWidget("Transport & Monitor", self)
        self.sidebar_control_dock.setObjectName("sidebarControlDock")
        self.sidebar_control_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.sidebar_control_dock.setWidget(self.sidebar.control_panel_widget())

        self.sidebar_rw_dock = QDockWidget("Single Read/Write", self)
        self.sidebar_rw_dock.setObjectName("sidebarRwDock")
        self.sidebar_rw_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.sidebar_rw_dock.setWidget(self.sidebar.io_panel_widget())

        self.sidebar_variables_dock = QDockWidget("Variables", self)
        self.sidebar_variables_dock.setObjectName("sidebarVariablesDock")
        self.sidebar_variables_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.sidebar_variables_dock.setWidget(self.sidebar.variable_panel_widget())

        self.inspector = self._build_inspector_panel()
        self.inspector_dock = QDockWidget("Inspector", self)
        self.inspector_dock.setObjectName("inspectorDock")
        self.inspector_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.inspector_dock.setWidget(self.inspector)

        # Keep this alias for compatibility with existing callers/tests.
        self.sidebar_dock = self.sidebar_control_dock

        self._apply_default_dock_layout()

    def _apply_default_dock_layout(self) -> None:
        self.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea,
            self.sidebar_control_dock,
        )
        self.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea,
            self.sidebar_rw_dock,
        )
        self.splitDockWidget(
            self.sidebar_control_dock,
            self.sidebar_rw_dock,
            Qt.Orientation.Vertical,
        )
        self.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea,
            self.sidebar_variables_dock,
        )
        self.splitDockWidget(
            self.sidebar_rw_dock,
            self.sidebar_variables_dock,
            Qt.Orientation.Vertical,
        )

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.inspector_dock)

        # Default split: compact 260px left rail and flexible center/right area.
        self.resizeDocks(
            [self.sidebar_control_dock, self.inspector_dock],
            [260, 340],
            Qt.Orientation.Horizontal,
        )
        self.resizeDocks(
            [
                self.sidebar_control_dock,
                self.sidebar_rw_dock,
                self.sidebar_variables_dock,
            ],
            [220, 170, 360],
            Qt.Orientation.Vertical,
        )

    def _build_inspector_panel(self) -> QFrame:
        inspector = QFrame()
        inspector.setObjectName("inspectorPanel")
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(8, 8, 8, 8)
        inspector_layout.setSpacing(8)

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

        self.log_panel = LogPanel()

        inspector_layout.addWidget(connection_card)
        inspector_layout.addWidget(monitor_card)
        inspector_layout.addWidget(self.log_panel, 1)
        return inspector

    def _restore_window_layout(self) -> None:
        geometry = self.settings.value(self.SETTINGS_GEOMETRY_KEY)
        state = self.settings.value(self.SETTINGS_STATE_KEY)
        saved_version = self.settings.value(self.SETTINGS_LAYOUT_VERSION_KEY)
        try:
            layout_version = int(saved_version)
        except (TypeError, ValueError):
            layout_version = 0

        restored = False
        if layout_version == self.SETTINGS_STATE_VERSION:
            if geometry is not None:
                self.restoreGeometry(geometry)
            if state is not None:
                restored = self.restoreState(state, self.SETTINGS_STATE_VERSION)
        if not restored:
            self._apply_default_dock_layout()
        self._clamp_to_available_screen()

    def _clamp_to_available_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        if available.width() <= 0 or available.height() <= 0:
            return

        max_width = max(640, available.width())
        max_height = max(480, available.height())
        clamped_width = min(self.width(), max_width)
        clamped_height = min(self.height(), max_height)
        if clamped_width != self.width() or clamped_height != self.height():
            self.resize(clamped_width, clamped_height)

        max_x = max(available.left(), available.right() - self.width() + 1)
        max_y = max(available.top(), available.bottom() - self.height() + 1)
        clamped_x = min(max(self.x(), available.left()), max_x)
        clamped_y = min(max(self.y(), available.top()), max_y)
        if clamped_x != self.x() or clamped_y != self.y():
            self.move(clamped_x, clamped_y)

    def _notify_runtime_warning(self, title: str, detail: str) -> None:
        full = f"{title}: {detail}"
        brief = full if len(full) <= 110 else f"{full[:107]}..."
        self.toolbar.set_status_text(brief)
        self._log(full)

    def _save_window_layout(self) -> None:
        self.settings.setValue(self.SETTINGS_GEOMETRY_KEY, self.saveGeometry())
        self.settings.setValue(
            self.SETTINGS_STATE_KEY,
            self.saveState(self.SETTINGS_STATE_VERSION),
        )
        self.settings.setValue(
            self.SETTINGS_LAYOUT_VERSION_KEY,
            self.SETTINGS_STATE_VERSION,
        )

    def _create_summary_card(
        self, title: str, subtitle: str, field_names: List[str]
    ) -> Tuple[QFrame, Dict[str, QLabel]]:
        card = QFrame()
        card.setObjectName("summaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

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
            value.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            row.addWidget(key)
            row.addWidget(value, 1)
            layout.addLayout(row)
            fields[name] = value

        layout.addStretch(1)
        return card, fields

    def _log(self, message: str) -> None:
        self.log_panel.append_line(message)

    def _refresh_ports(self) -> None:
        ports = SerialConnection.list_ports()
        self.sidebar.set_ports(ports)
        if not ports:
            self._log("No serial ports found.")
        self._refresh_summary_cards()

    def _browse_symbols(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open ELF or MAP",
            str(Path.cwd()),
            "ELF/MAP Files (*.elf *.out *.map);;All Files (*)",
        )
        if path:
            self._load_symbols(path)

    def _load_symbols(self, filepath: str) -> None:
        try:
            variables = self.parser.parse(filepath)
        except Exception as exc:
            QMessageBox.critical(self, "Load Symbols", f"Failed to parse file: {exc}")
            return

        self.current_symbol_path = filepath
        self.sidebar.set_variables(variables)
        self._log(f"Loaded {len(variables)} variables from {Path(filepath).name}.")
        self._refresh_summary_cards()

    def _toggle_connection(self) -> None:
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
            QMessageBox.warning(
                self, "Connection", "Ping failed. Check device id and cable."
            )
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
        self._schedule_monitor_restart()

    def _disconnect_device(self) -> None:
        self.restart_monitor_timer.stop()
        if self.device_manager:
            self.device_manager.stop_monitor()
        if self.conn and self.conn.is_open():
            self.conn.close()
        self.conn = None
        self.device = None
        self.device_manager = None
        self.bridge = None
        self.monitor_state.reset()
        self.toolbar.set_connected(False)
        self.sidebar.set_connected(False)
        self._log("Disconnected.")
        self._refresh_summary_cards()

    def _preview_variable(self, name: str) -> None:
        variable = self.parser.get_variable(name)
        if not variable:
            return
        self._sync_dtype_with_variable(variable)
        self.toolbar.set_status_text(
            f"{variable.name}  0x{variable.address:08X}  {variable.var_type}"
        )

    def _sync_dtype_with_variable(self, variable: Variable) -> None:
        label = self._dtype_label_for_variable(variable)
        if label:
            self.sidebar.set_dtype_label(label)

    def _dtype_label_for_variable(self, variable: Variable) -> Optional[str]:
        normalized = variable.var_type.strip().lower()
        exact = self.DTYPE_TYPE_HINTS.get(normalized)
        if exact:
            return exact

        for token, label in self.DTYPE_SUBSTRING_HINTS:
            if token in normalized:
                return label

        try:
            dtype = DataType(variable.dtype_code)
        except ValueError:
            return None

        for label, option in self.DTYPE_OPTIONS.items():
            if option == dtype:
                return label
        return None

    def _add_variable_monitor(self, name: str) -> None:
        variable = self.parser.get_variable(name)
        if not variable:
            return

        if not self.monitor_state.add_monitored(name):
            return

        color = self._series_color_for(name)
        self.sidebar.set_monitored(name, True)
        self.waveform.add_variable(name, color)
        self._ensure_card(name, color)
        self._log(f"Added {name} to monitor.")
        self._refresh_summary_cards()
        self._schedule_monitor_restart()

    def _remove_variable_monitor(self, name: str) -> None:
        if not self.monitor_state.remove_monitored(name):
            return

        self.sidebar.set_monitored(name, False)
        self.waveform.remove_variable(name)
        self._remove_card(name)
        self._log(f"Removed {name} from monitor.")
        self._refresh_summary_cards()
        self._schedule_monitor_restart()

    def _toggle_variable_monitor(self, name: str) -> None:
        if name in self.monitor_state.monitored_names:
            self._remove_variable_monitor(name)
        else:
            self._add_variable_monitor(name)

    def _series_color_for(self, name: str) -> str:
        index = self.monitor_state.series_index(name)
        return SERIES_COLORS[index % len(SERIES_COLORS)]

    def _ensure_card(self, name: str, color: str) -> None:
        if name in self.cards:
            return
        card = ValueCard(name, color)
        self.cards[name] = card
        self.cards_layout.insertWidget(max(0, self.cards_layout.count() - 1), card)

    def _remove_card(self, name: str) -> None:
        card = self.cards.pop(name, None)
        if card is None:
            return
        card.setParent(None)
        card.deleteLater()

    def _toggle_pause(self) -> None:
        paused = self.monitor_state.toggle_paused()
        self.waveform.set_paused(paused)
        self.toolbar.set_paused(paused)
        self.sidebar.set_paused(paused)
        self._log("Monitor paused." if paused else "Monitor resumed.")
        self._refresh_summary_cards()

    def _set_time_window(self, label: str) -> None:
        self.waveform.set_time_window(self.WINDOW_OPTIONS[label])
        self._refresh_summary_cards()

    def _handle_rate_change(self, _label: str) -> None:
        self._refresh_summary_cards()
        self._schedule_monitor_restart()

    def _schedule_monitor_restart(self) -> None:
        # Debounce rapid UI actions (e.g., fast variable double-clicks) to avoid
        # repeated stop/start monitor churn on the transport layer.
        self.restart_monitor_timer.start(80)

    def _current_dtype(self) -> DataType:
        return self.DTYPE_OPTIONS.get(
            self.sidebar.current_dtype_label(),
            DataType.FLOAT,
        )

    def _selected_variable(self) -> Optional[Variable]:
        name = self.sidebar.current_variable_name()
        if not name:
            return None
        return self.parser.get_variable(name)

    def _pause_stream_for_single_io(self) -> bool:
        was_streaming = bool(self.device_manager and self.monitor_state.active)
        if was_streaming and self.device_manager:
            self.device_manager.stop_monitor()
            self.monitor_state.stop_streaming()
            self._refresh_summary_cards()
        return was_streaming

    def _resume_stream_after_single_io(self, was_streaming: bool) -> None:
        if was_streaming:
            self._schedule_monitor_restart()

    def _read_once_variable(self) -> None:
        variable = self._selected_variable()
        if not variable:
            QMessageBox.warning(self, "Read Once", "Please select a variable first.")
            return
        if not self.device:
            QMessageBox.warning(self, "Read Once", "No active device connection.")
            return

        was_streaming = self._pause_stream_for_single_io()
        try:
            value_bytes = self.device.read_value(variable, timeout=1.0)
        except Exception as exc:
            self._resume_stream_after_single_io(was_streaming)
            self._notify_runtime_warning(
                "Read Once",
                f"{variable.name} failed ({exc})",
            )
            return
        self._resume_stream_after_single_io(was_streaming)

        if value_bytes is None:
            error_reason = self.device.last_error or "unknown error"
            self._notify_runtime_warning(
                "Read Once",
                f"{variable.name} failed ({error_reason})",
            )
            return

        try:
            if variable.dtype_code:
                dtype = DataType(variable.dtype_code)
            else:
                dtype = self._current_dtype()
            value = Device.bytes_to_value(value_bytes[: dtype.size], dtype)
            if dtype == DataType.FLOAT:
                shown = f"{float(value):.6g}"
            else:
                shown = str(int(value))
        except Exception:
            shown = value_bytes.hex()

        self.sidebar.set_rw_value(shown)
        self._log(f"READ {variable.name} = {shown}")

    def _write_once_variable(self) -> None:
        variable = self._selected_variable()
        if not variable:
            QMessageBox.warning(self, "Write Once", "Please select a variable first.")
            return
        if not self.device:
            QMessageBox.warning(self, "Write Once", "No active device connection.")
            return

        raw_text = self.sidebar.current_write_value()
        if not raw_text:
            QMessageBox.warning(self, "Write Once", "Please input a value.")
            return

        dtype = self._current_dtype()
        try:
            if dtype == DataType.FLOAT:
                typed_value = float(raw_text)
            else:
                typed_value = int(raw_text, 0)
            value_bytes = Device.value_to_bytes(typed_value, dtype)
        except Exception as exc:
            self._log(f"WRITE FAIL {variable.name}: invalid value {raw_text} ({exc})")
            QMessageBox.warning(self, "Write Once", f"Invalid value: {exc}")
            return

        was_streaming = self._pause_stream_for_single_io()
        try:
            ok = self.device.write_single(
                variable,
                value_bytes,
                timeout=1.0,
                dtype_override=dtype,
            )
        except Exception as exc:
            self._resume_stream_after_single_io(was_streaming)
            self._notify_runtime_warning(
                "Write Once",
                f"{variable.name} failed ({exc})",
            )
            return
        self._resume_stream_after_single_io(was_streaming)

        if not ok:
            error_reason = self.device.last_error or "unknown error"
            self._notify_runtime_warning(
                "Write Once",
                f"{variable.name} failed ({error_reason})",
            )
            return

        self._log(f"WRITE {variable.name} <= {raw_text} ({dtype.name})")

    def _restart_monitoring_if_needed(self) -> None:
        if not self.device_manager or not self.monitor_state.monitored_names:
            if self.device_manager:
                self.device_manager.stop_monitor()
            self.monitor_state.stop_streaming()
            self._refresh_summary_cards()
            return

        variables = []
        for name in self.monitor_state.monitored_names:
            variable = self.parser.get_variable(name)
            if variable is not None:
                variables.append(variable)
        if not variables:
            return

        self.device_manager.stop_monitor()
        monitor_active = self.device_manager.start_monitor(
            variables,
            self.RATE_OPTIONS[self.sidebar.current_rate_label()],
        )
        self.monitor_state.set_active(monitor_active)
        if monitor_active:
            self._log(
                "Streaming "
                f"{len(variables)} variable(s) at "
                f"{self.sidebar.current_rate_label()}."
            )
        elif self.device:
            self._log(f"MONITOR FAIL: {self.device.last_error or 'unknown error'}")
        self._refresh_summary_cards()

    def _on_sample_received(self, name: str, timestamp: float, value: float) -> None:
        if self.monitor_state.paused:
            return
        self.store.append(name, timestamp, value)
        card = self.cards.get(name)
        if card:
            card.update_value(value)
        self.waveform.update_data(name, timestamp, value)
        self._refresh_summary_cards()

    def _export_png(self) -> None:
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

    def _export_csv(self) -> None:
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

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.restart_monitor_timer.stop()
        self._save_window_layout()
        if self.device_manager:
            self.device_manager.stop_monitor()
        if self.conn and self.conn.is_open():
            self.conn.close()
        super().closeEvent(event)

    def _refresh_summary_cards(self) -> None:
        self.connection_fields["Port"].setText(
            self.sidebar.current_port() or "Not selected"
        )
        self.connection_fields["Baud"].setText(str(self.sidebar.current_baudrate()))
        self.connection_fields["Device"].setText(str(self.sidebar.current_device_id()))
        self.connection_fields["Symbols"].setText(
            Path(self.current_symbol_path).name if self.current_symbol_path else "None"
        )

        self.monitor_fields["Variables"].setText(
            str(len(self.monitor_state.monitored_names))
        )
        self.monitor_fields["Rate"].setText(self.sidebar.current_rate_label())
        self.monitor_fields["Window"].setText(self.sidebar.window_combo.currentText())
        if self.monitor_state.paused:
            mode = "Paused"
        elif self.monitor_state.active:
            mode = "Streaming"
        elif self.device:
            mode = "Armed"
        else:
            mode = "Offline"
        self.monitor_fields["Mode"].setText(mode)
