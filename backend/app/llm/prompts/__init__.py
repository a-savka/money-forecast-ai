from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


@cache
def load_prompt(name: str) -> str:
    """Промпты хранятся файлами с версией в имени — сравнения воспроизводимы."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()
