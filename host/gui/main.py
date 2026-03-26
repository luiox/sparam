import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .styles.catppuccin import build_stylesheet


def run_gui() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
