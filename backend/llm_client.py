import re
from .config import get_settings


class LLMError(RuntimeError):
    pass


def strip_markdown_fence(text: str) -> str:
    """Remove ```yaml fences if the model returns them."""
    if not text:
        return ""
    text = text.strip()
    fenced = re.match(r"^```(?:yaml|yml)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text


class LLMClient:
    def __init__(self):
        self.settings = get_settings()

    def is_mock(self) -> bool:
        return self.settings.use_mock_llm

    def generate_text(self, prompt: str, provider: str = "qiniu", model: str | None = None) -> str:
        provider = (provider or self.settings.llm_provider or "qiniu").lower()

        if provider == "local":
            raise LLMError("local provider should be handled by the rule-based generator before calling LLMClient.")

        if provider != "qiniu":
            raise LLMError(f"暂不支持的模型提供方：{provider}")

        api_key = self.settings.llm_api_key or self.settings.openai_api_key
        base_url = self.settings.llm_base_url or self.settings.openai_base_url or "https://api.qnaigc.com/v1"
        selected_model = model or self.settings.llm_model or self.settings.openai_model or "deepseek-v3"

        if not api_key:
            raise LLMError("七牛云 API Key 未配置，请在 .env 文件中配置 LLM_API_KEY，或在页面选择“本地演示模型”。")

        try:
            from openai import OpenAI
        except Exception as exc:
            raise LLMError("缺少 openai 依赖，请先执行 pip install -r requirements.txt") from exc

        try:
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": "你是专业编剧和结构化 YAML 输出专家。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            content = response.choices[0].message.content or ""
            return strip_markdown_fence(content)
        except Exception as exc:
            raise LLMError(f"AI 生成失败：{exc}") from exc
