"""
Модуль работы с SQLite для ChatList.
Инкапсулирует доступ к базе данных.
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

# Путь к файлу БД рядом с основным скриптом
DB_PATH = Path(__file__).parent / "chatlist.db"


def get_connection() -> sqlite3.Connection:
    """Возвращает подключение к БД."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Создаёт БД и таблицы при первом запуске."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            text TEXT NOT NULL,
            tags TEXT DEFAULT ''
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prompts_created ON prompts(created)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prompts_tags ON prompts(tags)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            api_url TEXT NOT NULL,
            api_id TEXT NOT NULL UNIQUE,
            model TEXT DEFAULT 'gpt-3.5-turbo',
            is_active INTEGER DEFAULT 1
        )
    """)
    # Миграция: добавить колонку model для существующих БД
    try:
        cur.execute("ALTER TABLE models ADD COLUMN model TEXT DEFAULT 'gpt-3.5-turbo'")
        cur.execute("UPDATE models SET model = 'gpt-3.5-turbo' WHERE model IS NULL")
    except sqlite3.OperationalError:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_id INTEGER NOT NULL,
            model_id INTEGER NOT NULL,
            response TEXT NOT NULL,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
            FOREIGN KEY (model_id) REFERENCES models(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_results_prompt_id ON results(prompt_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_results_model_id ON results(model_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_results_created ON results(created)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
    """)

    # Начальная модель OpenRouter, если таблица пуста
    cur.execute("SELECT COUNT(*) FROM models")
    if cur.fetchone()[0] == 0:
        cur.execute(
            """INSERT INTO models (name, api_url, api_id, model, is_active)
               VALUES (?, ?, ?, ?, ?)""",
            (
                "GPT-3.5 (OpenRouter)",
                "https://openrouter.ai/api/v1/chat/completions",
                "OPENROUTER_API_KEY",
                "openai/gpt-3.5-turbo",
                1,
            ),
        )

    conn.commit()
    conn.close()


# --- CRUD: prompts ---

def prompt_create(text: str, tags: str = "") -> int:
    """Создаёт промт. Возвращает id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO prompts (text, tags) VALUES (?, ?)", (text, tags))
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid or 0


def prompt_get(pid: int) -> Optional[dict]:
    """Возвращает промт по id или None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, created, text, tags FROM prompts WHERE id = ?", (pid,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def prompt_list(order_by: str = "created", desc: bool = True, search: str = "") -> list[dict]:
    """Список промтов. order_by: created|text, search — поиск по тексту и тегам."""
    col = "created" if order_by == "created" else "text"
    dir_ = "DESC" if desc else "ASC"
    conn = get_connection()
    cur = conn.cursor()
    if search:
        cur.execute(
            f"SELECT id, created, text, tags FROM prompts WHERE text LIKE ? OR tags LIKE ? ORDER BY {col} {dir_}",
            (f"%{search}%", f"%{search}%"),
        )
    else:
        cur.execute(f"SELECT id, created, text, tags FROM prompts ORDER BY {col} {dir_}")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def prompt_update(pid: int, text: str, tags: str = "") -> bool:
    """Обновляет промт. Возвращает True при успехе."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE prompts SET text = ?, tags = ? WHERE id = ?", (text, tags, pid))
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def prompt_delete(pid: int) -> bool:
    """Удаляет промт. Возвращает True при успехе."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM prompts WHERE id = ?", (pid,))
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok


# --- CRUD: models ---

def model_create(name: str, api_url: str, api_id: str, model: str = "gpt-3.5-turbo", is_active: int = 1) -> int:
    """Создаёт модель. Возвращает id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO models (name, api_url, api_id, model, is_active) VALUES (?, ?, ?, ?, ?)",
        (name, api_url, api_id, model, is_active),
    )
    mid = cur.lastrowid
    conn.commit()
    conn.close()
    return mid or 0


def model_get(mid: int) -> Optional[dict]:
    """Возвращает модель по id или None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, api_url, api_id, model, is_active FROM models WHERE id = ?", (mid,)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def model_list(active_only: bool = False, search: str = "") -> list[dict]:
    """Список моделей. active_only — только is_active=1."""
    conn = get_connection()
    cur = conn.cursor()
    if active_only:
        if search:
            cur.execute(
                "SELECT id, name, api_url, api_id, model, is_active FROM models WHERE is_active = 1 AND (name LIKE ? OR api_id LIKE ?)",
                (f"%{search}%", f"%{search}%"),
            )
        else:
            cur.execute(
                "SELECT id, name, api_url, api_id, model, is_active FROM models WHERE is_active = 1"
            )
    else:
        if search:
            cur.execute(
                "SELECT id, name, api_url, api_id, model, is_active FROM models WHERE name LIKE ? OR api_id LIKE ?",
                (f"%{search}%", f"%{search}%"),
            )
        else:
            cur.execute("SELECT id, name, api_url, api_id, model, is_active FROM models")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def model_update(mid: int, name: str, api_url: str, api_id: str, model: str, is_active: int) -> bool:
    """Обновляет модель."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE models SET name = ?, api_url = ?, api_id = ?, model = ?, is_active = ? WHERE id = ?",
        (name, api_url, api_id, model, is_active, mid),
    )
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def model_delete(mid: int) -> bool:
    """Удаляет модель."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM models WHERE id = ?", (mid,))
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok


# --- CRUD: results ---

def result_create(prompt_id: int, model_id: int, response: str) -> int:
    """Создаёт результат. Возвращает id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO results (prompt_id, model_id, response) VALUES (?, ?, ?)",
        (prompt_id, model_id, response),
    )
    rid = cur.lastrowid
    conn.commit()
    conn.close()
    return rid or 0


def result_list(prompt_id: Optional[int] = None, order_by: str = "created", desc: bool = True) -> list[dict]:
    """Список результатов. prompt_id — фильтр по промту."""
    col = "created" if order_by == "created" else "id"
    dir_ = "DESC" if desc else "ASC"
    conn = get_connection()
    cur = conn.cursor()
    if prompt_id is not None:
        cur.execute(
            f"SELECT r.id, r.prompt_id, r.model_id, r.response, r.created, m.name as model_name "
            f"FROM results r JOIN models m ON r.model_id = m.id "
            f"WHERE r.prompt_id = ? ORDER BY r.{col} {dir_}",
            (prompt_id,),
        )
    else:
        cur.execute(
            f"SELECT r.id, r.prompt_id, r.model_id, r.response, r.created, m.name as model_name "
            f"FROM results r JOIN models m ON r.model_id = m.id "
            f"ORDER BY r.{col} {dir_}"
        )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- CRUD: settings ---

def setting_get(key: str) -> Optional[str]:
    """Возвращает значение настройки или None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row["value"] if row else None


def setting_set(key: str, value: str) -> None:
    """Устанавливает настройку."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()
