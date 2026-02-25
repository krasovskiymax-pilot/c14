"""
Диалог AI-ассистента для улучшения промтов.
"""
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLabel,
    QPushButton,
    QMessageBox,
    QProgressBar,
    QGroupBox,
    QWidget,
    QComboBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from models import get_active_models, Model
from prompt_assistant import improve_prompt, parse_improved_response


class ImprovePromptThread(QThread):
    """Поток улучшения промта."""
    finished = pyqtSignal(str)  # raw response
    error = pyqtSignal(str)

    def __init__(self, prompt_text: str, model: Model, parent=None):
        super().__init__(parent)
        self.prompt_text = prompt_text
        self.model = model

    def run(self):
        result = improve_prompt(self.prompt_text, self.model)
        if result.startswith(("Ошибка", "HTTP", "Переменная", "Таймаут")):
            self.error.emit(result)
        else:
            self.finished.emit(result)


class PromptImproveDialog(QDialog):
    """Диалог улучшения промта."""

    def __init__(self, parent=None, original_text: str = "", on_substitute=None):
        super().__init__(parent)
        self.original_text = original_text
        self.on_substitute = on_substitute  # callback(text) для подстановки в поле
        self.parsed: dict = {}
        self._models: list[Model] = []
        self.setWindowTitle("Улучшить промт")
        self.setMinimumSize(550, 450)
        self.resize(650, 550)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Выбор модели и кнопка «Улучшить»
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Модель:"))
        self.model_combo = QComboBox()
        self._models = get_active_models()
        for m in self._models:
            self.model_combo.addItem(m.name, m)
        self.model_combo.setMinimumWidth(200)
        model_row.addWidget(self.model_combo, 0)
        improve_btn = QPushButton("Улучшить")
        improve_btn.clicked.connect(self._on_improve_clicked)
        model_row.addWidget(improve_btn)
        model_row.addStretch()
        layout.addLayout(model_row)

        # Исходный промт
        g_orig = QGroupBox("Исходный промт")
        lo = QVBoxLayout(g_orig)
        self.original_edit = QTextEdit()
        self.original_edit.setPlainText(self.original_text)
        self.original_edit.setReadOnly(True)
        self.original_edit.setMaximumHeight(80)
        lo.addWidget(self.original_edit)
        layout.addWidget(g_orig)

        # Статус / результат
        self.status_label = QLabel("Выберите модель и нажмите «Улучшить».")
        layout.addWidget(self.status_label)
        self.progress = QProgressBar()
        self.progress.setMaximum(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Улучшенный и варианты
        g_improved = QGroupBox("Улучшенный промт")
        li = QVBoxLayout(g_improved)
        self.improved_edit = QTextEdit()
        self.improved_edit.setReadOnly(True)
        self.improved_edit.setPlaceholderText("Ожидайте ответ модели…")
        self.improved_edit.setMinimumHeight(80)
        li.addWidget(self.improved_edit)
        layout.addWidget(g_improved)

        g_alt = QGroupBox("Альтернативные варианты")
        la = QVBoxLayout(g_alt)
        self.alternatives_widget = QWidget()
        self.alternatives_layout = QVBoxLayout(self.alternatives_widget)
        la.addWidget(self.alternatives_widget)
        layout.addWidget(g_alt)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.substitute_btn = QPushButton("Подставить в поле ввода")
        self.substitute_btn.clicked.connect(self._on_substitute)
        self.substitute_btn.setEnabled(False)
        btn_layout.addWidget(self.substitute_btn)
        btn_layout.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _on_improve_clicked(self):
        if not self.original_text.strip():
            return
        model = self.model_combo.currentData()
        if not model:
            QMessageBox.warning(self, "Ошибка", "Нет активных моделей. Добавьте модели в Настройки → Модели.")
            return
        self.status_label.setText(f"Запрос к {model.name}…")
        self.progress.setVisible(True)
        self.model_combo.setEnabled(False)
        self._thread = ImprovePromptThread(self.original_text, model, self)
        self._thread.finished.connect(self._on_finished)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_finished(self, text: str):
        self.progress.setVisible(False)
        self.model_combo.setEnabled(True)
        self.parsed = parse_improved_response(text)
        self.improved_edit.setPlainText(self.parsed.get("improved", text))
        self.status_label.setText("Готово")

        # Альтернативы — очистить старые
        while self.alternatives_layout.count():
            item = self.alternatives_layout.takeAt(0)
            if item.layout():
                self._clear_layout(item.layout())
            if item.widget():
                item.widget().deleteLater()
        for i, alt in enumerate(self.parsed.get("alternatives", [])[:3], 1):
            row = QHBoxLayout()
            lbl = QLabel(f"Вариант {i}:")
            lbl.setMinimumWidth(70)
            row.addWidget(lbl)
            te = QTextEdit()
            te.setPlainText(alt)
            te.setReadOnly(True)
            te.setMaximumHeight(60)
            te.setObjectName(f"alt_{i}")
            row.addWidget(te, 1)
            sub_btn = QPushButton("Подставить")
            sub_btn.clicked.connect(lambda checked=False, t=alt: self._substitute_text(t))
            row.addWidget(sub_btn)
            self.alternatives_layout.addLayout(row)
        self.substitute_btn.setEnabled(bool(self.parsed.get("improved")))

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _on_error(self, msg: str):
        self.progress.setVisible(False)
        self.model_combo.setEnabled(True)
        self.status_label.setText("Ошибка")
        self.improved_edit.setPlainText(msg)
        QMessageBox.warning(self, "Ошибка", msg)

    def _on_substitute(self):
        t = self.parsed.get("improved", "").strip()
        if t and self.on_substitute:
            self.on_substitute(t)
        self.accept()

    def _substitute_text(self, text: str):
        if text and self.on_substitute:
            self.on_substitute(text)
        self.accept()
