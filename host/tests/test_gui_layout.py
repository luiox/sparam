import importlib.util
import sys
from pathlib import Path
from unittest import SkipTest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_main_window_exposes_signal_lab_layout() -> None:
    if importlib.util.find_spec("PySide6") is None:
        raise SkipTest("PySide6 is not installed")
    if importlib.util.find_spec("pyqtgraph") is None:
        raise SkipTest("pyqtgraph is not installed")

    from PySide6.QtWidgets import QApplication

    from gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert window.findChild(type(window.centralWidget()), "workspaceShell") is not None
    assert window.findChild(type(window.centralWidget()), "inspectorPanel") is not None
    assert (
        window.findChild(type(window.centralWidget()), "signalStatsStrip") is not None
    )

    window.close()
    app.quit()
