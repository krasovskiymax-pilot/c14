"""
ChatList — главное окно и точка входа.
"""
import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QMessageBox,
    QHeaderView,
)
from PyQt5.QtCore import Qt

import db


class ChatListWindow(QMainWindow):
    """Главное окно ChatList."""

    def __init__(self):
        super().__init__()
        db.init_db()
        self._temp_results: list[dict] = []  # model_id, model_name, response, selected
        self._current_prompt_id: int | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.setWindowTitle("ChatList")
        self.setMinimumSize(700, 500)
        self.resize(900, 600)

        central = QWidget()
        layout = QVBoxLayout(central)

        # --- Зона ввода промта ---
        prompt_label = QLabel("Промт:")
        layout.addWidget(prompt_label)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите текст запроса...")
        self.prompt_edit.setMaximumHeight(120)
        layout.addWidget(self.prompt_edit)

        # --- Кнопки управления ---
        btn_layout = QHBoxLayout()
        self.btn_send = QPushButton("Отправить")
        self.btn_save = QPushButton("Сохранить")
        self.btn_new = QPushButton("Новый запрос")
        btn_layout.addWidget(self.btn_send)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_new)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Зона таблицы результатов ---
        results_label = QLabel("Результаты:")
        layout.addWidget(results_label)
        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Выбрано"])
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.results_table)

        self.setCentralWidget(central)

        # --- Меню ---
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")
        file_menu.addAction("Выход", self.close)

        settings_menu = menubar.addMenu("Настройки")
        settings_menu.addAction("Модели...", self._on_models_settings)

        help_menu = menubar.addMenu("Справка")
        help_menu.addAction("О программе", self._on_about)

        # --- Строка состояния ---
        self.statusBar().showMessage("Готов")

    def _connect_signals(self):
        self.btn_send.clicked.connect(self._on_send)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_new.clicked.connect(self._on_new)

    def _on_send(self):
        self.statusBar().showMessage("Отправка запросов...")
        # Заглушка: этап 7 будет реализован позже
        self.statusBar().showMessage("Отправка пока не реализована — этап 7")

    def _on_save(self):
        self.statusBar().showMessage("Сохранение...")
        # Заглушка: этап 9 будет реализован позже
        self.statusBar().showMessage("Сохранение пока не реализовано — этап 9")

    def _on_new(self):
        self._temp_results.clear()
        self._current_prompt_id = None
        self._refresh_results_table()
        self.prompt_edit.clear()
        self.statusBar().showMessage("Новый запрос")

    def _refresh_results_table(self):
        self.results_table.setRowCount(len(self._temp_results))
        for i, row in enumerate(self._temp_results):
            self.results_table.setItem(i, 0, QTableWidgetItem(row.get("model_name", "")))
            self.results_table.setItem(i, 1, QTableWidgetItem(row.get("response", "")))
            # Чекбокс для колонки "Выбрано" будет в этапе 8
            self.results_table.setItem(i, 2, QTableWidgetItem(""))
        self.results_table.resizeColumnsToContents()

    def _on_models_settings(self):
        QMessageBox.information(
            self,
            "Настройки моделей",
            "Редактирование моделей будет реализовано на этапе 11.",
        )

    def _on_about(self):
        QMessageBox.about(
            self,
            "О программе",
            "ChatList\n\nОтправка промтов в несколько нейросетей и сравнение ответов.",
        )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ChatList")
    window = ChatListWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
