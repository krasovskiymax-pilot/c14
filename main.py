"""
ChatList — главное окно и точка входа.
"""
import sys
from datetime import datetime
from pathlib import Path

import markdown
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QTextBrowser,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QMessageBox,
    QHeaderView,
    QComboBox,
    QProgressBar,
    QDialog,
    QCheckBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

import db
from models import get_active_models
from network import send_prompt_to_all_models
from models_dialog import ModelsSettingsDialog
from prompts_dialog import PromptsDialog
from prompt_assistant_dialog import PromptImproveDialog
from settings_dialog import (
    SettingsDialog,
    get_theme,
    get_font_size,
    DARK_STYLESHEET,
    THEME_DARK,
)


class MarkdownViewerDialog(QDialog):
    """Диалог просмотра ответа с форматированием Markdown."""

    def __init__(self, parent=None, title: str = "Ответ", text: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(500, 400)
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        try:
            body_html = markdown.markdown(text, extensions=["extra", "nl2br"])
        except Exception:
            body_html = f"<pre>{text}</pre>"
        style = """
        <style>
        body { font-family: sans-serif; padding: 12px; line-height: 1.5; }
        code { background: #f0f0f0; padding: 2px 6px; border-radius: 4px; }
        pre { background: #f5f5f5; padding: 12px; overflow-x: auto; border-radius: 4px; }
        pre code { background: none; padding: 0; }
        h1,h2,h3 { margin-top: 1em; }
        table { border-collapse: collapse; margin: 8px 0; }
        th, td { border: 1px solid #ccc; padding: 6px 12px; }
        </style>
        """
        html = f"<!DOCTYPE html><html><head>{style}</head><body>{body_html}</body></html>"
        browser.setHtml(html)
        layout.addWidget(browser)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class ChatListWindow(QMainWindow):
    """Главное окно ChatList."""

    def __init__(self):
        super().__init__()
        db.init_db()
        self._temp_results: list[dict] = []
        self._current_prompt_id: int | None = None
        self._setup_ui()
        self._connect_signals()
        self._load_prompts_combo()
        self._apply_app_theme_and_font()  # тема и шрифт из БД

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
        self.btn_improve = QPushButton("Улучшить промт")
        self.btn_improve.clicked.connect(self._on_improve_prompt)
        self.btn_improve.setToolTip("Улучшить текст промта с помощью ИИ")
        self.btn_save = QPushButton("Сохранить")
        self.btn_new = QPushButton("Новый запрос")
        btn_layout.addWidget(self.btn_send)
        btn_layout.addWidget(self.btn_improve)
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
        self.results_table.setHorizontalHeaderLabels(["Выбрать", "Модель", "Ответ"])
        self.results_table.setColumnWidth(0, 80)  # узкая колонка для чекбоксов
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.results_table.setWordWrap(True)  # многострочный текст в ячейках
        self.results_table.cellDoubleClicked.connect(lambda r, c: self._on_open_response())
        self.results_table.horizontalHeader().sectionResized.connect(
            lambda *_: self.results_table.resizeRowsToContents()
        )  # при изменении ширины — пересчёт высоты строк
        layout.addWidget(self.results_table)

        # Кнопки под таблицей результатов
        results_btn_layout = QHBoxLayout()
        self.btn_save_selected = QPushButton("Сохранить выбранные")
        self.btn_save_selected.clicked.connect(self._on_save_selected)
        self.btn_save_selected.setToolTip("Сохранить в БД только отмеченные ответы")
        results_btn_layout.addWidget(self.btn_save_selected)
        self.btn_open = QPushButton("Открыть")
        self.btn_open.clicked.connect(self._on_open_response)
        self.btn_open.setToolTip("Открыть выбранный ответ в отдельном окне")
        results_btn_layout.addWidget(self.btn_open)
        clear_results_btn = QPushButton("Очистить")
        clear_results_btn.clicked.connect(self._on_clear_results)
        clear_results_btn.setToolTip("Очистить таблицу результатов")
        results_btn_layout.addWidget(clear_results_btn)
        results_btn_layout.addStretch()
        layout.addLayout(results_btn_layout)

        self.setCentralWidget(central)

        # --- Меню ---
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")
        file_menu.addAction("Выход", self.close)

        data_menu = menubar.addMenu("Данные")
        data_menu.addAction("Промты...", self._on_prompts_dialog)

        settings_menu = menubar.addMenu("Настройки")
        settings_menu.addAction("Параметры...", self._on_settings_dialog)
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

    def _on_improve_prompt(self):
        text = self.prompt_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Подсказка", "Введите текст промта для улучшения.")
            return
        def on_substitute(improved: str):
            self.prompt_edit.setPlainText(improved)
            self.statusBar().showMessage("Промт подставлен")
        d = PromptImproveDialog(self, original_text=text, on_substitute=on_substitute)
        d.exec_()

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
        QApplication.processEvents()

        # Выполняем в главном потоке
        try:
            results = send_prompt_to_all_models(models, prompt)
            data = [
                {"model_id": r[0], "model_name": r[1], "response": r[2] or "", "selected": False}
                for r in results
            ]
            # Откладываем обновление UI (снижает риск крэша Qt)
            QTimer.singleShot(0, lambda: self._on_send_finished(data))
        except Exception as e:
            QTimer.singleShot(0, lambda: self._on_send_finished([
                {"model_id": 0, "model_name": "Ошибка", "response": str(e), "selected": False}
            ]))

    def _save_results_to_file(self, data: list) -> Path | None:
        """Сохраняет результаты в файл. Возвращает путь к файлу или None."""
        if not data:
            return None
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path(__file__).parent / "results"
        out_dir.mkdir(exist_ok=True)
        path = out_dir / f"chatlist_{stamp}.txt"
        lines = []
        for row in data:
            name = row.get("model_name", "?")
            resp = row.get("response", "")
            lines.append(f"{'='*60}\nМодель: {name}\n{'='*60}\n{resp}\n")
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _on_send_finished(self, data: list):
        try:
            self.btn_send.setEnabled(True)
            self.progress_bar.setVisible(False)
            self._temp_results = data or []
            err_prefixes = ("Ошибка", "Переменная", "HTTP", "Неверный", "Таймаут")
            success = sum(
                1 for r in self._temp_results
                if r.get("response") and not any(r["response"].startswith(p) for p in err_prefixes)
            )

            self._refresh_results_table()
            self.statusBar().showMessage(f"Готово. Получено ответов: {success} из {len(self._temp_results)}.")
        except Exception as e:
            self.btn_send.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка при обработке результатов:\n{e}",
            )

    def _on_save_selected(self):
        """Сохраняет в БД только выбранные ответы."""
        selected = [r for r in self._temp_results if r.get("selected")]
        if not selected:
            QMessageBox.information(
                self, "Выбор",
                "Отметьте галочками ответы для сохранения."
            )
            return
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Внимание", "Введите промт перед сохранением.")
            return
        try:
            if self._current_prompt_id is None:
                self._current_prompt_id = db.prompt_create(prompt_text)
                self._load_prompts_combo()
            for r in selected:
                db.result_create(self._current_prompt_id, r["model_id"], r["response"])
            self.statusBar().showMessage(f"Сохранено: {len(selected)} выбранных ответов")
            QMessageBox.information(self, "Сохранено", f"Сохранено ответов: {len(selected)}.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def _on_save(self):
        """Сохраняет текущий промт и все результаты в БД."""
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Внимание", "Введите промт перед сохранением.")
            return
        if not self._temp_results:
            QMessageBox.information(self, "Сохранение", "Сначала отправьте запрос и получите результаты.")
            return
        try:
            if self._current_prompt_id is None:
                self._current_prompt_id = db.prompt_create(prompt_text)
                self._load_prompts_combo()
            for r in self._temp_results:
                db.result_create(self._current_prompt_id, r["model_id"], r["response"])
            self.statusBar().showMessage(f"Сохранено: промт + {len(self._temp_results)} результатов")
            QMessageBox.information(self, "Сохранено", f"Сохранено результатов: {len(self._temp_results)}.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def _on_new(self):
        self._temp_results.clear()
        self._current_prompt_id = None
        self._refresh_results_table()
        self.prompt_edit.clear()
        self.prompts_combo.setCurrentIndex(0)
        self.statusBar().showMessage("Новый запрос")

    def _sanitize_for_display(self, text: str) -> str:
        """Удаляет символы, способные вызвать крэш Qt."""
        if not text:
            return ""
        result = []
        for c in str(text):
            code = ord(c)
            # Разрешаем печатные символы, переносы; исключаем null, суррогаты, замену
            if code == 0 or (0xD800 <= code <= 0xDFFF) or code == 0xFFFD:
                continue
            if c >= " " or c in "\n\r\t":
                result.append(c)
        s = "".join(result)
        # Лимит увеличен, чтобы показывать весь ответ (многострочное отображение в таблице)
        max_len = 50000
        if len(s) > max_len:
            return s[:max_len] + "…"
        return s

    def _on_open_response(self):
        """Открыть выбранный ответ в диалоге просмотра Markdown."""
        row = self.results_table.currentRow()
        if row < 0 or row >= len(self._temp_results):
            QMessageBox.information(self, "Выбор", "Выберите строку с ответом для просмотра.")
            return
        r = self._temp_results[row] if row < len(self._temp_results) else {}
        title = f"Ответ: {r.get('model_name', 'Модель')}"
        text = r.get("response", "")
        d = MarkdownViewerDialog(self, title=title, text=text)
        d.exec_()

    def _on_clear_results(self):
        """Очистить таблицу результатов."""
        self._temp_results.clear()
        self._refresh_results_table()
        self.statusBar().showMessage("Результаты очищены")

    def _refresh_results_table(self):
        self.results_table.setRowCount(len(self._temp_results))
        for i, row in enumerate(self._temp_results):
            try:
                cb = QCheckBox()
                cb.setChecked(bool(row.get("selected", False)))
                cb.stateChanged.connect(lambda state, idx=i: self._on_selection_changed(idx, state))
                self.results_table.setCellWidget(i, 0, cb)
                name = str(row.get("model_name", ""))[:80]
                resp = self._sanitize_for_display(str(row.get("response", "")))
                self.results_table.setItem(i, 1, QTableWidgetItem(name))
                self.results_table.setItem(i, 2, QTableWidgetItem(resp))
            except Exception:
                self.results_table.setItem(i, 1, QTableWidgetItem("?"))
                self.results_table.setItem(i, 2, QTableWidgetItem("(ошибка отображения)"))
        self.results_table.resizeRowsToContents()  # высота строк по содержимому

    def _on_selection_changed(self, row_idx: int, state):
        if 0 <= row_idx < len(self._temp_results):
            self._temp_results[row_idx]["selected"] = state == Qt.Checked

    def _on_prompts_dialog(self):
        try:
            d = PromptsDialog(self)
            d.exec_()
            self._load_prompts_combo()
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Не удалось открыть «Промты»:\n{e}",
            )

    def _on_settings_dialog(self):
        d = SettingsDialog(self)
        if d.exec_() == QDialog.Accepted:
            self._apply_app_theme_and_font()

    def _on_models_settings(self):
        d = ModelsSettingsDialog(self)
        d.exec_()
        self._load_prompts_combo()

    def _apply_app_theme_and_font(self):
        """Применяет тему и размер шрифта из БД ко всему приложению."""
        app = QApplication.instance()
        if not app:
            return
        theme = get_theme()
        font_size = get_font_size()
        if theme == THEME_DARK:
            app.setStyleSheet(DARK_STYLESHEET)
        else:
            app.setStyleSheet("")
        font = app.font()
        font.setPointSize(font_size)
        app.setFont(font)

    def _on_about(self):
        QMessageBox.about(
            self,
            "О программе",
            "<h2>ChatList</h2>"
            "<p>Сравнение ответов нейросетей.</p>"
            "<p>Отправка одного промта в несколько моделей ИИ "
            "(OpenAI, Claude, Llama, Qwen и др. через OpenRouter) "
            "и просмотр результатов в таблице.</p>"
            "<p><b>Возможности:</b></p>"
            "<ul>"
            "<li>Выбор и сохранение промтов</li>"
            "<li>Улучшение промтов с помощью ИИ</li>"
            "<li>Сохранение выбранных ответов в базу</li>"
            "<li>Настройки темы и шрифта</li>"
            "</ul>"
            "<p>Python, PyQt5, SQLite, OpenRouter API.</p>",
        )


def _excepthook(exc_type, exc_value, exc_tb):
    """Перехват необработанных исключений — показывает диалог вместо тихого выхода."""
    import traceback
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(msg, file=sys.stderr)
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance()
        if app:
            QMessageBox.critical(None, "Ошибка", f"Критическая ошибка:\n\n{exc_value}")
    except Exception:
        pass


def main():
    sys.excepthook = _excepthook
    app = QApplication(sys.argv)
    app.setApplicationName("ChatList")
    icon_path = Path(__file__).parent / "app.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = ChatListWindow()
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
