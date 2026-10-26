"""Проверка подключения к LLM-провайдеру с реальным ключом из .env.

uv run python -m scripts.llm_smoke gigachat
uv run python -m scripts.llm_smoke yandexgpt
"""

import sys

from pydantic import BaseModel

from app.llm import get_provider, structured_call


class SmokeAnswer(BaseModel):
    capital: str
    population_mln: float


def main() -> None:
    provider = get_provider(sys.argv[1] if len(sys.argv) > 1 else None)
    res = structured_call(
        provider,
        "Ты — справочник. Отвечай кратко.",
        "Назови столицу России и её население в миллионах.",
        SmokeAnswer,
        use_cache=False,
    )
    print(f"{res.provider}/{res.model}: {res.data} | {res.usage} | {res.latency_ms} мс")


if __name__ == "__main__":
    main()
