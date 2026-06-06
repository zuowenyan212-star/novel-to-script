from backend.graph_builder import build_character_graph_from_yaml
from backend.visual_assistant import generate_video_assist


def test_v04_graph_detects_hostile_and_friendly_edges():
    yaml_text = """
schema_version: "1.1"
title: "关系测试"
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
    role: "盟友"
    description: "师爷"
  - id: "char_003"
    name: "柳风"
    role: "反派"
    description: "敌人"
scenes:
  - id: "scene_001"
    source_chapter: "chapter_001"
    title: "并肩查案"
    location: "县衙"
    time: "清晨"
    characters:
      - "char_001"
      - "char_002"
    summary: "周伯帮助林安查案，二人互相信任并肩行动。"
    action:
      - "周伯扶起林安，二人并肩作战。"
    dialogue: []
    transition: "切换"
  - id: "scene_002"
    source_chapter: "chapter_001"
    title: "堂前对峙"
    location: "县衙"
    time: "夜晚"
    characters:
      - "char_001"
      - "char_003"
    summary: "柳风威胁林安，二人激烈对峙。"
    action:
      - "柳风冷笑着拔剑，林安怒视他。"
    dialogue: []
    transition: "切换"
"""
    graph = build_character_graph_from_yaml(yaml_text)
    relations = {
        tuple(sorted([edge["source"], edge["target"]])): edge["relation"]
        for edge in graph["edges"]
    }

    assert relations[("char_001", "char_002")] == "friendly"
    assert relations[("char_001", "char_003")] == "hostile"


def test_v04_video_assist_disabled_for_local_provider():
    result = generate_video_assist(
        novel_text="第一章 开端\n第二章 发展\n第三章 结尾",
        yaml_text="title: 测试",
        provider="local",
        model="local-rule",
        visual_style="manga",
    )
    assert result["success"] is False
    assert "大模型" in result["message"]
    assert result["storyboard"] == []
