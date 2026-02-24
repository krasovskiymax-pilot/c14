"""
Модуль отправки HTTP-запросов к API нейросетей.
Использует requests (стабильнее httpx на Windows).
"""
import json
from typing import Optional

import requests

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
    """
    api_key = get_api_key(model.api_id)
    if not api_key or not str(api_key).strip():
        raise ApiKeyError(
            f"Переменная {model.api_id} не найдена в .env или пуста. "
            f"Добавьте {model.api_id}=ваш_ключ в .env или .env.local"
        )

    api_key = str(api_key).strip()
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
        resp = requests.post(
            model.api_url, json=payload, headers=headers, timeout=timeout
        )
        resp.raise_for_status()
        text = resp.text
        if not text or not text.strip():
            raise NetworkError(f"Пустой ответ от {model.name}")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            preview = text[:200] + "…" if len(text) > 200 else text
            raise NetworkError(
                f"Неверный JSON от {model.name}: {e}. Тело: {preview}"
            ) from e
    except requests.Timeout as e:
        raise NetworkError(f"Таймаут при запросе к {model.name}: {e}") from e
    except requests.HTTPError as e:
        r = e.response
        code = r.status_code if r else 0
        err_text = r.text if r else str(e)
        raise NetworkError(f"HTTP {code} от {model.name}: {err_text}") from e
    except requests.RequestException as e:
        raise NetworkError(f"Ошибка запроса к {model.name}: {e}") from e

    choices = data.get("choices", [])
    if not choices:
        raise NetworkError(f"Пустой ответ от {model.name}")

    content = choices[0].get("message", {}).get("content", "")
    return model.id, content


def send_prompt_to_all_models(
    models: list[Model],
    prompt: str,
    timeout: float = DEFAULT_TIMEOUT,
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
        except Exception as e:
            return m.id, m.name, f"Ошибка: {e}"

    # Последовательное выполнение (избегаем крашей при многопоточности на Windows)
    for m in models:
        mid, mname, resp = task(m)
        results.append((mid, mname, resp))

    return results
