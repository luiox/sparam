import importlib.util
import struct
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, List, Optional, Tuple, cast
from unittest import SkipTest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _FakeDevice:
    def __init__(self) -> None:
        self.last_error = ""
        self.write_calls: List[Tuple[Any, bytes, float, Optional[Any]]] = []

    def write_single(
        self,
        variable: Any,
        value_bytes: bytes,
        timeout: float = 1.0,
        dtype_override: Optional[Any] = None,
    ) -> bool:
        self.write_calls.append((variable, value_bytes, timeout, dtype_override))
        return True


class _RaisingDevice:
    def __init__(self) -> None:
        self.last_error = ""

    def write_single(
        self,
        variable: Any,
        value_bytes: bytes,
        timeout: float = 1.0,
        dtype_override: Optional[Any] = None,
    ) -> bool:
        raise RuntimeError("mock transport write failure")


def _require_gui_stack() -> None:
    if importlib.util.find_spec("PySide6") is None:
        raise SkipTest("PySide6 is not installed")
    if importlib.util.find_spec("pyqtgraph") is None:
        raise SkipTest("pyqtgraph is not installed")


def test_main_window_handles_rapid_variable_events_without_duplicates() -> None:
    _require_gui_stack()

    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from gui.main_window import MainWindow
    from sparam.elf_parser import Variable

    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as temp_dir:
        settings = QSettings(
            str(Path(temp_dir) / "rapid-events.ini"),
            QSettings.Format.IniFormat,
        )
        settings.clear()
        window = MainWindow(settings=settings)

        variable = Variable("motor_speed", 0x20000000, 4, "uint32_t")
        window.parser.variables = {variable.name: variable}
        window.sidebar.set_variables([variable])

        for _ in range(120):
            window.sidebar.variable_activated.emit(variable.name)
            app.processEvents()

        assert window.monitored_names == [variable.name]

        for _ in range(120):
            window.sidebar.variable_remove_requested.emit(variable.name)
            app.processEvents()

        assert window.monitored_names == []

        window.close()
    app.quit()


def test_write_once_uses_integer_parsing_for_uint32() -> None:
    _require_gui_stack()

    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from gui.main_window import MainWindow
    from sparam import DataType, Device
    from sparam.elf_parser import Variable

    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as temp_dir:
        settings = QSettings(
            str(Path(temp_dir) / "write-once.ini"),
            QSettings.Format.IniFormat,
        )
        settings.clear()
        window = MainWindow(settings=settings)

        variable = Variable("motor_speed", 0x20000000, 4, "uint32_t")
        window.parser.variables = {variable.name: variable}
        window.sidebar.set_variables([variable])
        window.sidebar.list_widget.setCurrentRow(0)
        window.sidebar.dtype_combo.setCurrentText("uint32")
        window.sidebar.set_rw_value("0x2A")

        fake_device = _FakeDevice()
        window.device = cast(Device, fake_device)

        window._write_once_variable()

        assert len(fake_device.write_calls) == 1
        _, value_bytes, _, dtype = fake_device.write_calls[0]
        assert value_bytes == struct.pack("<I", 42)
        assert dtype == DataType.UINT32

        window.close()
    app.quit()


def test_variable_selection_auto_syncs_rw_dtype() -> None:
    _require_gui_stack()

    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from gui.main_window import MainWindow
    from sparam.elf_parser import Variable

    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as temp_dir:
        settings = QSettings(
            str(Path(temp_dir) / "dtype-sync.ini"),
            QSettings.Format.IniFormat,
        )
        settings.clear()
        window = MainWindow(settings=settings)

        variable = Variable("torque_target", 0x20000010, 2, "int16_t")
        window.parser.variables = {variable.name: variable}
        window.sidebar.set_variables([variable])
        window.sidebar.dtype_combo.setCurrentText("float")

        window._preview_variable(variable.name)

        assert window.sidebar.current_dtype_label() == "int16"

        window.close()
    app.quit()


def test_write_once_handles_device_exception_without_crash() -> None:
    _require_gui_stack()

    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from gui.main_window import MainWindow
    from sparam import Device
    from sparam.elf_parser import Variable

    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as temp_dir:
        settings = QSettings(
            str(Path(temp_dir) / "write-exception.ini"),
            QSettings.Format.IniFormat,
        )
        settings.clear()
        window = MainWindow(settings=settings)

        variable = Variable("motor_speed", 0x20000000, 4, "uint32_t")
        window.parser.variables = {variable.name: variable}
        window.sidebar.set_variables([variable])
        window.sidebar.list_widget.setCurrentRow(0)
        window.sidebar.dtype_combo.setCurrentText("uint32")
        window.sidebar.set_rw_value("32")
        window.device = cast(Device, _RaisingDevice())

        window._write_once_variable()

        window.close()
    app.quit()


def test_sidebar_toggle_all_sections_round_trip() -> None:
    _require_gui_stack()

    from PySide6.QtWidgets import QApplication

    from gui.widgets.sidebar import Sidebar

    app = QApplication.instance() or QApplication([])

    sidebar = Sidebar()
    assert sidebar.all_sections_expanded()
    assert sidebar.toggle_all_btn.text() == "Collapse All"

    sidebar.toggle_all_sections()
    assert not sidebar.all_sections_expanded()
    assert sidebar.toggle_all_btn.text() == "Expand All"

    sidebar.toggle_all_sections()
    assert sidebar.all_sections_expanded()
    assert sidebar.toggle_all_btn.text() == "Collapse All"

    sidebar.deleteLater()
    app.quit()
