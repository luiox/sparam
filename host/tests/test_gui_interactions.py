import importlib.util
import struct
import sys
from pathlib import Path
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


def _require_gui_stack() -> None:
    if importlib.util.find_spec("PySide6") is None:
        raise SkipTest("PySide6 is not installed")
    if importlib.util.find_spec("pyqtgraph") is None:
        raise SkipTest("pyqtgraph is not installed")


def test_main_window_handles_rapid_variable_events_without_duplicates() -> None:
    _require_gui_stack()

    from PySide6.QtWidgets import QApplication

    from gui.main_window import MainWindow
    from sparam.elf_parser import Variable

    app = QApplication.instance() or QApplication([])
    window = MainWindow()

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

    from PySide6.QtWidgets import QApplication

    from gui.main_window import MainWindow
    from sparam import DataType, Device
    from sparam.elf_parser import Variable

    app = QApplication.instance() or QApplication([])
    window = MainWindow()

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
