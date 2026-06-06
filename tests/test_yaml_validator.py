from backend.yaml_validator import validate_yaml_text


def test_validate_script_yaml():
    yaml_text = """
schema_version: "1.0"
title: "测试剧本"
source:
  type: "novel"
  chapters:
    - id: "chapter_001"
      title: "第一章"
characters:
  - id: "char_001"
    name: "林安"
    role: "主角"
    description: "县令"
scenes:
  - id: "scene_001"
    source_chapter: "chapter_001"
    title: "堂前"
    location: "县衙"
    time: "白天"
    characters:
      - "char_001"
    summary: "审案"
    action:
      - "林安走进大堂。"
    dialogue:
      - speaker: "char_001"
        line: "开始审案。"
        emotion: "平静"
    transition: "切走"
"""
    result = validate_yaml_text(yaml_text)
    assert result["valid"] is True
