from dataclasses import dataclass, field
from typing import List


@dataclass
class MonitorState:
    monitored_names: List[str] = field(default_factory=list)
    active: bool = False
    paused: bool = False

    def add_monitored(self, name: str) -> bool:
        if name in self.monitored_names:
            return False
        self.monitored_names.append(name)
        return True

    def remove_monitored(self, name: str) -> bool:
        if name not in self.monitored_names:
            return False
        self.monitored_names = [item for item in self.monitored_names if item != name]
        return True

    def clear_monitored(self) -> None:
        self.monitored_names = []

    def series_index(self, name: str) -> int:
        if name in self.monitored_names:
            return self.monitored_names.index(name)
        return len(self.monitored_names)

    def toggle_paused(self) -> bool:
        self.paused = not self.paused
        return self.paused

    def set_active(self, active: bool) -> None:
        self.active = active

    def stop_streaming(self) -> None:
        self.active = False

    def reset(self) -> None:
        self.active = False
        self.paused = False
        self.monitored_names = []
