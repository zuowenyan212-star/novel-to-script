import unittest

from backend.chapter_parser import parse_chapters


SAMPLE = """第一章 雨夜
林舟回到咖啡馆。

第二章 旧仓库
苏晚发现录音机。

Chapter 3 Rooftop
两人在天台等待黎明。
"""


class ChapterParserTest(unittest.TestCase):
    def test_parse_common_heading_formats(self):
        chapters = parse_chapters(SAMPLE)

        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0].chapter_id, "chapter_001")
        self.assertEqual(chapters[1].title, "第二章 旧仓库")
        self.assertGreater(chapters[2].word_count, 0)

    def test_returns_single_unnamed_chapter_without_headings(self):
        chapters = parse_chapters("没有章节标题的正文。")

        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0].title, "未命名章节")


if __name__ == "__main__":
    unittest.main()

