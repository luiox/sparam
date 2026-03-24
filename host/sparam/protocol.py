from enum import IntEnum
from dataclasses import dataclass
from typing import List, Optional, Tuple
import struct


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
    CRC16_TABLE = [
        0x0000,
        0xC0C1,
        0xC181,
        0x0140,
        0xC301,
        0x03C0,
        0x0280,
        0xC241,
        0xC601,
        0x06C0,
        0x0780,
        0xC741,
        0x0500,
        0xC5C1,
        0xC481,
        0x0440,
        0xCC01,
        0x0CC0,
        0x0D80,
        0xCD41,
        0x0F00,
        0xCFC1,
        0xCE81,
        0x0E40,
        0x0A00,
        0xCAC1,
        0xCB81,
        0x0B40,
        0xC901,
        0x09C0,
        0x0880,
        0xC841,
        0xD801,
        0x18C0,
        0x1980,
        0xD941,
        0x1B00,
        0xDBC1,
        0xDA81,
        0x1A40,
        0x1E00,
        0xDEC1,
        0xDF81,
        0x1F40,
        0xDD01,
        0x1DC0,
        0x1C80,
        0xDC41,
        0x1400,
        0xD4C1,
        0xD581,
        0x1540,
        0xD701,
        0x17C0,
        0x1680,
        0xD641,
        0xD201,
        0x12C0,
        0x1380,
        0xD341,
        0x1100,
        0xD1C1,
        0xD081,
        0x1040,
        0xF001,
        0x30C0,
        0x3180,
        0xF141,
        0x3300,
        0xF3C1,
        0xF281,
        0x3240,
        0x3600,
        0xF6C1,
        0xF781,
        0x3740,
        0xF501,
        0x35C0,
        0x3480,
        0xF441,
        0x3C00,
        0xFCC1,
        0xFD81,
        0x3D40,
        0xFF01,
        0x3FC0,
        0x3E80,
        0xFE41,
        0xFA01,
        0x3AC0,
        0x3B80,
        0xFB41,
        0x3900,
        0xF9C1,
        0xF881,
        0x3840,
        0x2800,
        0xE8C1,
        0xE981,
        0x2940,
        0xEB01,
        0x2BC0,
        0x2A80,
        0xEA41,
        0xEE01,
        0x2EC0,
        0x2F80,
        0xEF41,
        0x2D00,
        0xEDC1,
        0xEC81,
        0x2C40,
        0xE401,
        0x24C0,
        0x2580,
        0xE541,
        0x2700,
        0xE7C1,
        0xE681,
        0x2640,
        0x2200,
        0xE2C1,
        0xE381,
        0x2340,
        0xE101,
        0x21C0,
        0x2080,
        0xE041,
        0xA001,
        0x60C0,
        0x6180,
        0xA141,
        0x6300,
        0xA3C1,
        0xA281,
        0x6240,
        0x6600,
        0xA6C1,
        0xA781,
        0x6740,
        0xA501,
        0x65C0,
        0x6480,
        0xA441,
        0x6C00,
        0xACC1,
        0xAD81,
        0x6D40,
        0xAF01,
        0x6FC0,
        0x6E80,
        0xAE41,
        0xAA01,
        0x6AC0,
        0x6B80,
        0xAB41,
        0x6900,
        0xA9C1,
        0xA881,
        0x6840,
        0x7800,
        0xB8C1,
        0xB981,
        0x7940,
        0xBB01,
        0x7BC0,
        0x7A80,
        0xBA41,
        0xBE01,
        0x7EC0,
        0x7F80,
        0xBF41,
        0x7D00,
        0xBDC1,
        0xBC81,
        0x7C40,
        0xB401,
        0x74C0,
        0x7580,
        0xB541,
        0x7700,
        0xB7C1,
        0xB681,
        0x7640,
        0x7200,
        0xB2C1,
        0xB381,
        0x7340,
        0xB101,
        0x71C0,
        0x7080,
        0xB041,
        0x5000,
        0x90C1,
        0x9181,
        0x5140,
        0x9301,
        0x53C0,
        0x5280,
        0x9241,
        0x9601,
        0x56C0,
        0x5780,
        0x9741,
        0x5500,
        0x95C1,
        0x9481,
        0x5440,
        0x9C01,
        0x5CC0,
        0x5D80,
        0x9D41,
        0x5F00,
        0x9FC1,
        0x9E81,
        0x5E40,
        0x5A00,
        0x9AC1,
        0x9B81,
        0x5B40,
        0x9901,
        0x59C0,
        0x5880,
        0x9841,
        0x8801,
        0x48C0,
        0x4980,
        0x8941,
        0x4B00,
        0x8BC1,
        0x8A81,
        0x4A40,
        0x4E00,
        0x8EC1,
        0x8F81,
        0x4F40,
        0x8D01,
        0x4DC0,
        0x4C80,
        0x8C41,
        0x4400,
        0x84C1,
        0x8581,
        0x4540,
        0x8701,
        0x47C0,
        0x4680,
        0x8641,
        0x8201,
        0x42C0,
        0x4380,
        0x8341,
        0x4100,
        0x81C1,
        0x8081,
        0x4040,
    ]

    @classmethod
    def crc16(cls, data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc = (crc >> 8) ^ cls.CRC16_TABLE[(crc ^ byte) & 0xFF]
        return crc

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
        if len(raw) < 4 + length:
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
        if rate == 0:
            command = CommandType.READ_SINGLE
        else:
            command = CommandType.READ_SINGLE + rate

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
