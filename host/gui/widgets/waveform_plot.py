from typing import Dict, List, Optional

import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class WaveformPlot(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("plotPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Signal Canvas")
        title.setProperty("sectionTitle", True)
        subtitle = QLabel(
            "Overlayed monitor stream with a restrained time window and subdued grid"
        )
        subtitle.setProperty("muted", True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#fbfaf7")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.08)
        self.plot_widget.setLabel("left", "Value")
        self.plot_widget.setLabel("bottom", "Time", units="s")
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.hideButtons()
        self.plot_widget.addLegend(offset=(10, 10), labelTextSize="10pt")
        self.plot_widget.getAxis("left").setTextPen("#777064")
        self.plot_widget.getAxis("bottom").setTextPen("#777064")
        self.plot_widget.getAxis("left").setPen("#d7d1c7")
        self.plot_widget.getAxis("bottom").setPen("#d7d1c7")
        self.plot_widget.getPlotItem().layout.setContentsMargins(12, 8, 12, 8)
        layout.addWidget(self.plot_widget)

        self._curves: Dict[str, pg.PlotCurveItem] = {}
        self._timestamps: Dict[str, List[float]] = {}
        self._values: Dict[str, List[float]] = {}
        self._time_window: Optional[float] = 10.0
        self._paused = False

    def add_variable(self, name: str, color: str) -> None:
        if name in self._curves:
            return
        curve = self.plot_widget.plot(name=name, pen=pg.mkPen(color=color, width=1.35))
        self._curves[name] = curve
        self._timestamps[name] = []
        self._values[name] = []

    def remove_variable(self, name: str) -> None:
        curve = self._curves.pop(name, None)
        if curve is not None:
            self.plot_widget.removeItem(curve)
        self._timestamps.pop(name, None)
        self._values.pop(name, None)

    def update_data(self, name: str, timestamp: float, value: float) -> None:
        if self._paused or name not in self._curves:
            return

        timestamps = self._timestamps[name]
        values = self._values[name]
        timestamps.append(timestamp)
        values.append(value)

        if self._time_window is not None:
            cutoff = timestamp - self._time_window
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)
                values.pop(0)

        if not timestamps:
            return

        origin = timestamps[0]
        self._curves[name].setData(
            [item - origin for item in timestamps],
            values,
        )

    def set_time_window(self, seconds: Optional[float]) -> None:
        self._time_window = seconds

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def export_png(self, filepath: str) -> None:
        exporter = ImageExporter(self.plot_widget.plotItem)
        exporter.export(filepath)
