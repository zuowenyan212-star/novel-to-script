import os
from dataclasses import dataclass
from functools import lru_cache

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI 小说转剧本工具"

    # Backward-compatible mock switch. The enhanced UI also supports provider=local.
    use_mock_llm: bool = _to_bool(os.getenv("USE_MOCK_LLM", "false"), False)

    # New generic LLM config. Prefer LLM_* variables, fallback to OPENAI_* variables.
    llm_provider: str = os.getenv("LLM_PROVIDER", "qiniu")
    llm_api_key: str = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.qnaigc.com/v1")
    llm_model: str = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL", "deepseek-v3")
    llm_use_system_proxy: bool = _to_bool(os.getenv("LLM_USE_SYSTEM_PROXY", "false"), False)

    # Backward-compatible aliases used by older code/comments.
    openai_api_key: str = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL", "https://api.qnaigc.com/v1")
    openai_model: str = os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "deepseek-v3")

    max_input_chars: int = int(os.getenv("MAX_INPUT_CHARS", "30000"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
