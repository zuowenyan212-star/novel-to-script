import os
from dataclasses import dataclass
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


def _to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI 小说转剧本工具"
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    use_mock_llm: bool = _to_bool(os.getenv("USE_MOCK_LLM", "true"), True)
    max_input_chars: int = int(os.getenv("MAX_INPUT_CHARS", "30000"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
