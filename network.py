"""
Модуль отправки HTTP-запросов к API нейросетей.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import httpx

from models import Model, get_api_key

DEFAULT_TIMEOUT = 60.0


class NetworkError(Exception):
    """Ошибка при сетевом запросе."""
    pass


class ApiKeyError(NetworkError):
    """API-ключ не найден в .env."""
    pass


def send_prompt_to_model(
    model: Model,
    prompt: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, str]:
    """
    Отправляет промт к одной модели.

    Возвращает (model_id, response_text).
    При ошибке выбрасывает NetworkError или ApiKeyError.
    Реализован базовый запрос для OpenAI-совместимого API.
    """
    api_key = get_api_key(model.api_id)
    if not api_key:
        raise ApiKeyError(f"Переменная {model.api_id} не найдена в .env")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    model_id = getattr(model, "model", None) or "gpt-3.5-turbo"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(model.api_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException as e:
        raise NetworkError(f"Таймаут при запросе к {model.name}: {e}") from e
    except httpx.HTTPStatusError as e:
        raise NetworkError(
            f"HTTP {e.response.status_code} от {model.name}: {e.response.text}"
        ) from e
    except httpx.RequestError as e:
        raise NetworkError(f"Ошибка запроса к {model.name}: {e}") from e

    # Парсинг ответа OpenAI-совместимого API
    choices = data.get("choices", [])
    if not choices:
        raise NetworkError(f"Пустой ответ от {model.name}")

    content = choices[0].get("message", {}).get("content", "")
    return model.id, content


def send_prompt_to_all_models(
    models: list[Model],
    prompt: str,
    timeout: float = DEFAULT_TIMEOUT,
    max_workers: int = 5,
) -> list[tuple[int, str, Optional[str]]]:
    """
    Отправляет промт во все модели конкурентно.

    Возвращает список кортежей: (model_id, model_name, response_or_error).
    response_or_error — текст ответа или строка с текстом ошибки.
    """
    results: list[tuple[int, str, Optional[str]]] = []
    name_by_id = {m.id: m.name for m in models}

    def task(m: Model):
        try:
            mid, response = send_prompt_to_model(m, prompt, timeout)
            return mid, m.name, response
        except (NetworkError, ApiKeyError) as e:
            return m.id, m.name, str(e)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(task, m): m for m in models}
        for future in as_completed(futures):
            mid, mname, resp = future.result()
            results.append((mid, mname, resp))

    return results
