from typing import Any, Dict, List, Optional, Tuple

from .yaml_codec import dump_yaml, load_yaml as parse_yaml


REQUIRED_TOP_LEVEL = ["schema_version", "title", "source", "characters", "scenes"]
REQUIRED_CHARACTER_FIELDS = ["id", "name", "role", "description"]
REQUIRED_SCENE_FIELDS = ["id", "source_chapter", "title", "location", "time", "characters", "summary", "action", "dialogue"]


def load_yaml(yaml_text: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    try:
        data = parse_yaml(yaml_text)
    except Exception as exc:
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

    if data.get("schema_version") != "1.1":
        warnings.append("建议 v0.3 输出使用 schema_version: 1.1，以支持 chapter_scripts 和 dialogue_index。")

    source = data.get("source", {})
    if not isinstance(source, dict):
        errors.append("source 必须是对象。")
        chapters = []
    else:
        chapters = source.get("chapters", [])
        if not isinstance(chapters, list) or not chapters:
            errors.append("source.chapters 必须是非空列表。")
        else:
            for chapter in chapters:
                if not isinstance(chapter, dict) or "id" not in chapter or "title" not in chapter:
                    errors.append("source.chapters 中每个章节都必须包含 id 和 title。")

    chapter_ids = {
        chapter.get("id")
        for chapter in chapters
        if isinstance(chapter, dict) and chapter.get("id")
    }

    characters = data.get("characters", [])
    character_ids = set()
    character_id_to_name = {}

    if not isinstance(characters, list) or not characters:
        errors.append("characters 必须是非空列表。")
    else:
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
                character_id_to_name[char_id] = character.get("name", "")

    scenes = data.get("scenes", [])
    scene_ids = set()
    dialogue_ids = set()

    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes 必须是非空列表。")
    else:
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
                    if item.get("id"):
                        if item["id"] in dialogue_ids:
                            errors.append(f"对白 id 重复：{item['id']}")
                        dialogue_ids.add(item["id"])

    chapter_scripts = data.get("chapter_scripts")
    if chapter_scripts is None:
        warnings.append("建议补充 chapter_scripts 字段，方便按章节查看 YAML 剧本。")
    elif not isinstance(chapter_scripts, list):
        errors.append("chapter_scripts 必须是列表。")
    else:
        for idx, chapter_script in enumerate(chapter_scripts, start=1):
            if not isinstance(chapter_script, dict):
                errors.append(f"chapter_scripts 第 {idx} 项必须是对象。")
                continue
            chapter_id = chapter_script.get("chapter_id")
            if chapter_ids and chapter_id not in chapter_ids:
                errors.append(f"chapter_scripts 第 {idx} 项引用的章节不存在：{chapter_id}")
            scene_id_list = chapter_script.get("scene_ids", [])
            if not isinstance(scene_id_list, list):
                errors.append(f"chapter_scripts 第 {idx} 项的 scene_ids 必须是列表。")
            else:
                for scene_id in scene_id_list:
                    if scene_ids and scene_id not in scene_ids:
                        errors.append(f"chapter_scripts 第 {idx} 项引用的场景不存在：{scene_id}")

    dialogue_index = data.get("dialogue_index")
    if dialogue_index is None:
        warnings.append("建议补充 dialogue_index 字段，方便单独查看所有台词。")
    elif not isinstance(dialogue_index, list):
        errors.append("dialogue_index 必须是列表。")
    else:
        for idx, item in enumerate(dialogue_index, start=1):
            if not isinstance(item, dict):
                errors.append(f"dialogue_index 第 {idx} 项必须是对象。")
                continue
            for field in ["id", "chapter_id", "scene_id", "speaker", "speaker_name", "line"]:
                if field not in item:
                    errors.append(f"dialogue_index 第 {idx} 项缺少字段：{field}")
            if item.get("chapter_id") and chapter_ids and item.get("chapter_id") not in chapter_ids:
                errors.append(f"dialogue_index 第 {idx} 项引用的章节不存在：{item.get('chapter_id')}")
            if item.get("scene_id") and scene_ids and item.get("scene_id") not in scene_ids:
                errors.append(f"dialogue_index 第 {idx} 项引用的场景不存在：{item.get('scene_id')}")
            if item.get("speaker") and character_ids and item.get("speaker") not in character_ids:
                errors.append(f"dialogue_index 第 {idx} 项 speaker 不存在：{item.get('speaker')}")

    if not errors and isinstance(scenes, list) and len(scenes) < 3:
        warnings.append("当前场景数量少于 3，建议检查是否充分拆分。")

    return len(errors) == 0, errors, warnings


def validate_yaml_text(yaml_text: str) -> Dict[str, Any]:
    data, load_errors = load_yaml(yaml_text)
    if load_errors:
        return {"valid": False, "errors": load_errors, "warnings": [], "data": None}

    valid, errors, warnings = validate_script_data(data)
    return {"valid": valid, "errors": errors, "warnings": warnings, "data": data}
