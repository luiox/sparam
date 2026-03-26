from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Tuple


@dataclass
class TimeSeries:
    timestamps: List[float]
    values: List[float]


class MonitorStore:
    def __init__(self, max_points: int = 1000):
        self.max_points = max_points
        self._timestamps: Dict[str, Deque[float]] = {}
        self._values: Dict[str, Deque[float]] = {}

    def append(self, name: str, timestamp: float, value: float) -> None:
        if name not in self._timestamps:
            self._timestamps[name] = deque(maxlen=self.max_points)
            self._values[name] = deque(maxlen=self.max_points)

        self._timestamps[name].append(timestamp)
        self._values[name].append(value)

    def series(self, name: str) -> TimeSeries:
        return TimeSeries(
            timestamps=list(self._timestamps.get(name, [])),
            values=list(self._values.get(name, [])),
        )

    def latest_value(self, name: str):
        values = self._values.get(name)
        if not values:
            return None
        return values[-1]

    def export_rows(self) -> List[Tuple[float, str, float]]:
        rows: List[Tuple[float, str, float]] = []
        for name in self._timestamps:
            timestamps = self._timestamps[name]
            values = self._values[name]
            rows.extend(zip(timestamps, [name] * len(timestamps), values))
        rows.sort(key=lambda item: item[0])
        return rows
