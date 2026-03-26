from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
import struct
import time

from .protocol import (
    Protocol,
    Frame,
    CommandType,
    DataType,
    ErrorCode,
    SAMPLE_RATES,
)
from .serial_conn import SerialConnection
from .elf_parser import ElfParser, Variable


@dataclass
class MonitoredVar:
    variable: Variable
    rate: int
    last_value: Optional[bytes] = None
    last_update: Optional[float] = None


class Device:
    def __init__(
        self,
        connection: SerialConnection,
        device_id: int,
        elf_parser: Optional[ElfParser] = None,
    ):
        self.connection = connection
        self.device_id = device_id
        self.parser = elf_parser or ElfParser()
        self._monitored: Dict[str, MonitoredVar] = {}
        self._on_data: Optional[Callable[[str, bytes], None]] = None
        self._protocol_version: Optional[int] = None
        self._device_name: Optional[str] = None

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
            response = self.connection.send_and_wait(data, timeout)
            if response is not None and response.is_ack():
                return True
            time.sleep(0.05)
        return False

    def query_info(self, timeout: float = 1.0) -> Optional[Dict]:
        data = Protocol.encode_query_info(self.device_id)
        response = self.connection.send_and_wait(data, timeout)

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
        return None

    def read_single(
        self, variables: List[Variable], timeout: float = 1.0
    ) -> Dict[str, bytes]:
        addresses = [v.address for v in variables]
        data = Protocol.encode_read(self.device_id, addresses, rate=0)
        response = self.connection.send_and_wait(data, timeout)

        results = {}
        if response:
            parsed = Protocol.decode_read_response(response)
            addr_to_name = {v.address: v.name for v in variables}
            for addr, value in parsed:
                name = addr_to_name.get(addr)
                if name:
                    results[name] = value

        return results

    def read_value(self, variable: Variable, timeout: float = 1.0) -> Optional[bytes]:
        results = self.read_single([variable], timeout)
        return results.get(variable.name)

    def write_single(
        self, variable: Variable, value: bytes, timeout: float = 1.0
    ) -> bool:
        dtype = (
            DataType(variable.dtype_code) if variable.dtype_code else DataType.UINT32
        )
        data = Protocol.encode_write(self.device_id, [(variable.address, dtype, value)])
        response = self.connection.send_and_wait(data, timeout)
        return response is not None and response.is_ack()

    def write_batch(self, writes: List[tuple], timeout: float = 1.0) -> bool:
        encoded_writes = []
        for var, value in writes:
            dtype = DataType(var.dtype_code) if var.dtype_code else DataType.UINT32
            encoded_writes.append((var.address, dtype, value))

        data = Protocol.encode_write(self.device_id, encoded_writes)
        response = self.connection.send_and_wait(data, timeout)
        return response is not None and response.is_ack()

    def start_monitor(
        self,
        variables: List[Variable],
        rate: int,
        on_data: Optional[Callable[[str, bytes], None]] = None,
    ) -> bool:
        addresses = [v.address for v in variables]
        data = Protocol.encode_read(self.device_id, addresses, rate=rate)
        response = self.connection.send_and_wait(data)

        if response and response.is_ack():
            for var in variables:
                self._monitored[var.name] = MonitoredVar(variable=var, rate=rate)
            self._on_data = on_data
            return True

        return False

    def stop_monitor(self) -> bool:
        data = Protocol.encode_stop(self.device_id)
        response = self.connection.send_and_wait(data)
        self._monitored.clear()
        return response is not None and response.is_ack()

    def on_frame_received(self, frame: Frame):
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
    def bytes_to_value(data: bytes, dtype: DataType) -> any:
        return struct.unpack(dtype.format_char, data)[0]

    @staticmethod
    def value_to_bytes(value: any, dtype: DataType) -> bytes:
        return struct.pack(dtype.format_char, value)
