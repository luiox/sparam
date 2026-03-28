import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Optional

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .styles.catppuccin import build_stylesheet


def _runtime_log_path() -> Path:
    return Path.cwd() / "sparam_gui_runtime.log"


def _append_runtime_log(line: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _runtime_log_path().open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {line}\n")


def _install_runtime_diagnostics() -> None:
    def _excepthook(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: Optional[TracebackType],
    ) -> None:
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        _append_runtime_log("UNCAUGHT PYTHON EXCEPTION")
        for line in text.rstrip().splitlines():
            _append_runtime_log(line)
        print(text, file=sys.stderr, flush=True)

    sys.excepthook = _excepthook

    def _qt_message_handler(
        mode: QtMsgType,
        _context: object,
        message: str,
    ) -> None:
        level_map = {
            QtMsgType.QtDebugMsg: "DEBUG",
            QtMsgType.QtInfoMsg: "INFO",
            QtMsgType.QtWarningMsg: "WARN",
            QtMsgType.QtCriticalMsg: "CRITICAL",
            QtMsgType.QtFatalMsg: "FATAL",
        }
        level = level_map.get(mode, "UNKNOWN")
        _append_runtime_log(f"QT {level}: {message}")

    qInstallMessageHandler(_qt_message_handler)


def run_gui() -> None:
    # Never treat Qt warnings as process-fatal in end-user GUI runs.
    os.environ.pop("QT_FATAL_WARNINGS", None)
    _install_runtime_diagnostics()

    app = QApplication(sys.argv)
    app.setStyleSheet(build_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
