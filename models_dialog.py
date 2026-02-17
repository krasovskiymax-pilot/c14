"""
Диалог настройки моделей нейросетей.
"""
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
)
from PyQt5.QtCore import Qt

import db
from models import get_all_models, add_model, update_model, delete_model, get_model


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
        from PyQt5.QtWidgets import QFormLayout, QLineEdit, QCheckBox
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
