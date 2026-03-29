import struct
from typing import Optional

from gui.controllers.io_controller import IOController
from sparam import DataType
from sparam.elf_parser import Variable


class _FakeReadDevice:
    def __init__(self, value: Optional[bytes], error: str = "") -> None:
        self.value = value
        self.last_error = error

    def read_value(self, variable: Variable, timeout: float = 1.0) -> Optional[bytes]:
        _ = variable
        _ = timeout
        return self.value


class _FakeWriteDevice:
    def __init__(self, ok: bool, error: str = "") -> None:
        self.ok = ok
        self.last_error = error
        self.calls = []

    def write_single(
        self,
        variable: Variable,
        value_bytes: bytes,
        timeout: float = 1.0,
        dtype_override: Optional[DataType] = None,
    ) -> bool:
        self.calls.append((variable, value_bytes, timeout, dtype_override))
        return self.ok


def test_io_controller_read_once_decodes_integer_values() -> None:
    variable = Variable("speed", 0x20000000, 4, "uint32_t")
    device = _FakeReadDevice(struct.pack("<I", 42))

    result = IOController().read_once(device, variable, DataType.FLOAT)

    assert result.ok is True
    assert result.value_text == "42"


def test_io_controller_read_once_reports_device_error() -> None:
    variable = Variable("speed", 0x20000000, 4, "uint32_t")
    device = _FakeReadDevice(None, "timeout")

    result = IOController().read_once(device, variable, DataType.FLOAT)

    assert result.ok is False
    assert "timeout" in result.error


def test_io_controller_write_once_handles_invalid_value() -> None:
    variable = Variable("speed", 0x20000000, 4, "uint32_t")
    device = _FakeWriteDevice(ok=True)

    result = IOController().write_once(device, variable, "abc", DataType.UINT32)

    assert result.ok is False
    assert result.error.startswith("Invalid value:")


def test_io_controller_write_once_passes_dtype_and_payload() -> None:
    variable = Variable("speed", 0x20000000, 4, "uint32_t")
    device = _FakeWriteDevice(ok=True)

    result = IOController().write_once(device, variable, "0x2A", DataType.UINT32)

    assert result.ok is True
    assert len(device.calls) == 1
    _var, value_bytes, _timeout, dtype = device.calls[0]
    assert value_bytes == struct.pack("<I", 42)
    assert dtype == DataType.UINT32


def test_io_controller_write_once_returns_device_failure() -> None:
    variable = Variable("speed", 0x20000000, 4, "uint32_t")
    device = _FakeWriteDevice(ok=False, error="nack")

    result = IOController().write_once(device, variable, "12", DataType.UINT32)

    assert result.ok is False
    assert "nack" in result.error
