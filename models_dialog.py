"""
Диалог настройки моделей нейросетей.
"""
from typing import Optional

import requests
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QMessageBox,
    QAbstractItemView,
    QWidget,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QLabel,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl

import db
from models import get_all_models, add_model, update_model, delete_model, get_model, get_api_key


def _is_free_model(pricing: dict) -> bool:
    """Проверяет, бесплатна ли модель (0 за ввод и вывод)."""
    if not pricing:
        return False
    prompt = pricing.get("prompt")
    completion = pricing.get("completion")
    # Структура может быть: число, строка, или объект с полем внутри
    def _zero(v) -> bool:
        if v is None:
            return True
        if isinstance(v, (int, float)):
            return v == 0
        if isinstance(v, dict):
            # Вложенная структура: {"price_per_token": 0}
            ppt = v.get("price_per_token", v.get("price", v.get("prompt")))
            return _zero(ppt)
        if isinstance(v, str):
            return v in ("0", "0.0", "")
        return False
    return _zero(prompt) and _zero(completion)


class OpenRouterFetchThread(QThread):
    """Поток загрузки списка моделей OpenRouter."""
    finished = pyqtSignal(list)  # [(id, name, context_length), ...]
    error = pyqtSignal(str)

    def run(self):
        try:
            api_key = get_api_key("OPENROUTER_API_KEY")
            headers = {}
            if api_key and str(api_key).strip():
                headers["Authorization"] = f"Bearer {api_key.strip()}"
            resp = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers or None,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            models = data.get("data", [])
            free = []
            for m in models:
                if not _is_free_model(m.get("pricing") or {}):
                    continue
                mid = m.get("id") or m.get("canonical_slug") or ""
                if not mid:
                    continue
                name = m.get("name") or mid
                ctx = m.get("context_length")
                ctx_str = str(int(ctx)) if ctx is not None else "—"
                free.append((mid, name, ctx_str))
            free.sort(key=lambda x: (x[1].lower(), x[0]))
            self.finished.emit(free)
        except requests.RequestException as e:
            self.error.emit(f"Ошибка сети: {e}")
        except (KeyError, TypeError, ValueError) as e:
            self.error.emit(f"Ошибка разбора ответа: {e}")


class OpenRouterModelsDialog(QDialog):
    """Диалог со списком бесплатных моделей OpenRouter в табличном виде."""

    def __init__(self, parent=None, model_edit: Optional[QLineEdit] = None):
        super().__init__(parent)
        self._model_edit = model_edit
        self._models_data: list[tuple[str, str, str]] = []
        self.setWindowTitle("Бесплатные модели OpenRouter")
        self.setMinimumSize(650, 450)
        self.resize(700, 500)
        self._setup_ui()
        self._start_fetch()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self._status_label = QLabel("Загрузка списка моделей…")
        layout.addWidget(self._status_label)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID модели", "Название", "Контекст (токены)"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.doubleClicked.connect(self._on_insert)
        layout.addWidget(self.table)
        btn_layout = QHBoxLayout()
        insert_btn = QPushButton("Вставить ID в форму")
        insert_btn.clicked.connect(self._on_insert)
        btn_layout.addWidget(insert_btn)
        btn_layout.addStretch()
        open_web_btn = QPushButton("Открыть на сайте")
        open_web_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://openrouter.ai/models")))
        btn_layout.addWidget(open_web_btn)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _start_fetch(self):
        self._thread = OpenRouterFetchThread(self)
        self._thread.finished.connect(self._on_fetched)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_fetched(self, models: list):
        self._models_data = models
        self._status_label.setText(f"Загружено бесплатных моделей: {len(models)}")
        self.table.setRowCount(len(models))
        for i, (mid, name, ctx) in enumerate(models):
            self.table.setItem(i, 0, QTableWidgetItem(mid))
            self.table.setItem(i, 1, QTableWidgetItem(name))
            self.table.setItem(i, 2, QTableWidgetItem(ctx))

    def _on_error(self, msg: str):
        self._status_label.setText("Ошибка загрузки")
        QMessageBox.warning(
            self,
            "Ошибка",
            f"{msg}\n\nУбедитесь, что OPENROUTER_API_KEY указан в .env (API может требовать ключ).",
        )

    def _on_insert(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._models_data):
            return
        mid = self._models_data[row][0]
        if self._model_edit is not None:
            self._model_edit.setText(mid)
            self.accept()


class ModelEditDialog(QDialog):
    """Диалог добавления/редактирования одной модели."""

    def __init__(self, parent=None, model_id: int | None = None):
        super().__init__(parent)
        self.model_id = model_id
        self._setup_ui()
        if model_id:
            self._load_model()

    def _setup_ui(self):
        self.setWindowTitle("Редактирование модели" if self.model_id else "Добавление модели")
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: GPT-4")
        form.addRow("Название:", self.name_edit)

        self.api_url_edit = QLineEdit()
        self.api_url_edit.setPlaceholderText("https://openrouter.ai/api/v1/chat/completions")
        form.addRow("API URL:", self.api_url_edit)

        self.api_id_edit = QLineEdit()
        self.api_id_edit.setPlaceholderText("OPENROUTER_API_KEY")
        form.addRow("Переменная .env (api_id):", self.api_id_edit)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("openai/gpt-3.5-turbo")
        form.addRow("ID модели в API:", self.model_edit)

        openrouter_btn = QPushButton("Список моделей OpenRouter…")
        openrouter_btn.setStyleSheet("QPushButton { color: #0066cc; text-decoration: underline; }")
        openrouter_btn.setFlat(True)
        openrouter_btn.clicked.connect(self._on_openrouter_models)
        form.addRow("", openrouter_btn)

        self.is_active_check = QCheckBox("Активна")
        self.is_active_check.setChecked(True)
        form.addRow("", self.is_active_check)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _on_openrouter_models(self):
        d = OpenRouterModelsDialog(self, self.model_edit)
        d.exec_()

    def _load_model(self):
        m = get_model(self.model_id)
        if m:
            self.name_edit.setText(m.name)
            self.api_url_edit.setText(m.api_url)
            self.api_id_edit.setText(m.api_id)
            self.model_edit.setText(m.model)
            self.is_active_check.setChecked(m.is_active == 1)

    def _on_ok(self):
        name = self.name_edit.text().strip()
        api_url = self.api_url_edit.text().strip()
        api_id = self.api_id_edit.text().strip()
        model = self.model_edit.text().strip() or "gpt-3.5-turbo"
        is_active = 1 if self.is_active_check.isChecked() else 0

        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название модели.")
            return
        if not api_url:
            QMessageBox.warning(self, "Ошибка", "Введите API URL.")
            return
        if not api_id:
            QMessageBox.warning(self, "Ошибка", "Введите имя переменной для API-ключа.")
            return

        # Проверка формата ID модели для OpenRouter (обычно provider/model-name)
        if "openrouter.ai" in api_url.lower() and "/" not in model:
            QMessageBox.warning(
                self,
                "Формат ID модели",
                "Для OpenRouter ID модели обычно в формате provider/model-name,\n"
                "например: qwen/qwen-2.5-7b-instruct, openai/gpt-3.5-turbo\n\n"
                "Нажмите «Список моделей OpenRouter», чтобы проверить актуальные ID.",
            )
            return

        try:
            if self.model_id:
                update_model(self.model_id, name, api_url, api_id, model, is_active)
            else:
                add_model(name, api_url, api_id, model, is_active)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "api_url": self.api_url_edit.text().strip(),
            "api_id": self.api_id_edit.text().strip(),
            "model": self.model_edit.text().strip() or "gpt-3.5-turbo",
            "is_active": 1 if self.is_active_check.isChecked() else 0,
        }


class ModelsSettingsDialog(QDialog):
    """Диалог управления моделями."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки моделей")
        self.setMinimumSize(600, 400)
        self._setup_ui()
        self._refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "API URL", "Модель API", "Активна"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self._on_add)
        edit_btn = QPushButton("Изменить")
        edit_btn.clicked.connect(self._on_edit)
        del_btn = QPushButton("Удалить")
        del_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _refresh_table(self):
        models = get_all_models()
        self.table.setRowCount(len(models))
        for i, m in enumerate(models):
            self.table.setItem(i, 0, QTableWidgetItem(str(m.id)))
            self.table.setItem(i, 1, QTableWidgetItem(m.name))
            self.table.setItem(i, 2, QTableWidgetItem(m.api_url))
            self.table.setItem(i, 3, QTableWidgetItem(m.model))
            self.table.setItem(i, 4, QTableWidgetItem("Да" if m.is_active else "Нет"))

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _on_add(self):
        d = ModelEditDialog(self)
        if d.exec_() == QDialog.Accepted:
            self._refresh_table()

    def _on_edit(self):
        mid = self._selected_id()
        if mid is None:
            QMessageBox.information(self, "Выбор", "Выберите модель для редактирования.")
            return
        d = ModelEditDialog(self, mid)
        if d.exec_() == QDialog.Accepted:
            self._refresh_table()

    def _on_delete(self):
        mid = self._selected_id()
        if mid is None:
            QMessageBox.information(self, "Выбор", "Выберите модель для удаления.")
            return
        if QMessageBox.question(
            self, "Подтверждение", "Удалить выбранную модель?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        if delete_model(mid):
            self._refresh_table()
            QMessageBox.information(self, "Готово", "Модель удалена.")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось удалить модель.")
