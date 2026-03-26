import time
from threading import Event, Thread
from typing import Callable, List, Literal, Optional

try:
    import serial
    import serial.tools.list_ports
except ImportError as exc:
    raise ImportError("pyserial is required: pip install pyserial") from exc

from .protocol import Frame, Protocol


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
        self.last_error = ""

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
            self._serial.reset_input_buffer()
            self.last_error = ""
            return True
        except serial.SerialException as exc:
            self.last_error = str(exc)
            return False

    def close(self) -> None:
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
        serial_port = self._serial
        if serial_port is None:
            return False
        try:
            serial_port.write(data)
            return True
        except serial.SerialException:
            return False

    def _receive_loop(self) -> None:
        while not self._stop_event.is_set() and self._serial:
            try:
                serial_port = self._serial
                if serial_port is None:
                    break
                data = serial_port.read(64)
                if data:
                    self._rx_buffer.extend(data)
                    self._try_parse_frames()
            except serial.SerialException:
                break

    def _try_parse_frames(self) -> None:
        while len(self._rx_buffer) >= 7:
            if self._rx_buffer[0] != 0xAA or self._rx_buffer[1] != 0x55:
                self._rx_buffer.pop(0)
                continue

            if len(self._rx_buffer) < 4:
                break

            length = self._rx_buffer[2]
            total_len = 3 + length

            if len(self._rx_buffer) < total_len:
                break

            frame_data = bytes(self._rx_buffer[:total_len])
            self._rx_buffer = self._rx_buffer[total_len:]

            frame = Protocol.decode(frame_data)
            if frame and self._on_frame:
                self._on_frame(frame)

    def _pop_next_frame(self) -> Optional[Frame]:
        while len(self._rx_buffer) >= 7:
            if self._rx_buffer[0] != 0xAA or self._rx_buffer[1] != 0x55:
                self._rx_buffer.pop(0)
                continue

            if len(self._rx_buffer) < 4:
                return None

            length = self._rx_buffer[2]
            total_len = 3 + length
            if len(self._rx_buffer) < total_len:
                return None

            frame_data = bytes(self._rx_buffer[:total_len])
            self._rx_buffer = self._rx_buffer[total_len:]
            frame = Protocol.decode(frame_data)
            if frame:
                return frame

        return None

    def start_receive(self, on_frame: Callable[[Frame], None]) -> None:
        self._on_frame = on_frame
        self._stop_event.clear()
        self._rx_thread = Thread(target=self._receive_loop, daemon=True)
        self._rx_thread.start()

    def send_and_wait(
        self,
        data: bytes,
        timeout: float = 1.0,
        accept_frame: Optional[Callable[[Frame], bool]] = None,
    ) -> Optional[Frame]:
        if not self.is_open():
            return None

        # If an async RX loop is already running, wait through the callback path.
        if self._rx_thread and self._rx_thread.is_alive():
            result: Optional[Frame] = None
            event = Event()

            def on_response(frame: Frame) -> None:
                nonlocal result
                if accept_frame and not accept_frame(frame):
                    return
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

        # Sync request-response path for CLI/GUI commands that don't start RX thread.
        self._rx_buffer.clear()
        serial_port = self._serial
        if serial_port is None:
            return None
        try:
            serial_port.reset_input_buffer()
        except serial.SerialException:
            return None

        if not self.send(data):
            return None

        # Give UART/USB bridge a moment to push the full response into host buffer.
        time.sleep(0.02)

        serial_port.timeout = timeout
        buf = bytearray()
        for _ in range(3):
            try:
                chunk = serial_port.read(64)
            except serial.SerialException:
                return None

            if not chunk:
                continue

            buf.extend(chunk)
            for i in range(max(0, len(buf) - 6)):
                if buf[i] != 0xAA or buf[i + 1] != 0x55:
                    continue

                total_len = 3 + buf[i + 2]
                end = i + total_len
                if end > len(buf):
                    continue

                frame = Protocol.decode(bytes(buf[i:end]))
                if frame is None:
                    continue
                if accept_frame and not accept_frame(frame):
                    continue
                return frame

        return None

    def __enter__(self) -> "SerialConnection":
        self.open()
        return self

    def __exit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> Literal[False]:
        self.close()
        return False
