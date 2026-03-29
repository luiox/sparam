from sparam.protocol import CommandType, Protocol


def test_protocol_roundtrip_empty_payload() -> None:
    frame_bytes = Protocol.encode(1, CommandType.ACK)
    decoded = Protocol.decode(frame_bytes)

    assert decoded is not None
    assert decoded.device_id == 1
    assert decoded.command == CommandType.ACK
    assert decoded.data == b""


def test_protocol_decode_rejects_crc_mismatch() -> None:
    frame_bytes = bytearray(Protocol.encode(1, CommandType.HEARTBEAT))
    frame_bytes[-1] ^= 0xFF

    assert Protocol.decode(bytes(frame_bytes)) is None


def test_protocol_decode_rejects_incomplete_frame() -> None:
    frame_bytes = Protocol.encode(1, CommandType.HEARTBEAT)

    assert Protocol.decode(frame_bytes[:-1]) is None


def test_protocol_decode_rejects_invalid_header() -> None:
    frame_bytes = bytearray(Protocol.encode(1, CommandType.HEARTBEAT))
    frame_bytes[0] = 0xAB

    assert Protocol.decode(bytes(frame_bytes)) is None
