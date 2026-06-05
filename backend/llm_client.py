"""OpenAI-compatible chat completion client."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import Settings
from .prompt_templates import SYSTEM_PROMPT


class LLMConfigurationError(RuntimeError):
    """Raised when a remote provider is selected without required settings."""


class LLMGenerationError(RuntimeError):
    """Raised when a remote model call fails."""


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, prompt: str) -> str | None:
        if not self.settings.uses_remote_llm:
            return None
        if not self.settings.api_key:
            raise LLMConfigurationError("大模型 API Key 未配置，请在 .env 文件中配置 LLM_API_KEY。")
        return self._chat_completion(prompt)

    def _chat_completion(self, prompt: str) -> str:
        url = self.settings.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.35,
        }
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.settings.request_timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMGenerationError(f"大模型接口返回错误：HTTP {exc.code} {detail}") from exc
        except URLError as exc:
            raise LLMGenerationError(f"大模型接口连接失败：{exc.reason}") from exc
        except Exception as exc:
            raise LLMGenerationError(f"大模型调用失败：{exc}") from exc

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMGenerationError("大模型返回结构异常，未找到 choices[0].message.content。") from exc

