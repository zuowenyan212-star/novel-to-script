from typing import Any, Dict, List, Tuple
import yaml


REQUIRED_TOP_LEVEL = ["schema_version", "title", "source", "characters", "scenes"]
REQUIRED_CHARACTER_FIELDS = ["id", "name", "role", "description"]
REQUIRED_SCENE_FIELDS = ["id", "source_chapter", "title", "location", "time", "characters", "summary", "action", "dialogue"]


def load_yaml(yaml_text: str) -> Tuple[Dict[str, Any] | None, List[str]]:
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        return None, [f"YAML 无法解析：{exc}"]

    if not isinstance(data, dict):
        return None, ["YAML 顶层结构必须是对象。"]
    return data, []


def validate_script_data(data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"缺少顶层必填字段：{field}")

    if errors:
        return False, errors, warnings

    source = data.get("source", {})
    if not isinstance(source, dict):
        errors.append("source 必须是对象。")
    else:
        chapters = source.get("chapters", [])
        if not isinstance(chapters, list) or not chapters:
            errors.append("source.chapters 必须是非空列表。")
        else:
            for chapter in chapters:
                if not isinstance(chapter, dict) or "id" not in chapter or "title" not in chapter:
                    errors.append("source.chapters 中每个章节都必须包含 id 和 title。")

    characters = data.get("characters", [])
    if not isinstance(characters, list) or not characters:
        errors.append("characters 必须是非空列表。")
        character_ids = set()
    else:
        character_ids = set()
        for idx, character in enumerate(characters, start=1):
            if not isinstance(character, dict):
                errors.append(f"characters 第 {idx} 项必须是对象。")
                continue
            for field in REQUIRED_CHARACTER_FIELDS:
                if field not in character:
                    errors.append(f"角色第 {idx} 项缺少字段：{field}")
            char_id = character.get("id")
            if char_id in character_ids:
                errors.append(f"角色 id 重复：{char_id}")
            if char_id:
                character_ids.add(char_id)

    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes 必须是非空列表。")
    else:
        scene_ids = set()
        chapter_ids = {
            chapter.get("id")
            for chapter in source.get("chapters", [])
            if isinstance(chapter, dict)
        } if isinstance(source, dict) else set()

        for idx, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                errors.append(f"scenes 第 {idx} 项必须是对象。")
                continue

            for field in REQUIRED_SCENE_FIELDS:
                if field not in scene:
                    errors.append(f"场景第 {idx} 项缺少字段：{field}")

            scene_id = scene.get("id")
            if scene_id in scene_ids:
                errors.append(f"场景 id 重复：{scene_id}")
            if scene_id:
                scene_ids.add(scene_id)

            source_chapter = scene.get("source_chapter")
            if chapter_ids and source_chapter not in chapter_ids:
                errors.append(f"场景 {scene_id} 引用的章节不存在：{source_chapter}")

            scene_characters = scene.get("characters", [])
            if not isinstance(scene_characters, list):
                errors.append(f"场景 {scene_id} 的 characters 必须是列表。")
            else:
                for char_id in scene_characters:
                    if char_id not in character_ids:
                        errors.append(f"场景 {scene_id} 引用了不存在的角色 id：{char_id}")

            action = scene.get("action", [])
            if action is not None and not isinstance(action, list):
                errors.append(f"场景 {scene_id} 的 action 必须是列表。")

            dialogue = scene.get("dialogue", [])
            if dialogue is not None and not isinstance(dialogue, list):
                errors.append(f"场景 {scene_id} 的 dialogue 必须是列表。")
            else:
                for d_idx, item in enumerate(dialogue or [], start=1):
                    if not isinstance(item, dict):
                        errors.append(f"场景 {scene_id} 的第 {d_idx} 条对白必须是对象。")
                        continue
                    if "speaker" not in item or "line" not in item:
                        errors.append(f"场景 {scene_id} 的第 {d_idx} 条对白必须包含 speaker 和 line。")
                    if item.get("speaker") not in character_ids:
                        errors.append(f"场景 {scene_id} 的对白 speaker 不存在：{item.get('speaker')}")
                    if not item.get("line"):
                        errors.append(f"场景 {scene_id} 的第 {d_idx} 条对白 line 不能为空。")

    if not errors and len(scenes) < 3:
        warnings.append("当前场景数量少于 3，建议检查是否充分拆分。")

    return len(errors) == 0, errors, warnings


def validate_yaml_text(yaml_text: str) -> Dict[str, Any]:
    data, load_errors = load_yaml(yaml_text)
    if load_errors:
        return {"valid": False, "errors": load_errors, "warnings": [], "data": None}

    valid, errors, warnings = validate_script_data(data)
    return {"valid": valid, "errors": errors, "warnings": warnings, "data": data}


def dump_yaml(data: Dict[str, Any]) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, indent=2)
