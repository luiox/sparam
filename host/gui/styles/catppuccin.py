PAGE_BG = "#f2f1ee"
SHELL_BG = "#ebe8e2"
PANEL_BG = "#f7f5f1"
CARD_BG = "#fbfaf7"
INPUT_BG = "#f1eee8"
BORDER = "#ddd7ce"
BORDER_STRONG = "#cbc3b7"
TEXT = "#28241f"
MUTED = "#777064"
ACCENT = "#2f2b27"
ACCENT_SOFT = "#e7e2d8"
SUCCESS = "#5d8a68"
WARNING = "#a07b32"
ERROR = "#b86a63"

SERIES_COLORS = [
    "#2563eb",
    "#0f766e",
    "#8b5cf6",
    "#c97a2b",
    "#4b5563",
]


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        background: {PAGE_BG};
        color: {TEXT};
        font-family: Monospace;
        font-size: 9pt;
    }}
    QMainWindow {{
        background: {PAGE_BG};
    }}
    QWidget#workspaceShell {{
        background: transparent;
    }}
    QFrame#toolbar {{
        background: {PANEL_BG};
        border: 1px solid {BORDER};
        border-radius: 0px;
    }}
    QDockWidget {{
        background: {PANEL_BG};
        border: 1px solid {BORDER};
        border-radius: 0px;
    }}
    QDockWidget::title {{
        background: {PANEL_BG};
        border: 1px solid {BORDER};
        border-bottom: none;
        border-radius: 0px;
        padding: 4px 8px;
        text-transform: uppercase;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1px;
    }}
    QFrame#sidebar {{
        background: {SHELL_BG};
        border: 1px solid {BORDER};
        border-radius: 0px;
    }}
    QFrame#sectionCard,
    QFrame#summaryCard,
    QFrame#signalStatsStrip,
    QFrame#inspectorPanel,
    QWidget#plotPanel,
    QFrame#valueCard,
    QFrame#logPanel {{
        background: {PANEL_BG};
        border: 1px solid {BORDER};
        border-radius: 0px;
    }}
    QFrame#summaryCard,
    QFrame#logPanel,
    QFrame#valueCard {{
        background: {CARD_BG};
    }}
    QListWidget,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QSpinBox,
    QPushButton {{
        background: {INPUT_BG};
        color: {TEXT};
        border: 1px solid {BORDER};
        border-radius: 0px;
        padding: 5px 8px;
    }}
    QLineEdit,
    QComboBox,
    QSpinBox {{
        min-height: 16px;
    }}
    QPushButton {{
        font-weight: 600;
    }}
    QPushButton[micro="true"] {{
        padding: 2px 6px;
        min-height: 0px;
        font-size: 10px;
        font-weight: 700;
    }}
    QPushButton:hover {{
        background: {CARD_BG};
        border-color: {BORDER_STRONG};
    }}
    QPushButton[accent="true"] {{
        background: {ACCENT};
        color: {CARD_BG};
        border-color: {ACCENT};
    }}
    QPushButton:pressed {{
        background: {ACCENT_SOFT};
    }}
    QPushButton[accent="true"]:pressed {{
        background: #1f1c19;
    }}
    QLabel[muted="true"] {{
        color: {MUTED};
    }}
    QLabel[hero="true"] {{
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.4px;
    }}
    QLabel[sectionTitle="true"] {{
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.0px;
        text-transform: uppercase;
        color: {TEXT};
    }}
    QLabel[chip="true"] {{
        background: {INPUT_BG};
        border: 1px solid {BORDER};
        border-radius: 0px;
        padding: 3px 8px;
        font-size: 10px;
        font-weight: 700;
    }}
    QLabel[chip="true"][state="connected"] {{
        color: {SUCCESS};
        border-color: #d5dfd6;
        background: #f3f7f3;
    }}
    QLabel[chip="true"][state="warning"] {{
        color: {WARNING};
        border-color: #e4d8bd;
        background: #faf6eb;
    }}
    QLabel[chip="true"][state="idle"] {{
        color: {MUTED};
    }}
    QListWidget {{
        outline: none;
    }}
    QListWidget::item {{
        padding: 6px 6px;
        border-radius: 0px;
        margin: 1px 0;
    }}
    QListWidget::item:selected {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        color: {TEXT};
    }}
    QTextEdit {{
        background: transparent;
        border: none;
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QComboBox::drop-down,
    QSpinBox::up-button,
    QSpinBox::down-button {{
        border: none;
        background: transparent;
        width: 16px;
    }}
    QSplitter::handle {{
        background: transparent;
        width: 8px;
    }}
    """
