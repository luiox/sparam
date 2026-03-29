from dataclasses import dataclass
from typing import Optional, Protocol

from sparam import DataType, Device, Variable


class ReadDevice(Protocol):
    @property
    def last_error(self) -> str:
        ...

    def read_value(self, variable: Variable, timeout: float = 1.0) -> Optional[bytes]:
        ...


class WriteDevice(Protocol):
    @property
    def last_error(self) -> str:
        ...

    def write_single(
        self,
        variable: Variable,
        value_bytes: bytes,
        timeout: float = 1.0,
        dtype_override: Optional[DataType] = None,
    ) -> bool:
        ...


@dataclass
class IOResult:
    ok: bool
    value_text: str = ""
    error: str = ""
    error_type: str = ""
    value_text_fallback: bool = False


class IOController:
    def read_once(
        self,
        device: ReadDevice,
        variable: Variable,
        fallback_dtype: DataType,
        timeout: float = 1.0,
    ) -> IOResult:
        try:
            value_bytes = device.read_value(variable, timeout=timeout)
        except Exception as exc:
            return IOResult(
                ok=False,
                error=f"{variable.name} failed ({exc})",
                error_type="device_error",
            )

        if value_bytes is None:
            error_reason = device.last_error or "unknown error"
            return IOResult(
                ok=False,
                error=f"{variable.name} failed ({error_reason})",
                error_type="device_error",
            )

        try:
            dtype = (
                DataType(variable.dtype_code)
                if variable.dtype_code
                else fallback_dtype
            )
            value = Device.bytes_to_value(value_bytes[: dtype.size], dtype)
            if dtype == DataType.FLOAT:
                shown = f"{float(value):.6g}"
            else:
                shown = str(int(value))
            return IOResult(ok=True, value_text=shown)
        except Exception:
            # Fall back to raw bytes text so one-shot read remains usable.
            return IOResult(
                ok=True,
                value_text=value_bytes.hex(),
                value_text_fallback=True,
            )

    def write_once(
        self,
        device: WriteDevice,
        variable: Variable,
        raw_text: str,
        dtype: DataType,
        timeout: float = 1.0,
    ) -> IOResult:
        try:
            typed_value = (
                float(raw_text) if dtype == DataType.FLOAT else int(raw_text, 0)
            )
            value_bytes = Device.value_to_bytes(typed_value, dtype)
        except Exception as exc:
            return IOResult(
                ok=False,
                error=f"Invalid value: {exc}",
                error_type="invalid_input",
            )

        try:
            ok = device.write_single(
                variable,
                value_bytes,
                timeout=timeout,
                dtype_override=dtype,
            )
        except Exception as exc:
            return IOResult(
                ok=False,
                error=f"{variable.name} failed ({exc})",
                error_type="device_error",
            )

        if not ok:
            error_reason = device.last_error or "unknown error"
            return IOResult(
                ok=False,
                error=f"{variable.name} failed ({error_reason})",
                error_type="device_error",
            )

        return IOResult(ok=True)
