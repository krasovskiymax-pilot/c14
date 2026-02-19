"""
Диалог управления таблицей «Промты» с CRUD.
"""
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
    QHeaderView,
    QAbstractItemView,
    QFormLayout,
    QLineEdit,
    QTextEdit,
)
from PyQt5.QtCore import Qt

import db


class PromptEditDialog(QDialog):
    """Диалог добавления/редактирования промта."""

    def __init__(self, parent=None, prompt_id: int | None = None):
        super().__init__(parent)
        self.prompt_id = prompt_id
        self._setup_ui()
        if prompt_id:
            self._load()

    def _setup_ui(self):
        self.setWindowTitle("Изменить промт" if self.prompt_id else "Добавить промт")
        layout = QFormLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Текст промта")
        self.text_edit.setMaximumHeight(120)
        layout.addRow("Текст:", self.text_edit)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("теги, через запятую")
        layout.addRow("Теги:", self.tags_edit)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def _load(self):
        p = db.prompt_get(self.prompt_id)
        if p:
            self.text_edit.setPlainText(p["text"])
            self.tags_edit.setText(p.get("tags", "") or "")

    def _on_ok(self):
        if not self.text_edit.toPlainText().strip():
            QMessageBox.warning(self, "Ошибка", "Введите текст промта.")
            return
        self.accept()

    def get_data(self):
        return {
            "text": self.text_edit.toPlainText().strip(),
            "tags": self.tags_edit.text().strip(),
        }


class PromptsDialog(QDialog):
    """Диалог таблицы «Промты» с кнопками CRUD."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Промты")
        self.setMinimumSize(600, 400)
        self.resize(750, 500)
        self._setup_ui()
        self._refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # CRUD-кнопки
        crud_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self._on_add)
        edit_btn = QPushButton("Изменить")
        edit_btn.clicked.connect(self._on_edit)
        del_btn = QPushButton("Удалить")
        del_btn.clicked.connect(self._on_delete)
        crud_layout.addWidget(add_btn)
        crud_layout.addWidget(edit_btn)
        crud_layout.addWidget(del_btn)
        crud_layout.addStretch()
        layout.addLayout(crud_layout)

        # Таблица
        self.table = QTableWidget()
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "Текст", "Теги"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _refresh_table(self):
        prompts = db.prompt_list()
        self.table.setRowCount(len(prompts))
        for i, p in enumerate(prompts):
            self.table.setItem(i, 0, QTableWidgetItem(str(p["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(str(p.get("created", ""))))
            text = p.get("text", "")
            display = (text[:100] + "…") if len(text) > 100 else text
            self.table.setItem(i, 2, QTableWidgetItem(display))
            self.table.setItem(i, 3, QTableWidgetItem(p.get("tags", "") or ""))
        self.table.resizeColumnsToContents()

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _on_add(self):
        d = PromptEditDialog(self)
        if d.exec_() == QDialog.Accepted:
            data = d.get_data()
            db.prompt_create(data["text"], data["tags"])
            self._refresh_table()
            QMessageBox.information(self, "Готово", "Промт добавлен.")

    def _on_edit(self):
        pid = self._selected_id()
        if pid is None:
            QMessageBox.information(self, "Выбор", "Выберите промт для редактирования.")
            return
        d = PromptEditDialog(self, pid)
        if d.exec_() == QDialog.Accepted:
            data = d.get_data()
            db.prompt_update(pid, data["text"], data["tags"])
            self._refresh_table()
            QMessageBox.information(self, "Готово", "Промт обновлён.")

    def _on_delete(self):
        pid = self._selected_id()
        if pid is None:
            QMessageBox.information(self, "Выбор", "Выберите промт для удаления.")
            return
        if QMessageBox.question(
            self, "Подтверждение", "Удалить выбранный промт?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        if db.prompt_delete(pid):
            self._refresh_table()
            QMessageBox.information(self, "Готово", "Промт удалён.")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось удалить промт.")
