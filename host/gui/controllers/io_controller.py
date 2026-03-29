from dataclasses import dataclass

from sparam import DataType, Device, Variable


@dataclass
class IOResult:
    ok: bool
    value_text: str = ""
    error: str = ""


class IOController:
    def read_once(
        self,
        device: Device,
        variable: Variable,
        fallback_dtype: DataType,
        timeout: float = 1.0,
    ) -> IOResult:
        try:
            value_bytes = device.read_value(variable, timeout=timeout)
        except Exception as exc:
            return IOResult(ok=False, error=f"{variable.name} failed ({exc})")

        if value_bytes is None:
            error_reason = device.last_error or "unknown error"
            return IOResult(ok=False, error=f"{variable.name} failed ({error_reason})")

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
            return IOResult(ok=True, value_text=value_bytes.hex())

    def write_once(
        self,
        device: Device,
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
            return IOResult(ok=False, error=f"Invalid value: {exc}")

        try:
            ok = device.write_single(
                variable,
                value_bytes,
                timeout=timeout,
                dtype_override=dtype,
            )
        except Exception as exc:
            return IOResult(ok=False, error=f"{variable.name} failed ({exc})")

        if not ok:
            error_reason = device.last_error or "unknown error"
            return IOResult(ok=False, error=f"{variable.name} failed ({error_reason})")

        return IOResult(ok=True)
