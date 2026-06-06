\
import re
from dataclasses import dataclass, asdict
from typing import List


CHINESE_NUMERAL = "一二三四五六七八九十百千万两〇零"
CHAPTER_PATTERNS = [
    # 第一章 / 第1章 / 第 1 章：标题
    re.compile(r"^\s*(第\s*[0-9%s]+\s*章[^\n\r]*)\s*$" % CHINESE_NUMERAL, re.MULTILINE),
    # Chapter 1 / CHAPTER 01
    re.compile(r"^\s*((?:Chapter|CHAPTER)\s*[0-9]+[^\n\r]*)\s*$", re.MULTILINE),
    # 一、开端 / 1、开端
    re.compile(r"^\s*([%s0-9]{1,4}\s*[、.．]\s*[^\n\r]+)\s*$" % CHINESE_NUMERAL, re.MULTILINE),
]


@dataclass
class Chapter:
    chapter_id: str
    title: str
    content: str
    word_count: int
    summary: str = ""

    def to_dict(self):
        return asdict(self)


def count_words(text: str) -> int:
    """A simple mixed Chinese/English length counter for demo use."""
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    english_words = re.findall(r"[A-Za-z0-9_]+", text)
    return len(chinese_chars) + len(english_words)


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def summarize_content(content: str, max_len: int = 80) -> str:
    """Rule-based short summary used for chapter parsing display."""
    content = re.sub(r"\s+", "", content)
    if not content:
        return ""
    return content[:max_len] + ("…" if len(content) > max_len else "")


def _find_headings(text: str):
    matches = []
    for pattern in CHAPTER_PATTERNS:
        for match in pattern.finditer(text):
            heading = match.group(1).strip()
            matches.append((match.start(), match.end(), heading))
    # Deduplicate by start position, then sort.
    unique = {}
    for start, end, heading in matches:
        unique[start] = (start, end, heading)
    return sorted(unique.values(), key=lambda x: x[0])


def parse_chapters(novel_text: str) -> List[Chapter]:
    """
    Parse novel text into chapters. Supports:
    - 第一章 / 第1章
    - Chapter 1
    - 一、开端
    If no clear heading is found, paragraphs are grouped into one pseudo chapter.
    """
    text = clean_text(novel_text)
    if not text:
        return []

    headings = _find_headings(text)
    chapters: List[Chapter] = []

    if not headings:
        return [
            Chapter(
                chapter_id="chapter_001",
                title="未命名章节",
                content=text,
                word_count=count_words(text),
                summary=summarize_content(text),
            )
        ]

    for idx, (start, end, heading) in enumerate(headings):
        next_start = headings[idx + 1][0] if idx + 1 < len(headings) else len(text)
        content = text[end:next_start].strip()
        if not content and idx == 0:
            continue
        chapter = Chapter(
            chapter_id=f"chapter_{idx + 1:03d}",
            title=heading,
            content=content,
            word_count=count_words(content),
            summary=summarize_content(content),
        )
        chapters.append(chapter)

    return chapters


def parse_chapters_payload(novel_text: str) -> dict:
    chapters = parse_chapters(novel_text)
    return {
        "chapter_count": len(chapters),
        "total_word_count": sum(c.word_count for c in chapters),
        "chapters": [
            {
                "chapter_id": c.chapter_id,
                "title": c.title,
                "word_count": c.word_count,
                "summary": c.summary,
            }
            for c in chapters
        ],
    }
