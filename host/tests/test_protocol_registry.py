import pytest

from sparam.protocol import (
    C_TYPE_TO_DATA_TYPE,
    CLI_TYPE_TO_DATA_TYPE,
    MAX_MONITOR_RATE,
    MIN_MONITOR_RATE,
    READ_RATE_TO_COMMAND,
    DataType,
    is_read_command,
    is_stream_read_command,
    read_command_for_rate,
)


def test_read_command_registry_covers_monitor_rates() -> None:
    assert MIN_MONITOR_RATE == 1
    assert MAX_MONITOR_RATE == 8

    for rate in range(0, MAX_MONITOR_RATE + 1):
        assert read_command_for_rate(rate) == READ_RATE_TO_COMMAND[rate]


@pytest.mark.parametrize("rate", [-1, 9, 99])
def test_read_command_registry_rejects_unknown_rate(rate: int) -> None:
    with pytest.raises(ValueError):
        read_command_for_rate(rate)


def test_data_type_registries_align_for_cli_and_c_aliases() -> None:
    assert CLI_TYPE_TO_DATA_TYPE["float"] == DataType.FLOAT
    assert CLI_TYPE_TO_DATA_TYPE["uint32"] == DataType.UINT32

    assert C_TYPE_TO_DATA_TYPE["uint32_t"] == DataType.UINT32
    assert C_TYPE_TO_DATA_TYPE["unsigned char"] == DataType.UINT8


def test_read_command_classification_helpers() -> None:
    assert is_read_command(int(read_command_for_rate(0)))
    assert is_stream_read_command(int(read_command_for_rate(1)))
    assert not is_stream_read_command(int(read_command_for_rate(0)))


def test_data_type_size_and_format_are_registry_backed() -> None:
    assert DataType.UINT16.size == 2
    assert DataType.UINT16.format_char == "<H"
    assert DataType.FLOAT.size == 4
    assert DataType.FLOAT.format_char == "<f"
