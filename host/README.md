# sparam host

Python host tools for sparam, including protocol encoding/decoding, device communication, ELF parsing, and CLI utilities.

## Development

- Install dependencies (core + dev + test + gui): `uv sync --extra dev --extra test --extra gui`
- Format code: `uv run --extra dev ruff format .`
- Run linter: `uv run --extra dev ruff check .`
- Run type checks: `uv run --extra dev mypy cli.py gui sparam tests`
- Run tests: `uv run --extra test pytest -q`
- Run the full local quality gate:
  `uv run --extra dev ruff format . && uv run --extra dev ruff check . && uv run --extra dev mypy cli.py gui sparam tests && uv run --extra test pytest -q`

## GUI (PySide6)

- If you already ran `uv sync` only, add GUI deps with: `uv sync --extra gui`
- Launch GUI by script: `uv run sparam-gui`
- Or launch from CLI command: `uv run sparam gui`
- Launch the synthetic preview window: `uv run --extra gui sparam-gui-mock`

The GUI currently supports:

- Serial port connect/disconnect + device ping
- Offline symbol parsing (load `.elf` / `.out` / `.map` without serial device)
- Load `.elf` / `.out` / `.map` symbol files
- Variable list and prefix filter
- One-shot read for selected variable (`Read Once`)
- One-shot write for selected variable with explicit data type (`Write Once`)
- Variable monitor add by double-click and explicit remove via `Remove Selected`
- Dock-based layout: left Sidebar / center waveform / right Inspector
- Persistent window layout across restarts (dock position and size)
