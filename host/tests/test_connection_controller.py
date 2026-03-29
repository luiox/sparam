from gui.controllers.connection_controller import ConnectionController


class _FakeConnection:
    should_open = True

    def __init__(self, port: str, baudrate: int, timeout: float) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.last_error = "mock open failure"
        self.closed = False
        self._is_open = False

    def open(self) -> bool:
        self._is_open = self.should_open
        return self._is_open

    def close(self) -> None:
        self.closed = True
        self._is_open = False

    def is_open(self) -> bool:
        return self._is_open


class _FakeDevice:
    should_ping = True

    def __init__(
        self,
        conn: _FakeConnection,
        device_id: int,
        elf_parser: object,
    ) -> None:
        self.conn = conn
        self.device_id = device_id
        self.elf_parser = elf_parser
        self.last_error = "mock ping failure"

    def ping(self, timeout: float = 1.0) -> bool:
        _ = timeout
        return self.should_ping


class _FakeManager:
    def __init__(self, device: _FakeDevice) -> None:
        self.device = device
        self.stopped = False

    def stop_monitor(self) -> None:
        self.stopped = True


def test_connection_controller_connect_success() -> None:
    _FakeConnection.should_open = True
    _FakeDevice.should_ping = True

    controller = ConnectionController(
        connection_cls=_FakeConnection,
        device_cls=_FakeDevice,
        manager_cls=_FakeManager,
    )
    result = controller.connect("COM1", 115200, 1, parser=object())

    assert result.ok is True
    assert result.conn is not None
    assert result.device is not None
    assert result.device_manager is not None


def test_connection_controller_connect_open_failure() -> None:
    _FakeConnection.should_open = False
    _FakeDevice.should_ping = True

    controller = ConnectionController(
        connection_cls=_FakeConnection,
        device_cls=_FakeDevice,
        manager_cls=_FakeManager,
    )
    result = controller.connect("COM1", 115200, 1, parser=object())

    assert result.ok is False
    assert "unable to open" in result.error


def test_connection_controller_connect_ping_failure_closes_connection() -> None:
    _FakeConnection.should_open = True
    _FakeDevice.should_ping = False

    controller = ConnectionController(
        connection_cls=_FakeConnection,
        device_cls=_FakeDevice,
        manager_cls=_FakeManager,
    )
    result = controller.connect("COM1", 115200, 1, parser=object())

    assert result.ok is False
    assert result.conn is None


def test_connection_controller_disconnect_stops_monitor_and_closes() -> None:
    conn = _FakeConnection("COM1", 115200, 1.0)
    conn._is_open = True
    manager = _FakeManager(_FakeDevice(conn, 1, object()))

    controller = ConnectionController(
        connection_cls=_FakeConnection,
        device_cls=_FakeDevice,
        manager_cls=_FakeManager,
    )
    controller.disconnect(conn, manager)

    assert manager.stopped is True
    assert conn.closed is True
