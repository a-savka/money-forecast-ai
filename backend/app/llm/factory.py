from app.config import get_settings
from app.llm.base import LLMError, LLMProvider
from app.llm.mock import MockProvider


def available_providers() -> list[str]:
    """Провайдеры, для которых заданы ключи (mock доступен всегда)."""
    s = get_settings()
    out = ["mock"]
    if s.gigachat_auth_key:
        out.append("gigachat")
    if s.yandex_api_key and s.yandex_folder_id:
        out.append("yandexgpt")
    return out


def get_provider(name: str | None = None) -> LLMProvider:
    name = name or get_settings().llm_provider
    if name == "mock":
        return MockProvider()
    if name not in available_providers():
        raise LLMError(f"Провайдер {name} не настроен: задайте ключи в .env")
    if name == "gigachat":
        from app.llm.gigachat import GigaChatProvider

        return GigaChatProvider.from_settings()
    if name == "yandexgpt":
        from app.llm.yandexgpt import YandexGPTProvider

        return YandexGPTProvider.from_settings()
    raise LLMError(f"Неизвестный LLM-провайдер: {name}")
