from typing import Optional, Callable, List
from threading import Thread, Event
import time

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    raise ImportError("pyserial is required: pip install pyserial")

from .protocol import Protocol, Frame


class SerialConnection:
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Optional[serial.Serial] = None
        self._rx_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._on_frame: Optional[Callable[[Frame], None]] = None
        self._rx_buffer = bytearray()

    @staticmethod
    def list_ports() -> List[str]:
        ports = serial.tools.list_ports.comports()
        return [p.device for p in ports]

    def open(self) -> bool:
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
            )
            return True
        except serial.SerialException:
            return False

    def close(self):
        self._stop_event.set()
        if self._rx_thread:
            self._rx_thread.join(timeout=1.0)
            self._rx_thread = None

        if self._serial and self._serial.is_open:
            self._serial.close()
            self._serial = None

    def is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def send(self, data: bytes) -> bool:
        if not self.is_open():
            return False
        try:
            self._serial.write(data)
            return True
        except serial.SerialException:
            return False

    def _receive_loop(self):
        while not self._stop_event.is_set() and self._serial:
            try:
                data = self._serial.read(64)
                if data:
                    self._rx_buffer.extend(data)
                    self._try_parse_frames()
            except serial.SerialException:
                break

    def _try_parse_frames(self):
        while len(self._rx_buffer) >= 7:
            if self._rx_buffer[0] != 0xAA or self._rx_buffer[1] != 0x55:
                self._rx_buffer.pop(0)
                continue

            if len(self._rx_buffer) < 4:
                break

            length = self._rx_buffer[2]
            total_len = 3 + length + 2

            if len(self._rx_buffer) < total_len:
                break

            frame_data = bytes(self._rx_buffer[:total_len])
            self._rx_buffer = self._rx_buffer[total_len:]

            frame = Protocol.decode(frame_data)
            if frame and self._on_frame:
                self._on_frame(frame)

    def start_receive(self, on_frame: Callable[[Frame], None]):
        self._on_frame = on_frame
        self._stop_event.clear()
        self._rx_thread = Thread(target=self._receive_loop, daemon=True)
        self._rx_thread.start()

    def send_and_wait(self, data: bytes, timeout: float = 1.0) -> Optional[Frame]:
        result: Optional[Frame] = None
        event = Event()

        def on_response(frame: Frame):
            nonlocal result
            result = frame
            event.set()

        old_callback = self._on_frame
        self._on_frame = on_response

        if not self.send(data):
            self._on_frame = old_callback
            return None

        event.wait(timeout)
        self._on_frame = old_callback
        return result

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
