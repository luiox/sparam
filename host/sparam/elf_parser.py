import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Variable:
    name: str
    address: int
    size: int
    var_type: str

    @property
    def dtype_code(self) -> int:
        type_map = {
            "uint8_t": 0x01,
            "int8_t": 0x02,
            "uint16_t": 0x03,
            "int16_t": 0x04,
            "uint32_t": 0x05,
            "int32_t": 0x06,
            "float": 0x07,
            "unsigned char": 0x01,
            "signed char": 0x02,
            "unsigned short": 0x03,
            "short": 0x04,
            "unsigned int": 0x05,
            "int": 0x06,
        }
        return type_map.get(self.var_type, 0x05)


class ElfParser:
    def __init__(self) -> None:
        self.variables: Dict[str, Variable] = {}

    def parse_elf(self, filepath: str) -> List[Variable]:
        try:
            from elftools.elf.elffile import ELFFile
        except ImportError as exc:
            raise ImportError("pyelftools is required: pip install pyelftools") from exc

        self.variables.clear()

        with open(filepath, "rb") as f:
            elf = ELFFile(f)

            for section in elf.iter_sections():
                if section.name in [".data", ".bss", ".noinit"]:
                    self._parse_section_symbols(elf, section)

        return list(self.variables.values())

    def _parse_section_symbols(self, elf: Any, section: Any) -> None:
        from elftools.elf.sections import SymbolTableSection

        for s in elf.iter_sections():
            if isinstance(s, SymbolTableSection):
                for sym in s.iter_symbols():
                    if sym["st_shndx"] == "SHN_UNDEF":
                        continue
                    if sym["st_shndx"] == "SHN_ABS":
                        continue

                    try:
                        sym_section = elf.get_section(sym["st_shndx"])
                        if sym_section.name not in [".data", ".bss", ".noinit"]:
                            continue
                    except Exception:
                        continue

                    name = sym.name
                    if not name or name.startswith("_"):
                        continue

                    addr = sym["st_value"]
                    size = sym["st_size"]

                    if addr == 0 or size == 0:
                        continue

                    var_type = self._guess_type(size)
                    self.variables[name] = Variable(
                        name=name,
                        address=addr,
                        size=size,
                        var_type=var_type,
                    )

    def _guess_type(self, size: int) -> str:
        type_map = {1: "uint8_t", 2: "uint16_t", 4: "uint32_t", 8: "uint64_t"}
        return type_map.get(size, f"uint8_t[{size}]")

    def parse_map(self, filepath: str) -> List[Variable]:
        self.variables.clear()

        with open(filepath, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        patterns = [
            r"^\s*(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(\w+)\s*$",
            r"^\s*(\w+)\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s*$",
        ]

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    groups = match.groups()
                    if groups[0].startswith("0x"):
                        addr = int(groups[0], 16)
                        size = int(groups[1], 16)
                        name = groups[2]
                    else:
                        name = groups[0]
                        addr = int(groups[1], 16)
                        size = int(groups[2], 16)

                    if addr == 0 or size == 0:
                        continue

                    if name.startswith("_"):
                        continue

                    var_type = self._guess_type(size)
                    self.variables[name] = Variable(
                        name=name,
                        address=addr,
                        size=size,
                        var_type=var_type,
                    )
                    break

        return list(self.variables.values())

    def parse(self, filepath: str) -> List[Variable]:
        if filepath.endswith(".elf") or filepath.endswith(".out"):
            return self.parse_elf(filepath)
        elif filepath.endswith(".map"):
            return self.parse_map(filepath)
        else:
            raise ValueError(f"Unsupported file format: {filepath}")

    def get_variable(self, name: str) -> Optional[Variable]:
        return self.variables.get(name)

    def filter_variables(
        self, prefix: Optional[str] = None, min_size: int = 0, max_size: int = 0
    ) -> List[Variable]:
        result = list(self.variables.values())

        if prefix:
            result = [v for v in result if v.name.startswith(prefix)]

        if min_size > 0:
            result = [v for v in result if v.size >= min_size]

        if max_size > 0:
            result = [v for v in result if v.size <= max_size]

        return result
