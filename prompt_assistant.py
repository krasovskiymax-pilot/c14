"""
AI-ассистент для улучшения промтов.
Отправляет промт в модель с инструкцией вернуть улучшенную версию.
"""
from models import Model
from network import send_prompt_to_model, NetworkError, ApiKeyError

SYSTEM_PROMPT = """Ты помощник по улучшению промтов для нейросетей.
Пользователь пришлёт исходный промт. Верни в следующем формате:

УЛУЧШЕННЫЙ:
<улучшенная версия промта, более ясная и эффективная>

ВАРИАНТ 2:
<альтернативная формулировка>

ВАРИАНТ 3:
<ещё один вариант>

Отвечай только текстом в этом формате, без лишних пояснений."""


def improve_prompt(prompt_text: str, model: Model) -> str:
    """
    Отправляет промт в модель для улучшения.
    Возвращает ответ модели (улучшенный промт и варианты) или строку с ошибкой.
    """
    try:
        _, response = send_prompt_to_model(model, prompt_text, system=SYSTEM_PROMPT)
        return response or "(Пустой ответ)"
    except (NetworkError, ApiKeyError) as e:
        return str(e)
    except Exception as e:
        return f"Ошибка: {e}"


def parse_improved_response(text: str) -> dict:
    """
    Парсит ответ модели в структуру.
    Возвращает: {"improved": str, "alternatives": list[str]}.
    """
    result = {"improved": "", "alternatives": []}
    raw = text.strip()
    if not raw:
        return result

    lines = raw.split("\n")
    current_section = None
    current_text = []

    def flush():
        t = "\n".join(current_text).strip()
        if not t:
            return
        if current_section == "improved":
            result["improved"] = t
        elif current_section in ("alt2", "alt3"):
            result["alternatives"].append(t)

    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()
        if "УЛУЧШЕННЫЙ:" in upper:
            flush()
            current_section = "improved"
            idx = upper.find("УЛУЧШЕННЫЙ:") + len("УЛУЧШЕННЫЙ:")
            rest = stripped[idx:].strip() if idx < len(stripped) else ""
            current_text = [rest] if rest else []
        elif "ВАРИАНТ 2:" in upper:
            flush()
            current_section = "alt2"
            idx = upper.find("ВАРИАНТ 2:") + len("ВАРИАНТ 2:")
            rest = stripped[idx:].strip() if idx < len(stripped) else ""
            current_text = [rest] if rest else []
        elif "ВАРИАНТ 3:" in upper:
            flush()
            current_section = "alt3"
            idx = upper.find("ВАРИАНТ 3:") + len("ВАРИАНТ 3:")
            rest = stripped[idx:].strip() if idx < len(stripped) else ""
            current_text = [rest] if rest else []
        elif current_section:
            current_text.append(line)
    flush()

    if not result["improved"] and result["alternatives"]:
        result["improved"] = result["alternatives"][0]
    elif not result["improved"]:
        result["improved"] = raw
    return result
