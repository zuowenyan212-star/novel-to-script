YAML_SCHEMA_EXAMPLE = """
schema_version: "1.0"
title: "剧本标题"
source:
  type: "novel"
  chapters:
    - id: "chapter_001"
      title: "第一章 雨夜重逢"
logline: "一句话故事梗概"
theme: "故事主题"
characters:
  - id: "char_001"
    name: "角色名"
    role: "主角/配角"
    description: "角色简介"
    goal: "角色目标"
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
      - speaker: "char_001"
        line: "台词内容"
        emotion: "情绪或语气"
    transition: "转场说明"
"""


def build_generation_prompt(novel_text: str, chapters_payload: dict, style: str, language: str) -> str:
    chapter_lines = []
    for chapter in chapters_payload.get("chapters", []):
        chapter_lines.append(
            f"- {chapter['chapter_id']} | {chapter['title']} | {chapter['word_count']}字 | {chapter.get('summary', '')}"
        )
    chapter_overview = "\n".join(chapter_lines)

    return f"""
你是一个专业剧本编剧和 YAML 结构化数据专家。请将用户提供的多章节小说文本改编为结构化 YAML 剧本。

## 输出要求
- 只输出 YAML，不要输出解释文字、Markdown 代码块或额外说明。
- 剧本类型：{style}
- 输出语言：{language}
- 必须严格遵循下面的 YAML Schema。
- 人物需要统一放在 characters 中，并使用 char_001 这种稳定 id。
- scenes[].characters 必须引用 characters 中已经存在的角色 id。
- dialogue[].speaker 必须引用 characters 中已经存在的角色 id。
- 小说中的动作、环境描写、心理描写，优先改写到 action 字段。
- 人物说的话放到 dialogue 字段，不要把动作描写混入 line。
- 每个场景必须包含 id、source_chapter、title、location、time、characters、summary、action、dialogue、transition。
- 每个场景 id 必须唯一，格式为 scene_001。
- 每个角色 id 必须唯一，格式为 char_001。
- source.chapters 必须保留解析出的章节 id 和标题。
- YAML 缩进使用两个空格，确保可被 PyYAML 正常解析。

## YAML Schema 示例
{YAML_SCHEMA_EXAMPLE}

## 已解析章节
{chapter_overview}

## 小说文本
{novel_text}
""".strip()


def build_repair_prompt(bad_yaml: str, errors: list[str]) -> str:
    error_text = "\n".join(f"- {e}" for e in errors)
    return f"""
你是 YAML 修复助手。下面是一段不符合 Schema 的 YAML，请根据错误原因修复它。

## 修复要求
- 只输出修复后的 YAML，不要输出解释文字。
- 保持原始内容含义，不要凭空大幅扩写。
- 确保可以被 PyYAML 解析。
- 确保必填字段完整。
- 确保角色 id 与场景引用一致。

## Schema 示例
{YAML_SCHEMA_EXAMPLE}

## 错误原因
{error_text}

## 待修复 YAML
{bad_yaml}
""".strip()
