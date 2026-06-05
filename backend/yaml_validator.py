"""Schema validation and light repair for generated script YAML."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .yaml_codec import dump_yaml, load_yaml


@dataclass
class ValidationReport:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.valid = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def as_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors, "warnings": self.warnings}


def validate_yaml_text(yaml_text: str) -> ValidationReport:
    try:
        data = load_yaml(yaml_text)
    except Exception as exc:
        report = ValidationReport(valid=False)
        report.add_error(f"YAML 解析失败：{exc}")
        return report
    return validate_script_data(data)


def validate_script_data(data: Any) -> ValidationReport:
    report = ValidationReport()
    if not isinstance(data, dict):
        report.add_error("根节点必须是对象。")
        return report

    for key in ["schema_version", "title", "source", "logline", "theme", "characters", "scenes"]:
        if key not in data:
            report.add_error(f"缺少顶层字段：{key}")

    source = data.get("source")
    if not isinstance(source, dict):
        report.add_error("source 必须是对象。")
        source = {}
    chapters = source.get("chapters", []) if isinstance(source, dict) else []
    if not isinstance(chapters, list) or not chapters:
        report.add_error("source.chapters 必须是非空列表。")
        chapters = []

    chapter_ids = _validate_chapters(chapters, report)
    character_ids, character_names = _validate_characters(data.get("characters"), report)
    _validate_scenes(data.get("scenes"), chapter_ids, character_ids, character_names, report)
    return report


def validate_and_repair_yaml(yaml_text: str) -> tuple[str | None, ValidationReport]:
    try:
        data = load_yaml(yaml_text)
    except Exception as exc:
        report = ValidationReport(valid=False)
        report.add_error(f"YAML 解析失败，无法自动修复：{exc}")
        return None, report

    repaired = repair_script_data(data)
    report = validate_script_data(repaired)
    return dump_yaml(repaired), report


def repair_script_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        data = {}
    repaired = deepcopy(data)
    repaired.setdefault("schema_version", "1.0")
    repaired.setdefault("title", "未命名剧本")
    repaired.setdefault("logline", "待补充的一句话故事梗概")
    repaired.setdefault("theme", "待补充")
    repaired.setdefault("source", {"type": "novel", "chapters": []})
    repaired.setdefault("characters", [])
    repaired.setdefault("scenes", [])

    if not isinstance(repaired["source"], dict):
        repaired["source"] = {"type": "novel", "chapters": []}
    repaired["source"].setdefault("type", "novel")
    repaired["source"].setdefault("chapters", [])

    if not isinstance(repaired["characters"], list):
        repaired["characters"] = []
    for index, character in enumerate(repaired["characters"], start=1):
        if isinstance(character, dict):
            character.setdefault("id", f"char_{index:03d}")
            character.setdefault("name", f"角色{index}")
            character.setdefault("role", "角色")
            character.setdefault("description", "待补充")
            character.setdefault("goal", "待补充")

    if not isinstance(repaired["scenes"], list):
        repaired["scenes"] = []
    for index, scene in enumerate(repaired["scenes"], start=1):
        if isinstance(scene, dict):
            scene.setdefault("id", f"scene_{index:03d}")
            scene.setdefault("source_chapter", "")
            scene.setdefault("title", f"场景{index}")
            scene.setdefault("location", "待定地点")
            scene.setdefault("time", "待定时间")
            scene.setdefault("characters", [])
            scene.setdefault("summary", "待补充")
            scene.setdefault("action", [])
            scene.setdefault("dialogue", [])
            scene.setdefault("transition", "切至下一场")
    return repaired


def _validate_chapters(chapters: list[Any], report: ValidationReport) -> set[str]:
    chapter_ids: set[str] = set()
    for index, chapter in enumerate(chapters, start=1):
        path = f"source.chapters[{index}]"
        if not isinstance(chapter, dict):
            report.add_error(f"{path} 必须是对象。")
            continue
        chapter_id = chapter.get("id")
        if not chapter_id:
            report.add_error(f"{path}.id 为必填字段。")
        elif chapter_id in chapter_ids:
            report.add_error(f"章节 ID 重复：{chapter_id}")
        else:
            chapter_ids.add(str(chapter_id))
        if not chapter.get("title"):
            report.add_error(f"{path}.title 为必填字段。")
    return chapter_ids


def _validate_characters(characters: Any, report: ValidationReport) -> tuple[set[str], set[str]]:
    if not isinstance(characters, list) or not characters:
        report.add_error("characters 必须是非空列表。")
        return set(), set()

    ids: set[str] = set()
    names: set[str] = set()
    for index, character in enumerate(characters, start=1):
        path = f"characters[{index}]"
        if not isinstance(character, dict):
            report.add_error(f"{path} 必须是对象。")
            continue
        for key in ["id", "name", "role", "description", "goal"]:
            if not character.get(key):
                report.add_error(f"{path}.{key} 为必填字段。")
        char_id = character.get("id")
        if char_id:
            if char_id in ids:
                report.add_error(f"角色 ID 重复：{char_id}")
            ids.add(str(char_id))
        if character.get("name"):
            names.add(str(character["name"]))
    return ids, names


def _validate_scenes(
    scenes: Any,
    chapter_ids: set[str],
    character_ids: set[str],
    character_names: set[str],
    report: ValidationReport,
) -> None:
    if not isinstance(scenes, list) or not scenes:
        report.add_error("scenes 必须是非空列表。")
        return

    scene_ids: set[str] = set()
    for index, scene in enumerate(scenes, start=1):
        path = f"scenes[{index}]"
        if not isinstance(scene, dict):
            report.add_error(f"{path} 必须是对象。")
            continue
        for key in ["id", "source_chapter", "title", "location", "time", "characters", "summary", "action", "dialogue", "transition"]:
            if key not in scene:
                report.add_error(f"{path}.{key} 为必填字段。")

        scene_id = scene.get("id")
        if scene_id:
            if scene_id in scene_ids:
                report.add_error(f"场景 ID 重复：{scene_id}")
            scene_ids.add(str(scene_id))

        source_chapter = scene.get("source_chapter")
        if chapter_ids and source_chapter not in chapter_ids:
            report.add_error(f"{path}.source_chapter 引用不存在：{source_chapter}")

        scene_characters = scene.get("characters", [])
        if not isinstance(scene_characters, list) or not scene_characters:
            report.add_error(f"{path}.characters 必须是非空列表。")
        else:
            for char_id in scene_characters:
                if character_ids and char_id not in character_ids:
                    report.add_error(f"{path}.characters 引用了不存在的角色：{char_id}")

        if not isinstance(scene.get("action"), list) or not scene.get("action"):
            report.add_error(f"{path}.action 必须是非空列表。")

        dialogue = scene.get("dialogue")
        if not isinstance(dialogue, list):
            report.add_error(f"{path}.dialogue 必须是列表。")
            continue
        for dialogue_index, item in enumerate(dialogue, start=1):
            item_path = f"{path}.dialogue[{dialogue_index}]"
            if not isinstance(item, dict):
                report.add_error(f"{item_path} 必须是对象。")
                continue
            if not item.get("speaker"):
                report.add_error(f"{item_path}.speaker 为必填字段。")
            if not item.get("line"):
                report.add_error(f"{item_path}.line 为必填字段。")
            speaker = item.get("speaker")
            if speaker and character_ids and speaker not in character_ids:
                if speaker in character_names:
                    report.add_warning(f"{item_path}.speaker 建议使用角色 ID，而不是角色姓名：{speaker}")
                else:
                    report.add_error(f"{item_path}.speaker 引用了不存在的角色：{speaker}")

