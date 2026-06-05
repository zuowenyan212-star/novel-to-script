import re
from openai import OpenAI
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

    def generate_text(self, prompt: str) -> str:
        if self.settings.use_mock_llm:
            raise LLMError("当前为 Mock 模式，不调用真实大模型。")

        if not self.settings.openai_api_key:
            raise LLMError("大模型 API Key 未配置，请在 .env 文件中配置 OPENAI_API_KEY，或将 USE_MOCK_LLM=true 用于演示。")

        try:
            client = OpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
            )
            response = client.chat.completions.create(
                model=self.settings.openai_model,
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
