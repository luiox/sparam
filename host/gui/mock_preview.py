import math
import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from sparam.elf_parser import Variable

from .main_window import MainWindow
from .styles.catppuccin import build_stylesheet


class MockPreviewController:
    def __init__(self, window: MainWindow) -> None:
        self.window = window
        self.start_time = time.time()
        self.tick = 0
        self.variables = [
            Variable("motor_speed", 0x20000000, 4, "uint32_t"),
            Variable("motor_current", 0x20000004, 4, "uint32_t"),
            Variable("pid_kp", 0x20000008, 4, "float"),
        ]
        self.timer = QTimer(window)
        self.timer.timeout.connect(self.push_samples)
        self._setup_window()

    def _setup_window(self) -> None:
        self.window.parser.variables = {item.name: item for item in self.variables}
        self.window.sidebar.set_variables(self.variables)
        self.window.toolbar.set_preview()
        self.window.toolbar.set_status_text(
            "Mock preview mode: synthetic waveform data"
        )
        self.window._log("Loaded mock variables for UI preview.")
        for variable in self.variables:
            self.window._toggle_variable_monitor(variable.name)
        self.window.monitor_active = True
        self.window._log("Mock preview stream started.")

    def start(self) -> None:
        self.timer.start(50)

    def push_samples(self) -> None:
        elapsed = time.time() - self.start_time
        self.tick += 1
        speed = 1200 + 280 * math.sin(elapsed * 1.7) + (self.tick % 6) * 4
        current = 42 + 9 * math.sin(elapsed * 2.4 + 0.6)
        kp = 1.5 + 0.08 * math.sin(elapsed * 0.45)

        self.window._on_sample_received("motor_speed", time.time(), float(speed))
        self.window._on_sample_received("motor_current", time.time(), float(current))
        self.window._on_sample_received("pid_kp", time.time(), float(kp))


def run_mock_preview() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet())
    window = MainWindow()
    controller = MockPreviewController(window)
    controller.start()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_mock_preview()
