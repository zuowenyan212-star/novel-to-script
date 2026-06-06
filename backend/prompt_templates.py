YAML_SCHEMA_EXAMPLE = """
schema_version: "1.1"
title: "剧本标题"
source:
  type: "novel"
  chapters:
    - id: "chapter_001"
      title: "第一章 雨夜重逢"
logline: "一句话故事梗概"
theme: "故事主题"
adaptation_style: "忠于原文"
characters:
  - id: "char_001"
    name: "角色名"
    role: "主角/配角"
    description: "角色简介"
    goal: "角色目标"
chapter_scripts:
  - chapter_id: "chapter_001"
    chapter_title: "第一章 雨夜重逢"
    summary: "本章剧情摘要"
    scene_ids:
      - "scene_001"
scenes:
  - id: "scene_001"
    source_chapter: "chapter_001"
    title: "场景标题"
    location: "场景地点"
    time: "白天/夜晚/清晨"
    characters:
      - "char_001"
    summary: "本场剧情摘要"
    action:
      - "动作、环境或旁白描述"
    dialogue:
      - id: "dialogue_001"
        speaker: "char_001"
        speaker_name: "角色名"
        line: "台词内容"
        emotion: "情绪或语气"
    transition: "转场说明"
dialogue_index:
  - id: "dialogue_001"
    chapter_id: "chapter_001"
    chapter_title: "第一章 雨夜重逢"
    scene_id: "scene_001"
    speaker: "char_001"
    speaker_name: "角色名"
    line: "台词内容"
    emotion: "情绪或语气"
"""


ADAPTATION_STYLE_TEXT = {
    "faithful": "忠于原文：尽量保持原文事件顺序、人物动机和台词语义，不额外增加过多冲突。",
    "dramatic": "增强戏剧冲突化：在不改变主线事实的前提下，强化场景冲突、悬念、情绪张力和转场节奏。",
    "colloquial": "口语化：让台词更自然、更适合演员直接表演，减少书面化表达。",
}


def build_generation_prompt(novel_text: str, chapters_payload: dict, style: str, language: str, adaptation_style: str = "faithful") -> str:
    chapter_lines = []
    for chapter in chapters_payload.get("chapters", []):
        chapter_lines.append(
            f"- {chapter['chapter_id']} | {chapter['title']} | {chapter['word_count']}字 | {chapter.get('summary', '')}"
        )
    chapter_overview = "\n".join(chapter_lines)
    adaptation_instruction = ADAPTATION_STYLE_TEXT.get(adaptation_style, ADAPTATION_STYLE_TEXT["faithful"])

    return f"""
你是一个专业剧本编剧和 YAML 结构化数据专家。请将用户提供的多章节小说文本改编为结构化 YAML 剧本。

## 输出要求
- 只输出 YAML，不要输出解释文字、Markdown 代码块或额外说明。
- 剧本类型：{style}
- 输出语言：{language}
- 改编风格：{adaptation_instruction}
- 必须严格遵循下面的 YAML Schema。
- schema_version 使用 "1.1"。
- 必须按照章节组织输出 chapter_scripts，每个章节需要引用该章节下的场景 id。
- 必须将所有对白额外汇总到顶层 dialogue_index 中，标清 chapter_id、scene_id、speaker、speaker_name、line、emotion。
- 人物需要统一放在 characters 中，并使用 char_001 这种稳定 id。
- scenes[].characters 必须引用 characters 中已经存在的角色 id。
- scenes[].dialogue[].speaker 和 dialogue_index[].speaker 必须引用 characters 中已经存在的角色 id。
- 小说中的动作、环境描写、心理描写，优先改写到 action 字段。
- 人物说的话放到 dialogue 字段，不要把动作描写混入 line。
- 每个场景必须包含 id、source_chapter、title、location、time、characters、summary、action、dialogue、transition。
- 每个场景 id 必须唯一，格式为 scene_001。
- 每条对白 id 必须唯一，格式为 dialogue_001。
- source.chapters 必须保留解析出的章节 id 和标题。
- YAML 缩进使用两个空格，确保可被 PyYAML 正常解析。

## YAML Schema 示例
{YAML_SCHEMA_EXAMPLE}

## 已解析章节
{chapter_overview}

## 小说文本
{novel_text}
""".strip()


def build_repair_prompt(bad_yaml: str, errors: list, adaptation_style: str = "faithful") -> str:
    error_text = "\n".join(f"- {e}" for e in errors)
    return f"""
你是 YAML 修复助手。下面是一段不符合 Schema 的 YAML，请根据错误原因修复它。

## 修复要求
- 只输出修复后的 YAML，不要输出解释文字。
- 保持原始内容含义，不要凭空大幅扩写。
- 确保可以被 PyYAML 解析。
- 确保必填字段完整。
- 确保角色 id 与场景引用一致。
- 确保包含 chapter_scripts 和 dialogue_index。
- 确保每条对白都有 id、speaker、speaker_name、line、emotion。

## Schema 示例
{YAML_SCHEMA_EXAMPLE}

## 错误原因
{error_text}

## 待修复 YAML
{bad_yaml}
""".strip()
