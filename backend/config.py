import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def _manual_load_dotenv() -> None:
    """Small .env loader used by quick-start mode without python-dotenv."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


if load_dotenv is not None:
    load_dotenv()
else:
    _manual_load_dotenv()


def _to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _clean(value: Optional[str], default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip().strip('"').strip("'")


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI 小说转剧本工具"

    # Backward-compatible mock switch. The enhanced UI also supports provider=local.
    use_mock_llm: bool = _to_bool(os.getenv("USE_MOCK_LLM", "false"), False)

    # Generic LLM config. Prefer LLM_* variables, fallback to OPENAI_* variables.
    llm_provider: str = _clean(os.getenv("LLM_PROVIDER"), "qiniu")
    llm_api_key: str = _clean(os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"), "")
    llm_base_url: str = _clean(os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL"), "https://api.qnaigc.com/v1")
    llm_model: str = _clean(os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL"), "deepseek-v3")
    llm_use_system_proxy: bool = _to_bool(os.getenv("LLM_USE_SYSTEM_PROXY", "false"), False)

    # Backward-compatible aliases used by older code/comments.
    openai_api_key: str = _clean(os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"), "")
    openai_base_url: str = _clean(os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL"), "https://api.qnaigc.com/v1")
    openai_model: str = _clean(os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL"), "deepseek-v3")

    max_input_chars: int = int(os.getenv("MAX_INPUT_CHARS", "30000"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
