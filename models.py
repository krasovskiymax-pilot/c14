"""
Логика работы с моделями нейросетей.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

import db

# Сначала .env, затем .env.local (локальные ключи имеют приоритет)
load_dotenv()
env_local = Path(__file__).parent / ".env.local"
if env_local.exists():
    load_dotenv(env_local, override=True)


@dataclass
class Model:
    """Структура данных модели нейросети."""
    id: int
    name: str
    api_url: str
    api_id: str
    model: str  # ID модели для API (напр. openai/gpt-3.5-turbo для OpenRouter)
    is_active: int


def _row_to_model(row: dict) -> Model:
    return Model(
        id=row["id"],
        name=row["name"],
        api_url=row["api_url"],
        api_id=row["api_id"],
        model=row.get("model", "gpt-3.5-turbo") or "gpt-3.5-turbo",
        is_active=row["is_active"],
    )


def get_active_models() -> list[Model]:
    """Возвращает список активных моделей из БД."""
    rows = db.model_list(active_only=True)
    return [_row_to_model(r) for r in rows]


def get_all_models(search: str = "") -> list[Model]:
    """Возвращает все модели (с опциональным поиском)."""
    rows = db.model_list(active_only=False, search=search)
    return [_row_to_model(r) for r in rows]


def get_model(model_id: int) -> Optional[Model]:
    """Возвращает модель по id или None."""
    row = db.model_get(model_id)
    return _row_to_model(row) if row else None


def get_api_key(api_id: str) -> Optional[str]:
    """Загружает API-ключ из .env по имени переменной (api_id)."""
    return os.getenv(api_id)


def add_model(name: str, api_url: str, api_id: str, model: str = "gpt-3.5-turbo", is_active: int = 1) -> int:
    """Добавляет модель. Возвращает id."""
    return db.model_create(name, api_url, api_id, model, is_active)


def update_model(
    model_id: int, name: str, api_url: str, api_id: str, model: str, is_active: int
) -> bool:
    """Обновляет модель."""
    return db.model_update(model_id, name, api_url, api_id, model, is_active)


def delete_model(model_id: int) -> bool:
    """Удаляет модель."""
    return db.model_delete(model_id)
