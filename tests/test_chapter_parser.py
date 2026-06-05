from backend.chapter_parser import parse_chapters


def test_parse_chinese_chapters():
    text = """
第一章 开端
林安说道：“开始。”

第二章 发展
周伯说道：“有案子。”

第三章 结尾
商人说道：“冤枉。”
"""
    chapters = parse_chapters(text)
    assert len(chapters) == 3
    assert chapters[0].chapter_id == "chapter_001"
    assert "第一章" in chapters[0].title
    assert chapters[0].word_count > 0
