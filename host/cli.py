import click
import struct
import sys
from typing import Optional

from sparam import (
    SerialConnection,
    Device,
    ElfParser,
    DataType,
    Protocol,
)


@click.group()
@click.pass_context
def main(ctx):
    ctx.ensure_object(dict)


@main.command()
def list_ports():
    ports = SerialConnection.list_ports()
    for port in ports:
        click.echo(port)


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--prefix", "-p", default=None, help="Filter variables by prefix")
@click.option("--size", "-s", default=0, help="Filter by minimum size")
def parse_elf(filepath: str, prefix: Optional[str], size: int):
    parser = ElfParser()
    variables = parser.parse(filepath)

    if prefix:
        variables = [v for v in variables if v.name.startswith(prefix)]
    if size > 0:
        variables = [v for v in variables if v.size >= size]

    click.echo(f"Found {len(variables)} variables:")
    for v in variables:
        click.echo(
            f"  {v.name}: addr=0x{v.address:08X}, size={v.size}, type={v.var_type}"
        )


@main.command()
@click.option("--port", "-p", required=True, help="Serial port")
@click.option("--baud", "-b", default=115200, help="Baud rate")
@click.option("--device-id", "-d", default=1, help="Device ID")
@click.option("--timeout", "-t", default=1.0, help="Timeout in seconds")
def ping(port: str, baud: int, device_id: int, timeout: float):
    conn = SerialConnection(port, baud, timeout)
    if not conn.open():
        click.echo("Failed to open port", err=True)
        sys.exit(1)

    device = Device(conn, device_id)
    if device.ping(timeout):
        click.echo(f"Device {device_id} is online")
    else:
        click.echo(f"Device {device_id} is offline", err=True)
        sys.exit(1)

    conn.close()


@main.command()
@click.option("--port", "-p", required=True, help="Serial port")
@click.option("--baud", "-b", default=115200, help="Baud rate")
@click.option("--device-id", "-d", default=1, help="Device ID")
@click.option("--elf", "-e", required=True, help="ELF or MAP file path")
@click.option(
    "--var", "-v", multiple=True, required=True, help="Variable names to read"
)
@click.option("--timeout", "-t", default=1.0, help="Timeout in seconds")
def read(port: str, baud: int, device_id: int, elf: str, var: tuple, timeout: float):
    conn = SerialConnection(port, baud, timeout)
    if not conn.open():
        click.echo("Failed to open port", err=True)
        sys.exit(1)

    device = Device(conn, device_id)
    device.load_elf(elf)

    variables = []
    for name in var:
        v = device.get_variable(name)
        if v:
            variables.append(v)
        else:
            click.echo(f"Variable '{name}' not found", err=True)

    if not variables:
        click.echo("No valid variables", err=True)
        conn.close()
        sys.exit(1)

    results = device.read_single(variables, timeout)
    for name, value in results.items():
        v = device.get_variable(name)
        if v and v.dtype_code:
            try:
                dtype = DataType(v.dtype_code)
                val = struct.unpack(dtype.format_char, value)[0]
                click.echo(f"{name} = {val}")
            except:
                click.echo(f"{name} = {value.hex()}")
        else:
            click.echo(f"{name} = {value.hex()}")

    conn.close()


@main.command()
@click.option("--port", "-p", required=True, help="Serial port")
@click.option("--baud", "-b", default=115200, help="Baud rate")
@click.option("--device-id", "-d", default=1, help="Device ID")
@click.option("--elf", "-e", required=True, help="ELF or MAP file path")
@click.option("--var", "-v", required=True, help="Variable name to write")
@click.option("--value", required=True, type=float, help="Value to write")
@click.option(
    "--type",
    "-t",
    "var_type",
    default="float",
    type=click.Choice(["uint8", "int8", "uint16", "int16", "uint32", "int32", "float"]),
    help="Data type",
)
@click.option("--timeout", default=1.0, help="Timeout in seconds")
def write(
    port: str,
    baud: int,
    device_id: int,
    elf: str,
    var: str,
    value: float,
    var_type: str,
    timeout: float,
):
    type_map = {
        "uint8": DataType.UINT8,
        "int8": DataType.INT8,
        "uint16": DataType.UINT16,
        "int16": DataType.INT16,
        "uint32": DataType.UINT32,
        "int32": DataType.INT32,
        "float": DataType.FLOAT,
    }
    dtype = type_map[var_type]

    conn = SerialConnection(port, baud, timeout)
    if not conn.open():
        click.echo("Failed to open port", err=True)
        sys.exit(1)

    device = Device(conn, device_id)
    device.load_elf(elf)

    variable = device.get_variable(var)
    if not variable:
        click.echo(f"Variable '{var}' not found", err=True)
        conn.close()
        sys.exit(1)

    value_bytes = struct.pack(
        dtype.format_char, int(value) if dtype != DataType.FLOAT else value
    )

    if device.write_single(variable, value_bytes, timeout):
        click.echo(f"Written {value} to {var}")
    else:
        click.echo(f"Failed to write to {var}", err=True)
        sys.exit(1)

    conn.close()


@main.command()
@click.option("--port", "-p", required=True, help="Serial port")
@click.option("--baud", "-b", default=115200, help="Baud rate")
@click.option("--device-id", "-d", default=1, help="Device ID")
@click.option("--timeout", default=1.0, help="Timeout in seconds")
def stop(port: str, baud: int, device_id: int, timeout: float):
    conn = SerialConnection(port, baud, timeout)
    if not conn.open():
        click.echo("Failed to open port", err=True)
        sys.exit(1)

    conn.send(Protocol.encode_stop(device_id))
    click.echo("Stop command sent")
    conn.close()


@main.command()
@click.option("--port", "-p", required=True, help="Serial port")
@click.option("--baud", "-b", default=115200, help="Baud rate")
@click.option("--device-id", "-d", default=1, help="Device ID")
@click.option("--elf", "-e", required=True, help="ELF or MAP file path")
@click.option(
    "--var", "-v", multiple=True, required=True, help="Variable names to monitor"
)
@click.option(
    "--rate",
    "-r",
    default=3,
    type=click.IntRange(1, 8),
    help="Sample rate (1=1ms, 2=5ms, 3=10ms, 4=20ms, 5=50ms, 6=100ms, 7=200ms, 8=500ms)",
)
@click.option("--output", "-o", default=None, help="Output CSV file")
@click.option("--count", "-c", default=0, help="Number of samples (0 for infinite)")
def monitor(
    port: str,
    baud: int,
    device_id: int,
    elf: str,
    var: tuple,
    rate: int,
    output: Optional[str],
    count: int,
):
    import time
    import csv

    conn = SerialConnection(port, baud, 1.0)
    if not conn.open():
        click.echo("Failed to open port", err=True)
        sys.exit(1)

    device = Device(conn, device_id)
    device.load_elf(elf)

    variables = []
    for name in var:
        v = device.get_variable(name)
        if v:
            variables.append(v)
        else:
            click.echo(f"Variable '{name}' not found", err=True)

    if not variables:
        click.echo("No valid variables", err=True)
        conn.close()
        sys.exit(1)

    csv_file = None
    csv_writer = None
    if output:
        csv_file = open(output, "w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["timestamp"] + [v.name for v in variables])

    sample_count = 0
    running = True

    def on_data(name: str, value: bytes):
        nonlocal sample_count, running
        v = device.get_variable(name)
        if v and v.dtype_code:
            try:
                dtype = DataType(v.dtype_code)
                val = struct.unpack(dtype.format_char, value)[0]
                click.echo(f"{name} = {val}")
            except:
                click.echo(f"{name} = {value.hex()}")
        else:
            click.echo(f"{name} = {value.hex()}")

        sample_count += 1
        if count > 0 and sample_count >= count * len(variables):
            running = False

    conn.start_receive(lambda f: device.on_frame_received(f))

    if device.start_monitor(variables, rate, on_data):
        click.echo(f"Monitoring {len(variables)} variables at rate {rate}...")
        try:
            while running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            click.echo("\nStopping...")
        device.stop_monitor()
    else:
        click.echo("Failed to start monitoring", err=True)

    if csv_file:
        csv_file.close()
    conn.close()


if __name__ == "__main__":
    main()
