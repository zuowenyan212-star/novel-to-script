"""Utilities for detecting and summarizing novel chapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Iterable


CHAPTER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*第[零〇一二三四五六七八九十百千万两\d]+[章节回卷部篇]\s*[:：、.\-]?\s*(.*)$", re.IGNORECASE),
    re.compile(r"^\s*chapter\s+\d+\s*[:：、.\-]?\s*(.*)$", re.IGNORECASE),
    re.compile(r"^\s*[一二三四五六七八九十]+、\s*(.+)$"),
    re.compile(r"^\s*\d+[、.．]\s*(.+)$"),
)


@dataclass(frozen=True)
class Chapter:
    chapter_id: str
    title: str
    content: str
    word_count: int
    summary: str

    def to_public_dict(self, include_content: bool = False) -> dict[str, object]:
        data = asdict(self)
        if not include_content:
            data.pop("content", None)
        return data


def parse_chapters(novel_text: str) -> list[Chapter]:
    """Split a novel into chapters by common Chinese and English headings."""
    normalized = _normalize_text(novel_text)
    if not normalized:
        return []

    lines = normalized.split("\n")
    headings: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped and _is_chapter_heading(stripped):
            headings.append((index, stripped))

    if not headings:
        return [
            Chapter(
                chapter_id="chapter_001",
                title="未命名章节",
                content=normalized,
                word_count=count_words(normalized),
                summary=summarize_text(normalized),
            )
        ]

    chapters: list[Chapter] = []
    for chapter_index, (line_index, title) in enumerate(headings, start=1):
        next_line = headings[chapter_index][0] if chapter_index < len(headings) else len(lines)
        content = "\n".join(lines[line_index + 1 : next_line]).strip()
        if not content:
            content = title
        chapters.append(
            Chapter(
                chapter_id=f"chapter_{chapter_index:03d}",
                title=title,
                content=content,
                word_count=count_words(content),
                summary=summarize_text(content),
            )
        )
    return chapters


def count_words(text: str) -> int:
    """Count CJK characters plus Latin word-like tokens."""
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_count = len(re.findall(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*", text))
    return cjk_count + latin_count


def summarize_text(text: str, max_length: int = 120) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return ""
    sentences = re.findall(r".+?[。！？!?]", clean)
    summary = "".join(sentences[:2]).strip() if sentences else clean
    if len(summary) > max_length:
        return summary[: max_length - 1].rstrip() + "..."
    return summary


def chapters_to_public(chapters: Iterable[Chapter], include_content: bool = False) -> list[dict[str, object]]:
    return [chapter.to_public_dict(include_content=include_content) for chapter in chapters]


def _normalize_text(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _is_chapter_heading(line: str) -> bool:
    if len(line) > 40:
        return False
    if line.endswith(("。", "！", "？", "!", "?")):
        return False
    return any(pattern.match(line) for pattern in CHAPTER_PATTERNS)

