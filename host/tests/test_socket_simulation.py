import socket
import struct
import threading
import time

from sparam import Device, SocketConnection, Protocol, CommandType
from sparam.elf_parser import Variable
from sparam.device_manager import DeviceManager


class SimulatedDeviceServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0, device_id: int = 1):
        self.host = host
        self.port = port
        self.device_id = device_id
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind((host, port))
        self._sock.listen(1)
        self.port = self._sock.getsockname()[1]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self.memory = {
            0x20000000: struct.pack("<I", 123456),
        }
        self._stream_thread = None
        self._stream_stop = threading.Event()
        self._stream_conn = None
        self._stream_rate = 0
        self._stream_addresses = []

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._stream_stop.set()
        try:
            with socket.create_connection((self.host, self.port), timeout=0.2):
                pass
        except OSError:
            pass
        self._thread.join(timeout=1.0)
        if self._stream_thread:
            self._stream_thread.join(timeout=1.0)
        self._sock.close()

    def _serve(self):
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return

            with conn:
                conn.settimeout(0.2)
                rx = bytearray()
                while not self._stop.is_set():
                    try:
                        data = conn.recv(256)
                        if not data:
                            break
                        rx.extend(data)
                    except socket.timeout:
                        continue
                    except OSError:
                        break

                    while len(rx) >= 7:
                        if rx[0] != 0xAA or rx[1] != 0x55:
                            rx.pop(0)
                            continue

                        if len(rx) < 4:
                            break

                        length = rx[2]
                        total_len = 3 + length
                        if len(rx) < total_len:
                            break

                        packet = bytes(rx[:total_len])
                        rx = rx[total_len:]
                        frame = Protocol.decode(packet)
                        if not frame:
                            continue

                        response = self._handle_frame(frame, conn)
                        if response:
                            conn.sendall(response)

    def _start_streaming(self, conn, command, addresses):
        self._stream_stop.set()
        if self._stream_thread:
            self._stream_thread.join(timeout=1.0)

        self._stream_stop = threading.Event()
        self._stream_conn = conn
        self._stream_rate = command - CommandType.READ_SINGLE
        self._stream_addresses = addresses

        def stream():
            tick = 0
            intervals = {
                1: 0.001,
                2: 0.005,
                3: 0.01,
                4: 0.02,
                5: 0.05,
                6: 0.1,
                7: 0.2,
                8: 0.5,
            }
            interval = intervals[self._stream_rate]
            while not self._stream_stop.wait(interval):
                tick += 1
                payload = bytearray()
                for index, address in enumerate(self._stream_addresses):
                    value = 1000 + tick * 10 + index
                    self.memory[address] = struct.pack("<I", value)
                    payload.extend(struct.pack("<I", address))
                    payload.extend(self.memory[address])
                try:
                    self._stream_conn.sendall(
                        Protocol.encode(self.device_id, command, bytes(payload))
                    )
                except OSError:
                    break

        self._stream_thread = threading.Thread(target=stream, daemon=True)
        self._stream_thread.start()

    def _handle_frame(self, frame, conn):
        if frame.command == CommandType.HEARTBEAT:
            return Protocol.encode(self.device_id, CommandType.ACK)

        if frame.command == CommandType.READ_SINGLE:
            payload = bytearray()
            for i in range(0, len(frame.data), 4):
                address = struct.unpack("<I", frame.data[i : i + 4])[0]
                payload.extend(struct.pack("<I", address))
                payload.extend(self.memory.get(address, b"\x00\x00\x00\x00"))
            return Protocol.encode(self.device_id, CommandType.READ_SINGLE, bytes(payload))

        if frame.command in (CommandType.WRITE_SINGLE, CommandType.WRITE_BATCH):
            count = frame.data[0]
            offset = 1
            for _ in range(count):
                address = struct.unpack("<I", frame.data[offset : offset + 4])[0]
                offset += 4
                _dtype = frame.data[offset]
                offset += 1
                value = frame.data[offset : offset + 4]
                offset += 4
                self.memory[address] = value
            return Protocol.encode(self.device_id, CommandType.ACK)

        if CommandType.READ_1MS <= frame.command <= CommandType.READ_500MS:
            addresses = []
            for i in range(0, len(frame.data), 4):
                addresses.append(struct.unpack("<I", frame.data[i : i + 4])[0])
            self._start_streaming(conn, frame.command, addresses)
            return Protocol.encode(self.device_id, CommandType.ACK)

        if frame.command == CommandType.STOP_SAMPLING:
            self._stream_stop.set()
            return Protocol.encode(self.device_id, CommandType.ACK)

        return Protocol.encode(self.device_id, CommandType.NACK, b"\x02")


def test_device_ping_read_write_over_socket():
    server = SimulatedDeviceServer(device_id=1)
    server.start()

    conn = SocketConnection("127.0.0.1", server.port, timeout=1.0)
    assert conn.open()

    device = Device(conn, device_id=1)
    variable = Variable(
        name="test_u32",
        address=0x20000000,
        size=4,
        var_type="uint32_t",
    )

    assert device.ping(timeout=1.0)

    read_result = device.read_single([variable], timeout=1.0)
    assert struct.unpack("<I", read_result["test_u32"])[0] == 123456

    new_value = struct.pack("<I", 654321)
    assert device.write_single(variable, new_value, timeout=1.0)

    read_result2 = device.read_single([variable], timeout=1.0)
    assert struct.unpack("<I", read_result2["test_u32"])[0] == 654321

    conn.close()
    server.stop()


def test_device_manager_receives_periodic_stream_samples():
    server = SimulatedDeviceServer(device_id=1)
    server.start()

    conn = SocketConnection("127.0.0.1", server.port, timeout=1.0)
    assert conn.open()

    device = Device(conn, device_id=1)
    variable = Variable(
        name="motor_speed",
        address=0x20000000,
        size=4,
        var_type="uint32_t",
    )
    samples = []
    manager = DeviceManager(device)
    manager.add_callback(samples.append)

    assert manager.start_monitor([variable], rate=3)

    deadline = time.time() + 0.3
    while len(samples) < 3 and time.time() < deadline:
        time.sleep(0.01)

    manager.stop_monitor()
    conn.close()
    server.stop()

    assert len(samples) >= 3
    assert all(sample.name == "motor_speed" for sample in samples)
    assert all(isinstance(sample.timestamp, float) for sample in samples)
    assert samples[-1].value > samples[0].value
