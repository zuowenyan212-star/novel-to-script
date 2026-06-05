"""Prompt templates for remote LLM generation."""

from __future__ import annotations

from .chapter_parser import Chapter


SYSTEM_PROMPT = """你是一名专业影视剧本改编助手。你必须输出合法 YAML，不要输出解释文字。"""


def build_generation_prompt(
    novel_text: str,
    chapters: list[Chapter],
    style: str,
    adaptation_mode: str,
    detail_level: str,
    language: str,
) -> str:
    chapter_lines = "\n".join(
        f"- {chapter.chapter_id}: {chapter.title}，约 {chapter.word_count} 字，摘要：{chapter.summary}"
        for chapter in chapters
    )
    return f"""
请将下面的多章节小说改编为结构化剧本 YAML。

输出语言：{language}
剧本类型：{style}
改编风格：{adaptation_mode}
场景详细程度：{detail_level}

必须遵守：
1. 只输出 YAML，不要使用 Markdown 代码块。
2. 顶层字段必须包含 schema_version、title、source、logline、theme、characters、scenes。
3. characters 中的角色必须使用 char_001 这样的稳定 ID。
4. scenes 中的 characters 和 dialogue.speaker 必须引用角色 ID。
5. 每个 scene 必须包含 id、source_chapter、title、location、time、characters、summary、action、dialogue、transition。
6. dialogue 每项必须包含 speaker、line、emotion。
7. source.chapters 必须列出所有输入章节 ID 与标题。

章节清单：
{chapter_lines}

小说全文：
{novel_text}
""".strip()


def build_repair_prompt(yaml_text: str, errors: list[str]) -> str:
    error_text = "\n".join(f"- {error}" for error in errors)
    return f"""
下面的 YAML 不符合剧本 Schema。请修复为合法 YAML，只输出修复后的 YAML。

校验错误：
{error_text}

待修复 YAML：
{yaml_text}
""".strip()


def build_revision_prompt(
    existing_yaml: str,
    user_instruction: str,
    style: str,
    adaptation_mode: str,
    detail_level: str,
    language: str,
) -> str:
    return f"""
请根据用户的新一轮要求，修改下面已有的结构化剧本 YAML。

输出语言：{language}
剧本类型：{style}
改编风格：{adaptation_mode}
场景详细程度：{detail_level}

用户要求：
{user_instruction}

必须遵守：
1. 只输出完整 YAML，不要输出解释文字，不要使用 Markdown 代码块。
2. 保留 schema_version、title、source、logline、theme、characters、scenes 等顶层结构。
3. 保持角色 ID、场景 ID、章节引用可校验。
4. scenes.characters 和 dialogue.speaker 必须引用已有或新增 characters 的角色 ID。
5. 如果新增角色、场景或对白，请补齐所有必填字段。
6. 可以在 metadata.revision_history 中记录本轮修改要求。

已有 YAML：
{existing_yaml}
""".strip()
