import struct
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .elf_parser import ElfParser, Variable
from .protocol import CommandType, DataType, Frame, Protocol
from .serial_conn import SerialConnection
from .socket_conn import SocketConnection


@dataclass
class MonitoredVar:
    variable: Variable
    rate: int
    last_value: Optional[bytes] = None
    last_update: Optional[float] = None


AcceptFrame = Callable[[Frame], bool]
WriteBatch = List[Tuple[Variable, bytes]]
Connection = Union[SerialConnection, SocketConnection]
DeviceInfo = Dict[str, object]


class Device:
    def __init__(
        self,
        connection: Connection,
        device_id: int,
        elf_parser: Optional[ElfParser] = None,
    ) -> None:
        self.connection = connection
        self.device_id = device_id
        self.parser = elf_parser or ElfParser()
        self._monitored: Dict[str, MonitoredVar] = {}
        self._on_data: Optional[Callable[[str, bytes], None]] = None
        self._protocol_version: Optional[int] = None
        self._device_name: Optional[str] = None
        self._last_error: str = ""

    @property
    def last_error(self) -> str:
        return self._last_error

    def _set_error_from_response(self, response: Optional[Frame], op: str) -> None:
        if response is None:
            self._last_error = f"{op}: timeout or no response"
            return

        if response.is_nack():
            code = response.get_error_code()
            if code is not None:
                self._last_error = f"{op}: NACK {code.name} (0x{int(code):02X})"
            else:
                data_hex = response.data.hex() if response.data else ""
                self._last_error = f"{op}: NACK (data={data_hex})"
            return

        self._last_error = f"{op}: unexpected command 0x{int(response.command):02X}"

    def _send_and_wait_filtered(
        self,
        data: bytes,
        timeout: float,
        accept: AcceptFrame,
    ) -> Optional[Frame]:
        response = self.connection.send_and_wait(
            data,
            timeout,
            accept_frame=accept,
        )
        if response is not None:
            return response

        # Fallback for flaky serial drivers: do one direct blocking exchange.
        if isinstance(self.connection, SerialConnection) and self.connection.is_open():
            try:
                ser = self.connection._serial
                if ser is None:
                    return None
                ser.reset_input_buffer()
                ser.write(data)
                ser.timeout = timeout
                chunk = ser.read(64)
            except Exception:
                return None

            if not chunk:
                return None

            buf = bytearray(chunk)
            for i in range(max(0, len(buf) - 6)):
                if buf[i] != 0xAA or buf[i + 1] != 0x55:
                    continue
                end = i + 3 + buf[i + 2]
                if end > len(buf):
                    continue
                frame = Protocol.decode(bytes(buf[i:end]))
                if frame is None:
                    continue
                if not accept(frame):
                    continue
                return frame

        return None

    def load_elf(self, filepath: str) -> List[Variable]:
        return self.parser.parse(filepath)

    def load_map(self, filepath: str) -> List[Variable]:
        return self.parser.parse_map(filepath)

    def get_variable(self, name: str) -> Optional[Variable]:
        return self.parser.get_variable(name)

    def list_variables(self) -> List[Variable]:
        return list(self.parser.variables.values())

    def ping(self, timeout: float = 1.0) -> bool:
        data = Protocol.encode_heartbeat(self.device_id)
        for _ in range(3):
            response = self._send_and_wait_filtered(
                data,
                timeout,
                accept=lambda f: f.is_ack() or f.is_nack(),
            )
            if response is not None and response.is_ack():
                # Clear stale periodic streaming state from previous host sessions.
                self.stop_monitor()
                self._last_error = ""
                return True
            time.sleep(0.05)
        self._set_error_from_response(response, "ping")
        return False

    def query_info(self, timeout: float = 1.0) -> Optional[DeviceInfo]:
        data = Protocol.encode_query_info(self.device_id)
        response = self._send_and_wait_filtered(
            data,
            timeout,
            accept=lambda f: f.command == CommandType.QUERY_INFO or f.is_nack(),
        )

        if response and len(response.data) >= 2:
            self._protocol_version = response.data[0]
            name_len = response.data[1]
            if len(response.data) >= 2 + name_len:
                self._device_name = response.data[2 : 2 + name_len].decode(
                    "utf-8", errors="ignore"
                )

            return {
                "protocol_version": self._protocol_version,
                "device_name": self._device_name,
            }
        self._set_error_from_response(response, "query_info")
        return None

    def read_single(
        self, variables: List[Variable], timeout: float = 1.0
    ) -> Dict[str, bytes]:
        addresses = [v.address for v in variables]
        data = Protocol.encode_read(self.device_id, addresses, rate=0)
        for _ in range(3):
            response = self._send_and_wait_filtered(
                data,
                timeout,
                accept=lambda f: (
                    (
                        f.command >= CommandType.READ_SINGLE
                        and f.command <= CommandType.READ_500MS
                    )
                    or f.is_nack()
                ),
            )

            results: Dict[str, bytes] = {}
            if response:
                if response.is_nack():
                    self._set_error_from_response(response, "read")
                    return results
                parsed = Protocol.decode_read_response(response)
                addr_to_name = {v.address: v.name for v in variables}
                for addr, value in parsed:
                    name = addr_to_name.get(addr)
                    if name:
                        results[name] = value

                if parsed:
                    self._last_error = ""
                    return results

                self._set_error_from_response(response, "read")
            else:
                self._set_error_from_response(response, "read")
            time.sleep(0.03)

        return {}

    def read_value(self, variable: Variable, timeout: float = 1.0) -> Optional[bytes]:
        results = self.read_single([variable], timeout)
        return results.get(variable.name)

    def write_single(
        self,
        variable: Variable,
        value: bytes,
        timeout: float = 1.0,
        dtype_override: Optional[DataType] = None,
    ) -> bool:
        dtype = dtype_override or (
            DataType(variable.dtype_code) if variable.dtype_code else DataType.UINT32
        )
        data = Protocol.encode_write(self.device_id, [(variable.address, dtype, value)])
        response: Optional[Frame] = None
        for _ in range(3):
            response = self._send_and_wait_filtered(
                data,
                timeout,
                accept=lambda f: f.is_ack() or f.is_nack(),
            )
            if response is not None and response.is_ack():
                self._last_error = ""
                return True
            self._set_error_from_response(response, "write")
            time.sleep(0.03)

        return False

    def write_batch(self, writes: WriteBatch, timeout: float = 1.0) -> bool:
        encoded_writes: List[Tuple[int, DataType, bytes]] = []
        for var, value in writes:
            dtype = DataType(var.dtype_code) if var.dtype_code else DataType.UINT32
            encoded_writes.append((var.address, dtype, value))

        data = Protocol.encode_write(self.device_id, encoded_writes)
        response = self._send_and_wait_filtered(
            data,
            timeout,
            accept=lambda f: f.is_ack() or f.is_nack(),
        )
        if response is not None and response.is_ack():
            self._last_error = ""
            return True

        self._set_error_from_response(response, "write_batch")
        return False

    def start_monitor(
        self,
        variables: List[Variable],
        rate: int,
        on_data: Optional[Callable[[str, bytes], None]] = None,
    ) -> bool:
        addresses = [v.address for v in variables]
        data = Protocol.encode_read(self.device_id, addresses, rate=rate)
        response = self._send_and_wait_filtered(
            data,
            timeout=1.0,
            accept=lambda f: f.is_ack() or f.is_nack(),
        )

        if response and response.is_ack():
            for var in variables:
                self._monitored[var.name] = MonitoredVar(variable=var, rate=rate)
            self._on_data = on_data
            self._last_error = ""
            return True

        self._set_error_from_response(response, "start_monitor")
        return False

    def stop_monitor(self) -> bool:
        data = Protocol.encode_stop(self.device_id)
        response = self._send_and_wait_filtered(
            data,
            timeout=1.0,
            accept=lambda f: f.is_ack() or f.is_nack(),
        )
        self._monitored.clear()
        if response is not None and response.is_ack():
            self._last_error = ""
            return True

        self._set_error_from_response(response, "stop_monitor")
        return False

    def on_frame_received(self, frame: Frame) -> None:
        if (
            frame.command >= CommandType.READ_1MS
            and frame.command <= CommandType.READ_500MS
        ):
            parsed = Protocol.decode_read_response(frame)

            for addr, value in parsed:
                for name, monitored in self._monitored.items():
                    if monitored.variable.address == addr:
                        monitored.last_value = value
                        monitored.last_update = time.time()
                        if self._on_data:
                            self._on_data(name, value)
                        break

    @staticmethod
    def bytes_to_value(data: bytes, dtype: DataType) -> Any:
        return struct.unpack(dtype.format_char, data)[0]

    @staticmethod
    def value_to_bytes(value: Any, dtype: DataType) -> bytes:
        return struct.pack(dtype.format_char, value)
