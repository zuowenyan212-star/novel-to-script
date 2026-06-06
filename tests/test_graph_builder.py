from backend.graph_builder import build_character_graph_from_yaml


def test_build_character_graph_from_yaml():
    yaml_text = """
schema_version: "1.0"
title: "测试"
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
  - id: "char_002"
    name: "周伯"
    role: "配角"
    description: "师爷"
scenes:
  - id: "scene_001"
    source_chapter: "chapter_001"
    title: "县衙"
    location: "县衙"
    time: "清晨"
    characters:
      - "char_001"
      - "char_002"
    summary: "二人同场"
    action:
      - "林安走进县衙。"
    dialogue:
      - speaker: "char_001"
        line: "开始吧。"
        emotion: "平静"
    transition: "切至下一场"
"""
    graph = build_character_graph_from_yaml(yaml_text)
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["weight"] == 1
