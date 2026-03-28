import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import SkipTest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_main_window_exposes_signal_lab_layout() -> None:
    if importlib.util.find_spec("PySide6") is None:
        raise SkipTest("PySide6 is not installed")
    if importlib.util.find_spec("pyqtgraph") is None:
        raise SkipTest("pyqtgraph is not installed")

    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtWidgets import QApplication, QDockWidget, QWidget

    from gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as temp_dir:
        settings = QSettings(
            str(Path(temp_dir) / "layout.ini"),
            QSettings.Format.IniFormat,
        )
        settings.clear()
        window = MainWindow(settings=settings)

        assert window.findChild(QWidget, "workspaceShell") is not None
        assert window.findChild(QWidget, "inspectorPanel") is not None
        assert window.findChild(QWidget, "signalStatsStrip") is not None
        assert hasattr(window.sidebar, "read_once_btn")
        assert hasattr(window.sidebar, "write_once_btn")
        assert hasattr(window.sidebar, "remove_var_btn")

        sidebar_dock = window.findChild(QDockWidget, "sidebarDock")
        inspector_dock = window.findChild(QDockWidget, "inspectorDock")
        assert sidebar_dock is not None
        assert inspector_dock is not None
        assert (
            window.dockWidgetArea(sidebar_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
        )
        assert (
            window.dockWidgetArea(inspector_dock)
            == Qt.DockWidgetArea.RightDockWidgetArea
        )

        window.close()
    app.quit()


def test_main_window_persists_dock_layout() -> None:
    if importlib.util.find_spec("PySide6") is None:
        raise SkipTest("PySide6 is not installed")
    if importlib.util.find_spec("pyqtgraph") is None:
        raise SkipTest("pyqtgraph is not installed")

    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtWidgets import QApplication

    from gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as temp_dir:
        settings = QSettings(
            str(Path(temp_dir) / "persist-layout.ini"),
            QSettings.Format.IniFormat,
        )
        settings.clear()

        first = MainWindow(settings=settings)
        first.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, first.sidebar_dock)
        first.close()

        second = MainWindow(settings=settings)
        assert (
            second.dockWidgetArea(second.sidebar_dock)
            == Qt.DockWidgetArea.RightDockWidgetArea
        )
        second.close()

    app.quit()
