BACKGROUND = "#f3f4f6"
SIDEBAR = "#f8fafc"
CARD = "#fcfcfd"
CARD_ALT = "#f8fafc"
INPUT_BG = "#f8fafb"
BORDER = "#e5e7eb"
TEXT = "#111827"
MUTED = "#6b7280"
ACCENT = "#1f2937"
SUCCESS = "#4b7a5a"
WARNING = "#9a6b16"
ERROR = "#b25d5d"

SERIES_COLORS = [
    "#2563eb",
    "#0f766e",
    "#7c3aed",
    "#ea580c",
    "#dc2626",
]


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        background: {BACKGROUND};
        color: {TEXT};
        font-family: Monospace;
        font-size: 13px;
    }}
    QMainWindow {{
        background: {BACKGROUND};
    }}
    QFrame#toolbar,
    QFrame#sidebar,
    QFrame#sectionCard,
    QFrame#summaryCard,
    QWidget#plotPanel,
    QFrame#cardShelf,
    QFrame#valueCard,
    QFrame#logPanel {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 8px;
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
        border-radius: 6px;
        padding: 7px 10px;
    }}
    QPushButton:hover {{
        background: {CARD_ALT};
        border-color: #d1d5db;
    }}
    QPushButton[accent="true"] {{
        background: {ACCENT};
        color: {CARD};
        border-color: {ACCENT};
        font-weight: 700;
    }}
    QPushButton:pressed {{
        background: #eef2f7;
    }}
    QPushButton[accent="true"]:pressed {{
        background: #374151;
    }}
    QPushButton[semantic="success"] {{
        color: {SUCCESS};
    }}
    QPushButton[semantic="warning"] {{
        color: {WARNING};
    }}
    QPushButton[semantic="error"] {{
        color: {ERROR};
    }}
    QLabel[muted="true"] {{
        color: {MUTED};
    }}
    QLabel[hero="true"] {{
        font-size: 24px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    QLabel[chip="true"] {{
        background: {INPUT_BG};
        border: 1px solid {BORDER};
        border-radius: 999px;
        padding: 4px 10px;
        font-size: 12px;
    }}
    QLabel[chip="true"][state="connected"] {{
        color: {SUCCESS};
        border-color: #d6eadc;
    }}
    QLabel[chip="true"][state="warning"] {{
        color: {WARNING};
        border-color: #eadcb6;
    }}
    QLabel[sectionTitle="true"] {{
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }}
    QListWidget::item:selected {{
        background: {CARD_ALT};
        border: 1px solid {BORDER};
        color: {TEXT};
        border-radius: 4px;
    }}
    QListWidget::item {{
        padding: 6px 8px;
    }}
    QScrollArea {{
        border: none;
    }}
    QComboBox::drop-down,
    QSpinBox::up-button,
    QSpinBox::down-button {{
        border: none;
        background: transparent;
    }}
    QSplitter::handle {{
        background: {BACKGROUND};
        width: 8px;
    }}
    """
