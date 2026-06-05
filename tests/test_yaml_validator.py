import os
import unittest

from backend.chapter_parser import parse_chapters
from backend.script_generator import chat_turn_payload, generate_local_script, generate_script_payload
from backend.yaml_codec import dump_yaml, load_yaml
from backend.yaml_validator import validate_script_data, validate_yaml_text


SAMPLE = """《雨灯档案》

第一章 雨夜重逢
林舟推门走进咖啡馆。
苏晚：你父亲当年调查的旧案，没有结束。
林舟：我回来，不是为了翻旧账。

第二章 旧仓库
林舟来到旧仓库，发现录音机。
苏晚：当年唯一的目击者，他昨晚联系过我。

第三章 天台黎明
黎明前，两人赶到老报社天台。
林舟：如果真相会伤到所有人呢？
苏晚：那也比继续沉默好。
"""


class YamlValidatorTest(unittest.TestCase):
    def test_local_script_matches_schema(self):
        chapters = parse_chapters(SAMPLE)
        script = generate_local_script(chapters, "影视剧本", "忠于原文", "标准", "zh-CN")
        report = validate_script_data(script)

        self.assertTrue(report.valid, report.errors)

    def test_yaml_dump_can_be_validated(self):
        chapters = parse_chapters(SAMPLE)
        script = generate_local_script(chapters, "影视剧本", "忠于原文", "标准", "zh-CN")
        yaml_text = dump_yaml(script)
        loaded = load_yaml(yaml_text)
        report = validate_yaml_text(yaml_text)

        self.assertEqual(loaded["schema_version"], "1.0")
        self.assertTrue(report.valid, report.errors)

    def test_generate_payload_uses_mock_provider(self):
        os.environ["LLM_PROVIDER"] = "mock"
        result = generate_script_payload(SAMPLE)

        self.assertTrue(result["success"], result.get("error"))
        self.assertIn("yaml", result)
        self.assertEqual(result["chapter_count"], 3)
        self.assertEqual(result["model_mode"], "local")

    def test_chat_turn_revises_existing_yaml_locally(self):
        os.environ["LLM_PROVIDER"] = "mock"
        generated = generate_script_payload(SAMPLE)
        revised = chat_turn_payload("把对白更口语化，并加强冲突", existing_yaml=generated["yaml"])

        self.assertTrue(revised["success"], revised.get("error"))
        self.assertIn("revision_history", revised["yaml"])
        self.assertIn("强化戏剧冲突", revised["yaml"])


if __name__ == "__main__":
    unittest.main()
