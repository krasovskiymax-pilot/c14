"""
Тестовая программа для просмотра и редактирования SQLite-базы.
Список таблиц → кнопка «Открыть» → таблица с пагинацией и CRUD.
"""
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QDialog,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QSpinBox,
    QHeaderView,
    QAbstractItemView,
    QSplitter,
)
from PyQt5.QtCore import Qt

import sqlite3


class SqliteViewer(QMainWindow):
    """Главное окно: выбор файла, список таблиц, кнопка «Открыть»."""

    def __init__(self):
        super().__init__()
        self.db_path: Path | None = None
        self.conn: sqlite3.Connection | None = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Просмотр SQLite")
        self.setMinimumSize(600, 400)
        self.resize(800, 500)

        central = QWidget()
        layout = QVBoxLayout(central)

        # Выбор файла
        file_row = QHBoxLayout()
        self.file_label = QLabel("Файл не выбран")
        self.file_label.setStyleSheet("color: #666;")
        file_row.addWidget(self.file_label, 1)
        browse_btn = QPushButton("Обзор...")
        browse_btn.clicked.connect(self._on_browse)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        # Список таблиц
        layout.addWidget(QLabel("Таблицы:"))
        self.tables_list = QListWidget()
        self.tables_list.setMinimumHeight(150)
        layout.addWidget(self.tables_list)

        # Кнопка «Открыть»
        self.open_btn = QPushButton("Открыть")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._on_open_table)
        layout.addWidget(self.open_btn)

        self.setCentralWidget(central)

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл SQLite", "", "SQLite (*.db *.sqlite *.sqlite3);;Все файлы (*)"
        )
        if path:
            self._load_db(Path(path))

    def _load_db(self, path: Path):
        if self.conn:
            self.conn.close()
        try:
            self.conn = sqlite3.connect(path)
            self.db_path = path
            self.file_label.setText(str(path))
            self.file_label.setStyleSheet("")
            cur = self.conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            tables = [r[0] for r in cur.fetchall()]
            self.tables_list.clear()
            for t in tables:
                self.tables_list.addItem(QListWidgetItem(t))
            self.open_btn.setEnabled(bool(tables))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть БД: {e}")
            self.open_btn.setEnabled(False)

    def _on_open_table(self):
        item = self.tables_list.currentItem()
        if not item or not self.conn:
            return
        table_name = item.text()
        d = TableViewDialog(self, self.conn, table_name)
        d.exec_()


class TableViewDialog(QDialog):
    """Диалог просмотра таблицы с пагинацией и CRUD."""

    PAGE_SIZE = 20

    def __init__(self, parent, conn: sqlite3.Connection, table_name: str):
        super().__init__(parent)
        self.conn = conn
        self.table_name = table_name
        self.current_page = 0
        self.columns: list[str] = []
        self._setup_ui()
        self._load_schema()
        self._refresh_data()

    def _setup_ui(self):
        self.setWindowTitle(f"Таблица: {self.table_name}")
        self.setMinimumSize(700, 450)
        self.resize(900, 550)
        layout = QVBoxLayout(self)

        # Кнопки CRUD
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
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # Пагинация
        pagination = QHBoxLayout()
        self.prev_btn = QPushButton("← Назад")
        self.prev_btn.clicked.connect(self._prev_page)
        pagination.addWidget(self.prev_btn)
        self.page_label = QLabel()
        pagination.addWidget(self.page_label, 1, Qt.AlignCenter)
        self.next_btn = QPushButton("Вперёд →")
        self.next_btn.clicked.connect(self._next_page)
        pagination.addWidget(self.next_btn)
        layout.addLayout(pagination)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _load_schema(self):
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({self.table_name})")
        self.schema = cur.fetchall()
        self.columns = [row[1] for row in self.schema]

    def _get_total_count(self) -> int:
        cur = self.conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM [{self.table_name}]")
        return cur.fetchone()[0]

    def _refresh_data(self):
        total = self._get_total_count()
        total_pages = max(1, (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.current_page = min(self.current_page, total_pages - 1)
        self.current_page = max(0, self.current_page)

        offset = self.current_page * self.PAGE_SIZE
        cur = self.conn.cursor()
        cur.execute(
            f"SELECT * FROM [{self.table_name}] LIMIT ? OFFSET ?",
            (self.PAGE_SIZE, offset),
        )
        rows = cur.fetchall()

        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(val) if val is not None else ""))

        # Обновить пагинацию
        self.page_label.setText(
            f"Страница {self.current_page + 1} из {total_pages} (всего записей: {total})"
        )
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < total_pages - 1 and total > self.PAGE_SIZE)

    def _prev_page(self):
        self.current_page -= 1
        self._refresh_data()

    def _next_page(self):
        self.current_page += 1
        self._refresh_data()

    def _get_pk_column(self) -> str | None:
        """Возвращает имя первичного ключа или первую колонку."""
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({self.table_name})")
        for row in cur.fetchall():
            if row[5]:  # pk
                return row[1]
        return self.columns[0] if self.columns else None

    def _get_insert_columns(self) -> list[str]:
        """Колонки для INSERT (исключая autoincrement PK)."""
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({self.table_name})")
        result = []
        for row in cur.fetchall():
            name, type_, notnull, default, pk = row[1], row[2], row[3], row[4], row[5]
            if pk and "INT" in (type_ or "").upper():
                continue
            result.append(name)
        return result or self.columns

    def _on_add(self):
        insert_cols = self._get_insert_columns()
        d = RowEditDialog(self, insert_cols, {}, is_new=True)
        if d.exec_() != QDialog.Accepted:
            return
        data = d.get_data()
        if not data:
            return
        cols = ", ".join(f"[{k}]" for k in data.keys())
        placeholders = ", ".join("?" for _ in data)
        try:
            cur = self.conn.cursor()
            cur.execute(
                f"INSERT INTO [{self.table_name}] ({cols}) VALUES ({placeholders})",
                list(data.values()),
            )
            self.conn.commit()
            self._refresh_data()
            QMessageBox.information(self, "Готово", "Запись добавлена.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_edit(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Выбор", "Выберите строку для редактирования.")
            return
        data = {}
        pk_col = self._get_pk_column()
        for j in range(self.table.columnCount()):
            item = self.table.item(row, j)
            col = self.columns[j]
            data[col] = item.text() if item else ""
        d = RowEditDialog(self, self.columns, data, is_new=False)
        if d.exec_() != QDialog.Accepted:
            return
        new_data = d.get_data()
        if not new_data or not pk_col:
            return
        try:
            cur = self.conn.cursor()
            sets = ", ".join(f"[{k}] = ?" for k in new_data.keys() if k != pk_col)
            values = [v for k, v in new_data.items() if k != pk_col]
            values.append(data[pk_col])
            cur.execute(
                f"UPDATE [{self.table_name}] SET {sets} WHERE [{pk_col}] = ?",
                values,
            )
            self.conn.commit()
            self._refresh_data()
            QMessageBox.information(self, "Готово", "Запись обновлена.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_delete(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Выбор", "Выберите строку для удаления.")
            return
        if QMessageBox.question(
            self, "Подтверждение", "Удалить выбранную запись?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        pk_col = self._get_pk_column()
        if not pk_col:
            return
        item = self.table.item(row, self.columns.index(pk_col))
        pk_value = item.text() if item else ""
        try:
            cur = self.conn.cursor()
            cur.execute(f"DELETE FROM [{self.table_name}] WHERE [{pk_col}] = ?", (pk_value,))
            self.conn.commit()
            self._refresh_data()
            QMessageBox.information(self, "Готово", "Запись удалена.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


class RowEditDialog(QDialog):
    """Диалог добавления/редактирования записи."""

    def __init__(self, parent, columns: list[str], data: dict, is_new: bool):
        super().__init__(parent)
        self.columns = columns
        self.data = data
        self.is_new = is_new
        self.edits: dict[str, QLineEdit] = {}
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Добавить запись" if self.is_new else "Изменить запись")
        layout = QFormLayout(self)
        for col in self.columns:
            edit = QLineEdit()
            edit.setText(self.data.get(col, ""))
            self.edits[col] = edit
            layout.addRow(col + ":", edit)
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def _on_ok(self):
        self.accept()

    def get_data(self) -> dict:
        return {col: self.edits[col].text() for col in self.columns}


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SQLite Viewer")
    win = SqliteViewer()
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists() and not path.is_absolute():
            script_dir = Path(__file__).parent
            path = script_dir / sys.argv[1]
        if path.exists():
            win._load_db(path)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
