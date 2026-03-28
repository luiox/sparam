import socket
import time
from threading import Event, Thread
from typing import Callable, Literal, Optional

from .protocol import Frame, Protocol


class SocketConnection:
    def __init__(self, host: str, port: int, timeout: float = 1.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._rx_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._on_frame: Optional[Callable[[Frame], None]] = None
        self._rx_buffer = bytearray()

    def is_receive_running(self) -> bool:
        return bool(self._rx_thread and self._rx_thread.is_alive())

    def stop_receive(self) -> None:
        self._stop_event.set()
        if self._rx_thread and self._rx_thread.is_alive():
            self._rx_thread.join(timeout=1.0)
        self._rx_thread = None
        self._on_frame = None

    def open(self) -> bool:
        try:
            self._sock = socket.create_connection(
                (self.host, self.port), timeout=self.timeout
            )
            self._sock.settimeout(0.2)
            return True
        except OSError:
            self._sock = None
            return False

    def close(self) -> None:
        self.stop_receive()

        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def is_open(self) -> bool:
        return self._sock is not None

    def send(self, data: bytes) -> bool:
        if not self._sock:
            return False

        try:
            self._sock.sendall(data)
            return True
        except OSError:
            return False

    def _receive_loop(self) -> None:
        while not self._stop_event.is_set() and self._sock:
            try:
                data = self._sock.recv(256)
                if not data:
                    break
                self._rx_buffer.extend(data)
                self._try_parse_frames()
            except socket.timeout:
                continue
            except OSError:
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

    def start_receive(self, on_frame: Callable[[Frame], None]) -> None:
        self._on_frame = on_frame
        if self.is_receive_running():
            return
        self._stop_event.clear()
        self._rx_thread = Thread(target=self._receive_loop, daemon=True)
        self._rx_thread.start()

    def send_and_wait(
        self,
        data: bytes,
        timeout: float = 1.0,
        accept_frame: Optional[Callable[[Frame], bool]] = None,
    ) -> Optional[Frame]:
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

        end_time = time.monotonic() + timeout
        while result is None and time.monotonic() < end_time:
            try:
                if not self._sock:
                    break
                data_chunk = self._sock.recv(256)
                if not data_chunk:
                    break
                self._rx_buffer.extend(data_chunk)
                self._try_parse_frames()
            except socket.timeout:
                pass
            except OSError:
                break

            if event.is_set():
                break

        self._on_frame = old_callback
        return result

    def __enter__(self) -> "SocketConnection":
        self.open()
        return self

    def __exit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> Literal[False]:
        self.close()
        return False
