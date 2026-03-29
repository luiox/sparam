from dataclasses import dataclass
from typing import Optional, Protocol

from sparam import Device, DeviceManager, ElfParser, SerialConnection


class ConnectionLike(Protocol):
    @property
    def last_error(self) -> str:
        ...

    def open(self) -> bool:
        ...

    def close(self) -> None:
        ...

    def is_open(self) -> bool:
        ...


class MonitorManagerLike(Protocol):
    def stop_monitor(self) -> bool:
        ...


@dataclass
class ConnectionResult:
    ok: bool
    conn: Optional[SerialConnection] = None
    device: Optional[Device] = None
    device_manager: Optional[DeviceManager] = None
    error: str = ""


class ConnectionController:
    def __init__(
        self,
        connection_cls: type = SerialConnection,
        device_cls: type = Device,
        manager_cls: type = DeviceManager,
    ) -> None:
        self._connection_cls = connection_cls
        self._device_cls = device_cls
        self._manager_cls = manager_cls

    def connect(
        self,
        port: str,
        baudrate: int,
        device_id: int,
        parser: ElfParser,
        timeout: float = 1.0,
    ) -> ConnectionResult:
        conn = self._connection_cls(port, baudrate, timeout)
        if not conn.open():
            reason = conn.last_error or "port busy or unavailable"
            return ConnectionResult(ok=False, error=f"unable to open {port} ({reason})")

        device = self._device_cls(conn, device_id, elf_parser=parser)
        if not device.ping(timeout=timeout):
            conn.close()
            reason = device.last_error or "ping timeout"
            return ConnectionResult(ok=False, error=reason)

        manager = self._manager_cls(device)
        return ConnectionResult(
            ok=True,
            conn=conn,
            device=device,
            device_manager=manager,
        )

    def disconnect(
        self,
        conn: Optional[ConnectionLike],
        device_manager: Optional[MonitorManagerLike],
    ) -> None:
        if device_manager:
            device_manager.stop_monitor()
        if conn and conn.is_open():
            conn.close()
