# sparam host

Python host tools for sparam, including protocol encoding/decoding, device communication, ELF parsing, and CLI utilities.

## Development

- Install dependencies (core + test + gui): `uv sync --extra test --extra gui`
- Run tests: `uv run --extra test pytest -q`

## GUI (PySide6)

- If you already ran `uv sync` only, add GUI deps with: `uv sync --extra gui`
- Launch GUI by script: `uv run sparam-gui`
- Or launch from CLI command: `uv run sparam gui`

The GUI currently supports:

- Serial port connect/disconnect + device ping
- Offline symbol parsing (load `.elf` / `.out` / `.map` without serial device)
- Load `.elf` / `.out` / `.map` symbol files
- Variable list and prefix filter
- Read selected variable value
- Write selected variable value with explicit data type
