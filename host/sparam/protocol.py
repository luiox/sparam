import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional, Tuple

import crcmod.predefined


class CommandType(IntEnum):
    HEARTBEAT = 0x00
    QUERY_INFO = 0x01
    READ_SINGLE = 0x10
    READ_1MS = 0x11
    READ_5MS = 0x12
    READ_10MS = 0x13
    READ_20MS = 0x14
    READ_50MS = 0x15
    READ_100MS = 0x16
    READ_200MS = 0x17
    READ_500MS = 0x18
    STOP_SAMPLING = 0x1F
    WRITE_SINGLE = 0x20
    WRITE_BATCH = 0x21
    ACK = 0xA0
    NACK = 0xA1


class DataType(IntEnum):
    UINT8 = 0x01
    INT8 = 0x02
    UINT16 = 0x03
    INT16 = 0x04
    UINT32 = 0x05
    INT32 = 0x06
    FLOAT = 0x07

    @property
    def size(self) -> int:
        sizes = {
            DataType.UINT8: 1,
            DataType.INT8: 1,
            DataType.UINT16: 2,
            DataType.INT16: 2,
            DataType.UINT32: 4,
            DataType.INT32: 4,
            DataType.FLOAT: 4,
        }
        return sizes[self]

    @property
    def format_char(self) -> str:
        formats = {
            DataType.UINT8: "<B",
            DataType.INT8: "<b",
            DataType.UINT16: "<H",
            DataType.INT16: "<h",
            DataType.UINT32: "<I",
            DataType.INT32: "<i",
            DataType.FLOAT: "<f",
        }
        return formats[self]


class ErrorCode(IntEnum):
    INVALID_ADDR = 0x01
    INVALID_TYPE = 0x02
    TABLE_FULL = 0x03
    CRC_ERROR = 0x04


SAMPLE_RATES = {
    0: None,
    1: 1,
    2: 5,
    3: 10,
    4: 20,
    5: 50,
    6: 100,
    7: 200,
    8: 500,
}


@dataclass
class Frame:
    device_id: int
    command: int
    data: bytes

    def is_ack(self) -> bool:
        return self.command == CommandType.ACK

    def is_nack(self) -> bool:
        return self.command == CommandType.NACK

    def get_error_code(self) -> Optional[ErrorCode]:
        if self.is_nack() and len(self.data) > 0:
            return ErrorCode(self.data[0])
        return None


class Protocol:
    HEADER = bytes([0xAA, 0x55])
    _CRC16_MODBUS = crcmod.predefined.mkCrcFun("modbus")

    @classmethod
    def crc16(cls, data: bytes) -> int:
        return int(cls._CRC16_MODBUS(data))

    @classmethod
    def encode(cls, device_id: int, command: int, data: bytes = b"") -> bytes:
        payload = bytes([device_id, command]) + data
        crc = cls.crc16(payload)
        length = len(payload) + 2
        return cls.HEADER + bytes([length]) + payload + struct.pack("<H", crc)

    @classmethod
    def decode(cls, raw: bytes) -> Optional[Frame]:
        if len(raw) < 7:
            return None
        if raw[0:2] != cls.HEADER:
            return None

        length = raw[2]
        if len(raw) < 3 + length:
            return None

        payload_start = 3
        payload_end = 3 + length - 2
        crc_start = payload_end

        payload = raw[payload_start:crc_start]
        crc_received = struct.unpack("<H", raw[crc_start : crc_start + 2])[0]
        crc_calculated = cls.crc16(payload)

        if crc_received != crc_calculated:
            return None

        device_id = payload[0]
        command = payload[1]
        data = payload[2:]

        return Frame(device_id=device_id, command=command, data=data)

    @classmethod
    def encode_read(cls, device_id: int, addresses: List[int], rate: int = 0) -> bytes:
        command: int
        if rate == 0:
            command = CommandType.READ_SINGLE
        else:
            command = int(CommandType.READ_SINGLE) + rate

        data = b"".join(struct.pack("<I", addr) for addr in addresses)
        return cls.encode(device_id, command, data)

    @classmethod
    def encode_write(
        cls, device_id: int, writes: List[Tuple[int, DataType, bytes]]
    ) -> bytes:
        if len(writes) == 1:
            command = CommandType.WRITE_SINGLE
        else:
            command = CommandType.WRITE_BATCH

        data = bytes([len(writes)])
        for addr, dtype, value in writes:
            data += struct.pack("<I", addr)
            data += bytes([dtype])
            data += value

        return cls.encode(device_id, command, data)

    @classmethod
    def encode_stop(cls, device_id: int) -> bytes:
        return cls.encode(device_id, CommandType.STOP_SAMPLING)

    @classmethod
    def encode_heartbeat(cls, device_id: int) -> bytes:
        return cls.encode(device_id, CommandType.HEARTBEAT)

    @classmethod
    def encode_query_info(cls, device_id: int) -> bytes:
        return cls.encode(device_id, CommandType.QUERY_INFO)

    @classmethod
    def decode_read_response(cls, frame: Frame) -> List[Tuple[int, bytes]]:
        results = []
        data = frame.data
        offset = 0

        while offset + 4 <= len(data):
            addr = struct.unpack("<I", data[offset : offset + 4])[0]
            offset += 4

            value_bytes = data[offset : offset + 4]
            offset += 4

            results.append((addr, value_bytes))

        return results
