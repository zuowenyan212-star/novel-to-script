import os
import unittest
from unittest.mock import patch

from backend.config import get_settings


class ConfigTest(unittest.TestCase):
    def test_qiniu_defaults_use_openai_compatible_endpoint(self):
        with patch.dict(os.environ, {"LLM_API_KEY": "test-key"}, clear=True):
            settings = get_settings(provider_override="qiniu")

        self.assertEqual(settings.llm_provider, "qiniu")
        self.assertEqual(settings.base_url, "https://api.qnaigc.com/v1")
        self.assertEqual(settings.model, "deepseek-v3")
        self.assertTrue(settings.uses_remote_llm)

    def test_normalizes_endpoint_suffixes(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "qiniu",
                "LLM_API_KEY": "test-key",
                "LLM_BASE_URL": "https://api.qnaigc.com/v1/messages",
                "LLM_MODEL": "deepseek-v3",
            },
            clear=True,
        ):
            settings = get_settings()

        self.assertEqual(settings.base_url, "https://api.qnaigc.com/v1")


if __name__ == "__main__":
    unittest.main()

