import time
from dataclasses import dataclass
from typing import Callable, List

from .device import Device
from .elf_parser import Variable
from .protocol import DataType


@dataclass
class SamplePoint:
    name: str
    timestamp: float
    value: float


class DeviceManager:
    def __init__(self, device: Device):
        self.device = device
        self._callbacks: List[Callable[[SamplePoint], None]] = []
        self._receiving_started = False

    def add_callback(self, callback: Callable[[SamplePoint], None]) -> None:
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[SamplePoint], None]) -> None:
        self._callbacks = [item for item in self._callbacks if item != callback]

    def _stop_receive_if_started(self) -> None:
        if not self._receiving_started:
            return

        if hasattr(self.device.connection, "stop_receive"):
            self.device.connection.stop_receive()
        self._receiving_started = False

    def start_monitor(self, variables: List[Variable], rate: int) -> bool:
        if not self._receiving_started and hasattr(
            self.device.connection, "start_receive"
        ):
            self.device.connection.start_receive(self.device.on_frame_received)
            self._receiving_started = True

        started = self.device.start_monitor(variables, rate, self._on_data)
        if not started:
            self._stop_receive_if_started()
        return started

    def stop_monitor(self) -> bool:
        stopped = self.device.stop_monitor()
        self._stop_receive_if_started()
        return stopped

    def _on_data(self, name: str, raw_value: bytes) -> None:
        variable = self.device.get_variable(name)
        if variable and variable.dtype_code:
            try:
                value = Device.bytes_to_value(
                    raw_value[: DataType(variable.dtype_code).size],
                    DataType(variable.dtype_code),
                )
            except Exception:
                value = float(int.from_bytes(raw_value[:4], "little", signed=False))
        else:
            value = float(int.from_bytes(raw_value[:4], "little", signed=False))

        sample = SamplePoint(name=name, timestamp=time.time(), value=float(value))
        for callback in list(self._callbacks):
            callback(sample)
