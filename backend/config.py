"""Runtime configuration for local demo and OpenAI-compatible providers."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QINIU_DEFAULT_BASE_URL = "https://api.qnaigc.com/v1"
QINIU_DEFAULT_MODEL = "deepseek-v3"
OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "mock"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    request_timeout: int = 60
    use_system_proxy: bool = False

    @property
    def uses_remote_llm(self) -> bool:
        return self.llm_provider.lower() not in {"mock", "local", "demo", ""}


def get_settings(provider_override: str | None = None) -> Settings:
    _load_env_file(PROJECT_ROOT / ".env")
    provider = (provider_override or _env_first("LLM_PROVIDER", "mock")).strip() or "mock"
    provider_key = provider.lower()
    default_base_url = QINIU_DEFAULT_BASE_URL if provider_key == "qiniu" else OPENAI_DEFAULT_BASE_URL
    default_model = QINIU_DEFAULT_MODEL if provider_key == "qiniu" else OPENAI_DEFAULT_MODEL
    return Settings(
        llm_provider=provider,
        api_key=_env_first("LLM_API_KEY", "QINIU_API_KEY", "OPENAI_API_KEY", "").strip(),
        base_url=_normalize_base_url(_env_first("LLM_BASE_URL", "QINIU_BASE_URL", default_base_url).strip()),
        model=_env_first("LLM_MODEL", "QINIU_MODEL", default_model).strip(),
        request_timeout=int(os.getenv("LLM_TIMEOUT", "60")),
        use_system_proxy=_env_bool("LLM_USE_SYSTEM_PROXY", default=False),
    )


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(path)
        return
    except Exception:
        pass

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _env_first(*names_or_default: str) -> str:
    *names, default = names_or_default
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def _normalize_base_url(base_url: str) -> str:
    cleaned = (base_url or "").strip().rstrip("/")
    for suffix in ("/chat/completions", "/messages", "/models"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
    return cleaned or OPENAI_DEFAULT_BASE_URL


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
