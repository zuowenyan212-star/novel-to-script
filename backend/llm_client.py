import json
import re
import ssl
from typing import Any, Dict, Optional
from urllib import request, error

from .config import get_settings


class LLMError(RuntimeError):
    pass


def strip_markdown_fence(text: str) -> str:
    """Remove ```yaml fences if the model returns them."""
    if not text:
        return ""
    text = text.strip()
    fenced = re.match(r"^```(?:yaml|yml|json)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text


def _clean_env_value(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip().strip('"').strip("'")


def _normalize_base_url(base_url: str) -> str:
    """Normalize Qiniu/OpenAI-compatible base URL.

    Accepted examples:
    - https://api.qnaigc.com
    - https://api.qnaigc.com/v1
    - https://api.qnaigc.com/v1/
    - https://api.qnaigc.com/v1/chat/completions
    """
    base_url = _clean_env_value(base_url) or "https://api.qnaigc.com/v1"
    base_url = base_url.rstrip("/")

    if base_url.endswith("/chat/completions"):
        base_url = base_url[: -len("/chat/completions")].rstrip("/")

    if not base_url.endswith("/v1"):
        base_url = base_url + "/v1"

    return base_url


def _format_http_error(status_code: int, body: str) -> str:
    body = (body or "").strip()
    if len(body) > 700:
        body = body[:700] + "..."
    return f"模型接口返回错误 HTTP {status_code}：{body}"


class LLMClient:
    def __init__(self):
        self.settings = get_settings()

    def is_mock(self) -> bool:
        return self.settings.use_mock_llm

    def _get_qiniu_config(self, model: Optional[str]) -> Dict[str, str]:
        api_key = _clean_env_value(self.settings.llm_api_key or self.settings.openai_api_key)
        base_url = _normalize_base_url(self.settings.llm_base_url or self.settings.openai_base_url)
        selected_model = _clean_env_value(model) or _clean_env_value(self.settings.llm_model or self.settings.openai_model) or "deepseek-v3"

        # If frontend accidentally sends local model value while provider=qiniu,
        # fall back to configured Qiniu model instead of calling an invalid model.
        if selected_model.lower() in {"local", "local-rule", "本地演示模型"}:
            selected_model = _clean_env_value(self.settings.llm_model or self.settings.openai_model) or "deepseek-v3"

        invalid_keys = {
            "",
            "your_qiniu_api_key_here",
            "your_api_key",
            "你的七牛云api_key",
            "你的七牛云API_KEY",
            "你的七牛云api key",
        }
        if api_key in invalid_keys:
            raise LLMError("七牛云 API Key 未配置。请在项目根目录 .env 中配置 LLM_API_KEY，或启动时按提示输入 API Key。")

        return {
            "api_key": api_key,
            "base_url": base_url,
            "model": selected_model,
        }

    def generate_text(self, prompt: str, provider: str = "qiniu", model: Optional[str] = None) -> str:
        provider = (provider or self.settings.llm_provider or "qiniu").lower()

        if provider == "local":
            raise LLMError("local provider should be handled by the rule-based generator before calling LLMClient.")

        if provider != "qiniu":
            raise LLMError(f"暂不支持的模型提供方：{provider}")

        cfg = self._get_qiniu_config(model)
        return self._call_chat_completions(prompt, cfg)

    def _call_chat_completions(self, prompt: str, cfg: Dict[str, str]) -> str:
        url = cfg["base_url"].rstrip("/") + "/chat/completions"
        payload: Dict[str, Any] = {
            "model": cfg["model"],
            "messages": [
                {"role": "system", "content": "你是专业编剧和结构化 YAML 输出专家。只输出合法 YAML，不输出 Markdown 代码块。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "stream": False,
        }

        data = self._post_json(url, cfg["api_key"], payload)
        choices = data.get("choices") or []
        if not choices:
            raise LLMError(f"模型接口未返回 choices 字段：{str(data)[:500]}")

        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        if not content:
            raise LLMError(f"模型接口返回内容为空：{str(data)[:500]}")

        return strip_markdown_fence(content)

    def _post_json(self, url: str, api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST JSON without requiring third-party dependencies.

        Quick-start mode does not install requirements, so this uses urllib from
        the Python standard library. Full FastAPI mode can use the same path.
        """
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url,
            data=raw,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        # LLM_USE_SYSTEM_PROXY=false means avoid environment proxies in quick demos.
        # Set it to true if the user's network needs a system proxy.
        if self.settings.llm_use_system_proxy:
            opener = request.build_opener()
        else:
            opener = request.build_opener(request.ProxyHandler({}))

        try:
            with opener.open(req, timeout=120, context=ssl.create_default_context()) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                status = getattr(resp, "status", 200)
        except TypeError:
            # Some Python builds do not accept context in opener.open.
            try:
                with opener.open(req, timeout=120) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    status = getattr(resp, "status", 200)
            except error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                raise LLMError(_format_http_error(exc.code, body)) from exc
            except error.URLError as exc:
                raise LLMError(
                    f"无法连接模型接口，请检查网络、LLM_BASE_URL 和代理设置。当前地址：{url}。"
                    "如果需要走系统代理，请设置 LLM_USE_SYSTEM_PROXY=true。"
                ) from exc
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise LLMError(_format_http_error(exc.code, body)) from exc
        except error.URLError as exc:
            raise LLMError(
                f"无法连接模型接口，请检查网络、LLM_BASE_URL 和代理设置。当前地址：{url}。"
                "如果需要走系统代理，请设置 LLM_USE_SYSTEM_PROXY=true。"
            ) from exc
        except TimeoutError as exc:
            raise LLMError(f"模型接口请求超时。当前地址：{url}，模型：{payload.get('model')}") from exc
        except Exception as exc:
            raise LLMError(f"AI 生成失败：{exc}") from exc

        if status >= 400:
            raise LLMError(_format_http_error(status, body))

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LLMError(f"模型接口返回的不是合法 JSON：{body[:500]}") from exc

        if not isinstance(parsed, dict):
            raise LLMError(f"模型接口返回结构异常：{str(parsed)[:500]}")
        return parsed
