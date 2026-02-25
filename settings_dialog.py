"""
Диалог настроек программы.
Тема (светлая/тёмная), размер шрифта. Сохраняет в таблицу settings.
"""
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QPushButton,
    QFormLayout,
    QGroupBox,
)
from PyQt5.QtCore import Qt

import db

THEME_LIGHT = "light"
THEME_DARK = "dark"
SETTING_THEME = "theme"
SETTING_FONT_SIZE = "font_size"
DEFAULT_FONT_SIZE = 10


def get_theme() -> str:
    """Возвращает сохранённую тему: light или dark."""
    v = db.setting_get(SETTING_THEME)
    return v if v in (THEME_LIGHT, THEME_DARK) else THEME_LIGHT


def get_font_size() -> int:
    """Возвращает сохранённый размер шрифта."""
    v = db.setting_get(SETTING_FONT_SIZE)
    try:
        n = int(v)
        return max(8, min(24, n))
    except (TypeError, ValueError):
        return DEFAULT_FONT_SIZE


# Стили для тёмной темы
DARK_STYLESHEET = """
    QMainWindow, QDialog, QWidget {
        background-color: #2b2b2b;
        color: #e0e0e0;
    }
    QLabel, QCheckBox, QGroupBox {
        color: #e0e0e0;
    }
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
        background-color: #3c3f41;
        color: #e0e0e0;
        border: 1px solid #555;
    }
    QTextBrowser {
        background-color: #3c3f41;
        color: #e0e0e0;
    }
    QPushButton {
        background-color: #4a4a4a;
        color: #e0e0e0;
        border: 1px solid #555;
    }
    QPushButton:hover {
        background-color: #5a5a5a;
    }
    QTableWidget {
        background-color: #3c3f41;
        color: #e0e0e0;
        gridline-color: #555;
    }
    QTableWidget::item {
        color: #e0e0e0;
    }
    QHeaderView::section {
        background-color: #4a4a4a;
        color: #e0e0e0;
    }
    QProgressBar {
        background-color: #3c3f41;
    }
    QProgressBar::chunk {
        background-color: #0d47a1;
    }
    QMenuBar {
        background-color: #2b2b2b;
        color: #e0e0e0;
    }
    QMenuBar::item:selected {
        background-color: #4a4a4a;
    }
    QStatusBar {
        background-color: #2b2b2b;
        color: #a0a0a0;
    }
"""


class SettingsDialog(QDialog):
    """Диалог настроек: тема и размер шрифта."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumSize(350, 180)
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        g = QGroupBox("Внешний вид")
        form = QFormLayout(g)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Светлая", THEME_LIGHT)
        self.theme_combo.addItem("Тёмная", THEME_DARK)
        form.addRow("Тема:", self.theme_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setSuffix(" pt")
        form.addRow("Размер шрифта панелей:", self.font_size_spin)

        layout.addWidget(g)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _load_values(self):
        theme = get_theme()
        idx = self.theme_combo.findData(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.font_size_spin.setValue(get_font_size())

    def _on_ok(self):
        theme = self.theme_combo.currentData()
        font_size = self.font_size_spin.value()
        db.setting_set(SETTING_THEME, theme)
        db.setting_set(SETTING_FONT_SIZE, str(font_size))
        self.accept()
