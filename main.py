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
    QComboBox,
    QProgressBar,
    QCheckBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

import db
from models import get_active_models
from network import send_prompt_to_all_models
from models_dialog import ModelsSettingsDialog


class SendWorker(QThread):
    """Рабочий поток для отправки запросов к API."""
    finished = pyqtSignal(list)  # list of dicts

    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt

    def run(self):
        models = get_active_models()
        results = send_prompt_to_all_models(models, self.prompt)
        # Преобразуем в list[dict] для временной таблицы
        data = [
            {"model_id": r[0], "model_name": r[1], "response": r[2] or "", "selected": False}
            for r in results
        ]
        self.finished.emit(data)


class ChatListWindow(QMainWindow):
    """Главное окно ChatList."""

    def __init__(self):
        super().__init__()
        db.init_db()
        self._temp_results: list[dict] = []
        self._current_prompt_id: int | None = None
        self._send_worker: SendWorker | None = None
        self._setup_ui()
        self._connect_signals()
        self._load_prompts_combo()

    def _setup_ui(self):
        self.setWindowTitle("ChatList")
        self.setMinimumSize(700, 500)
        self.resize(900, 600)

        central = QWidget()
        layout = QVBoxLayout(central)

        # --- Зона ввода/выбора промта ---
        prompt_row = QHBoxLayout()
        prompt_row.addWidget(QLabel("Промт:"))
        self.prompts_combo = QComboBox()
        self.prompts_combo.setEditable(False)
        self.prompts_combo.setMinimumWidth(200)
        self.prompts_combo.currentIndexChanged.connect(self._on_prompt_selected)
        prompt_row.addWidget(self.prompts_combo, 0)
        clear_btn = QPushButton("Очистить")
        clear_btn.clicked.connect(self._on_clear_prompt)
        prompt_row.addWidget(clear_btn)
        prompt_row.addStretch()
        layout.addLayout(prompt_row)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите текст запроса или выберите сохранённый промт...")
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

        # --- Индикатор загрузки ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)  # бесконечный индикатор
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

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

        self.statusBar().showMessage("Готов")

    def _connect_signals(self):
        self.btn_send.clicked.connect(self._on_send)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_new.clicked.connect(self._on_new)

    def _load_prompts_combo(self):
        self.prompts_combo.blockSignals(True)
        self.prompts_combo.clear()
        self.prompts_combo.addItem("— Новый промт —", None)
        for p in db.prompt_list():
            short = (p["text"][:50] + "…") if len(p["text"]) > 50 else p["text"]
            self.prompts_combo.addItem(short, p["id"])
        self.prompts_combo.blockSignals(False)

    def _on_prompt_selected(self):
        pid = self.prompts_combo.currentData()
        if pid is not None:
            p = db.prompt_get(pid)
            if p:
                self.prompt_edit.setPlainText(p["text"])
                self._current_prompt_id = pid

    def _on_clear_prompt(self):
        self.prompts_combo.setCurrentIndex(0)
        self.prompt_edit.clear()
        self._current_prompt_id = None
        self.statusBar().showMessage("Очищено")

    def _on_send(self):
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Внимание", "Введите текст промта.")
            return

        models = get_active_models()
        if not models:
            QMessageBox.warning(
                self,
                "Внимание",
                "Нет активных моделей. Добавьте модели в Настройки → Модели.",
            )
            return

        self._temp_results.clear()
        self._refresh_results_table()
        self.btn_send.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.statusBar().showMessage("Отправка запросов…")

        self._send_worker = SendWorker(prompt)
        self._send_worker.finished.connect(self._on_send_finished)
        self._send_worker.start()

    def _on_send_finished(self, data: list):
        self._send_worker = None
        self.btn_send.setEnabled(True)
        self.progress_bar.setVisible(False)
        self._temp_results = data
        self._refresh_results_table()
        success = sum(1 for r in data if r.get("response") and not r["response"].startswith("Ошибка") and not r["response"].startswith("Переменная"))
        self.statusBar().showMessage(f"Готово. Получено ответов: {success} из {len(data)}.")

    def _on_save(self):
        selected = [r for r in self._temp_results if r.get("selected")]
        if not selected:
            QMessageBox.information(
                self,
                "Сохранение",
                "Отметьте галочкой строки для сохранения.",
            )
            return

        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Внимание", "Введите или выберите промт перед сохранением.")
            return

        try:
            if self._current_prompt_id is None:
                self._current_prompt_id = db.prompt_create(prompt_text)
                self._load_prompts_combo()

            for r in selected:
                db.result_create(self._current_prompt_id, r["model_id"], r["response"])

            self._temp_results = [x for x in self._temp_results if not x.get("selected")]
            self._refresh_results_table()
            self.statusBar().showMessage(f"Сохранено строк: {len(selected)}")
            QMessageBox.information(self, "Сохранено", f"Сохранено результатов: {len(selected)}.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")
            self.statusBar().showMessage("Ошибка сохранения")

    def _on_new(self):
        if self._send_worker and self._send_worker.isRunning():
            return
        self._temp_results.clear()
        self._current_prompt_id = None
        self._refresh_results_table()
        self.prompt_edit.clear()
        self.prompts_combo.setCurrentIndex(0)
        self.statusBar().showMessage("Новый запрос")

    def _refresh_results_table(self):
        self.results_table.setRowCount(len(self._temp_results))
        for i, row in enumerate(self._temp_results):
            self.results_table.setItem(i, 0, QTableWidgetItem(row.get("model_name", "")))
            resp = row.get("response", "")
            self.results_table.setItem(i, 1, QTableWidgetItem(resp))

            # Чекбокс "Выбрано"
            cb = QCheckBox()
            cb.setChecked(row.get("selected", False))
            cb.stateChanged.connect(lambda s, idx=i: self._on_selection_changed(idx, s))
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.addWidget(cb)
            cell_layout.setContentsMargins(4, 0, 0, 0)
            self.results_table.setCellWidget(i, 2, cell_widget)
        self.results_table.resizeColumnsToContents()

    def _on_selection_changed(self, row_idx: int, state: int):
        if 0 <= row_idx < len(self._temp_results):
            self._temp_results[row_idx]["selected"] = state == Qt.Checked

    def _on_models_settings(self):
        d = ModelsSettingsDialog(self)
        d.exec_()
        self._load_prompts_combo()

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
