"""Novel analysis and script generation orchestration."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import re
from typing import Any

from .chapter_parser import Chapter, chapters_to_public, parse_chapters, summarize_text
from .config import get_settings
from .llm_client import LLMClient
from .prompt_templates import build_generation_prompt, build_repair_prompt, build_revision_prompt
from .yaml_codec import dump_yaml, load_yaml
from .yaml_validator import repair_script_data, validate_script_data, validate_yaml_text


MIN_CHAPTERS = 3


def parse_chapter_payload(novel_text: str) -> dict[str, Any]:
    chapters = parse_chapters(novel_text)
    return {
        "chapter_count": len(chapters),
        "total_word_count": sum(chapter.word_count for chapter in chapters),
        "chapters": chapters_to_public(chapters),
        "meets_requirement": len(chapters) >= MIN_CHAPTERS,
    }


def generate_script_payload(
    novel_text: str,
    style: str = "影视剧本",
    language: str = "zh-CN",
    adaptation_mode: str = "忠于原文",
    detail_level: str = "标准",
    model_mode: str = "local",
) -> dict[str, Any]:
    chapters = parse_chapters(novel_text)
    if len(chapters) < MIN_CHAPTERS:
        return {
            "success": False,
            "error": f"当前仅检测到 {len(chapters)} 个章节，请至少输入 3 个章节。",
            "chapter_count": len(chapters),
            "chapters": chapters_to_public(chapters),
        }

    use_remote_llm = model_mode.lower() in {"llm", "large", "remote", "qiniu"}
    settings = get_settings(provider_override="qiniu" if use_remote_llm else "mock")
    client = LLMClient(settings)
    prompt = build_generation_prompt(novel_text, chapters, style, adaptation_mode, detail_level, language)
    remote_yaml = client.generate(prompt) if use_remote_llm else None

    if remote_yaml:
        data, yaml_text = _normalize_remote_yaml(remote_yaml)
        validation = validate_script_data(data)
        if not validation.valid and settings.uses_remote_llm:
            repair_prompt = build_repair_prompt(yaml_text, validation.errors)
            repaired_yaml = client.generate(repair_prompt)
            if repaired_yaml:
                data, yaml_text = _normalize_remote_yaml(repaired_yaml)
                validation = validate_script_data(data)
    else:
        data = generate_local_script(chapters, style, adaptation_mode, detail_level, language)
        validation = validate_script_data(data)
        yaml_text = dump_yaml(data)

    filename = build_download_filename(data.get("title", "script_output") if isinstance(data, dict) else "script_output")
    return {
        "success": validation.valid,
        "yaml": yaml_text,
        "script": data,
        "validation": validation.as_dict(),
        "chapter_count": len(chapters),
        "chapters": chapters_to_public(chapters),
        "filename": filename,
        "provider": settings.llm_provider,
        "model_mode": "llm" if use_remote_llm else "local",
        "model": settings.model if use_remote_llm else "local-demo",
        "reply": "已根据小说内容生成结构化 YAML 剧本。",
    }


def chat_turn_payload(
    message: str,
    existing_yaml: str = "",
    style: str = "影视剧本",
    language: str = "zh-CN",
    adaptation_mode: str = "忠于原文",
    detail_level: str = "标准",
    model_mode: str = "local",
) -> dict[str, Any]:
    if existing_yaml.strip():
        return revise_script_payload(
            existing_yaml=existing_yaml,
            user_instruction=message,
            style=style,
            language=language,
            adaptation_mode=adaptation_mode,
            detail_level=detail_level,
            model_mode=model_mode,
        )
    return generate_script_payload(
        novel_text=message,
        style=style,
        language=language,
        adaptation_mode=adaptation_mode,
        detail_level=detail_level,
        model_mode=model_mode,
    )


def revise_script_payload(
    existing_yaml: str,
    user_instruction: str,
    style: str = "影视剧本",
    language: str = "zh-CN",
    adaptation_mode: str = "忠于原文",
    detail_level: str = "标准",
    model_mode: str = "local",
) -> dict[str, Any]:
    if not user_instruction.strip():
        return {"success": False, "error": "请输入本轮修改要求。"}

    use_remote_llm = model_mode.lower() in {"llm", "large", "remote", "qiniu"}
    settings = get_settings(provider_override="qiniu" if use_remote_llm else "mock")
    client = LLMClient(settings)

    if use_remote_llm:
        prompt = build_revision_prompt(existing_yaml, user_instruction, style, adaptation_mode, detail_level, language)
        remote_yaml = client.generate(prompt)
        data, yaml_text = _normalize_remote_yaml(remote_yaml or existing_yaml)
        validation = validate_script_data(data)
        if not validation.valid:
            repair_prompt = build_repair_prompt(yaml_text, validation.errors)
            repaired_yaml = client.generate(repair_prompt)
            if repaired_yaml:
                data, yaml_text = _normalize_remote_yaml(repaired_yaml)
                validation = validate_script_data(data)
    else:
        try:
            data = load_yaml(existing_yaml)
        except Exception:
            data = {}
        data = _apply_local_revision(repair_script_data(data), user_instruction, style, adaptation_mode, detail_level)
        validation = validate_script_data(data)
        yaml_text = dump_yaml(data)

    title = data.get("title", "script_output") if isinstance(data, dict) else "script_output"
    return {
        "success": validation.valid,
        "yaml": yaml_text,
        "script": data,
        "validation": validation.as_dict(),
        "filename": build_download_filename(title),
        "provider": settings.llm_provider,
        "model_mode": "llm" if use_remote_llm else "local",
        "model": settings.model if use_remote_llm else "local-demo",
        "reply": "已根据你的新要求更新剧本 YAML。",
    }


def validate_yaml_payload(yaml_text: str, repair: bool = True) -> dict[str, Any]:
    validation = validate_yaml_text(yaml_text)
    result: dict[str, Any] = {"valid": validation.valid, "errors": validation.errors, "warnings": validation.warnings}
    if not validation.valid and repair:
        try:
            data = load_yaml(yaml_text)
            repaired = repair_script_data(data)
            repaired_report = validate_script_data(repaired)
            result["repaired_yaml"] = dump_yaml(repaired)
            result["repaired_validation"] = repaired_report.as_dict()
        except Exception as exc:
            result["repair_error"] = f"自动修复失败：{exc}"
    return result


def generate_local_script(
    chapters: list[Chapter],
    style: str,
    adaptation_mode: str,
    detail_level: str,
    language: str,
) -> dict[str, Any]:
    characters = _extract_characters(chapters)
    title = _infer_title(chapters)
    scenes = []
    for index, chapter in enumerate(chapters, start=1):
        scene_characters = _characters_in_text(chapter.content, characters) or [characters[0]["id"]]
        location = _infer_location(chapter.content)
        scene = {
            "id": f"scene_{index:03d}",
            "source_chapter": chapter.chapter_id,
            "title": _scene_title(chapter.title, index),
            "location": location,
            "time": _infer_time(chapter.content),
            "characters": scene_characters,
            "summary": chapter.summary,
            "action": _build_actions(chapter, location, scene_characters, characters, detail_level),
            "dialogue": _build_dialogues(chapter, scene_characters, characters),
            "transition": "淡出，进入片尾。" if index == len(chapters) else "切至下一章节场景。",
        }
        scenes.append(scene)

    return {
        "schema_version": "1.0",
        "title": title,
        "source": {
            "type": "novel",
            "chapters": [
                {"id": chapter.chapter_id, "title": chapter.title, "word_count": chapter.word_count}
                for chapter in chapters
            ],
        },
        "logline": _build_logline(chapters),
        "theme": _infer_theme(chapters, adaptation_mode),
        "metadata": {
            "style": style,
            "language": language,
            "adaptation_mode": adaptation_mode,
            "detail_level": detail_level,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generator": "local-demo",
        },
        "characters": characters,
        "scenes": scenes,
    }


def build_download_filename(title: str) -> str:
    safe_title = re.sub(r"[\\/:*?\"<>|\s]+", "_", str(title)).strip("_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not safe_title:
        return "script_output.yaml"
    return f"script_{safe_title}_{timestamp}.yaml"


def _normalize_remote_yaml(raw_text: str) -> tuple[dict[str, Any], str]:
    data = load_yaml(raw_text)
    if not isinstance(data, dict):
        data = repair_script_data(data)
    yaml_text = dump_yaml(data)
    return data, yaml_text


def _apply_local_revision(
    data: dict[str, Any],
    instruction: str,
    style: str,
    adaptation_mode: str,
    detail_level: str,
) -> dict[str, Any]:
    metadata = data.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        data["metadata"] = metadata

    metadata["style"] = style
    metadata["adaptation_mode"] = adaptation_mode
    metadata["detail_level"] = detail_level
    metadata.setdefault("revision_history", [])
    if not isinstance(metadata["revision_history"], list):
        metadata["revision_history"] = []
    metadata["revision_history"].append(
        {
            "instruction": instruction.strip(),
            "applied_by": "local-demo",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

    title_match = re.search(r"(?:标题|剧名|片名)(?:改成|修改为|设为|叫)\s*[《\"]?([^》\"\n，。,.]{2,30})", instruction)
    if title_match:
        data["title"] = title_match.group(1).strip()

    if "口语" in instruction:
        for scene in data.get("scenes", []):
            if not isinstance(scene, dict):
                continue
            for dialogue in scene.get("dialogue", []):
                if isinstance(dialogue, dict) and dialogue.get("line") and "。" not in dialogue["line"][-1:]:
                    dialogue["line"] = str(dialogue["line"]).rstrip("。") + "。"
                if isinstance(dialogue, dict):
                    dialogue["emotion"] = dialogue.get("emotion") or "自然"

    if any(word in instruction for word in ["冲突", "悬念", "紧张"]):
        data["theme"] = str(data.get("theme", "人物选择与转变")) + "；本轮强化戏剧冲突。"
        scenes = data.get("scenes", [])
        if isinstance(scenes, list) and scenes:
            first_scene = scenes[0]
            if isinstance(first_scene, dict):
                actions = first_scene.setdefault("action", [])
                if isinstance(actions, list):
                    actions.append("人物在新的压力下重新做出选择，场面张力进一步升级。")

    return data


def _infer_title(chapters: list[Chapter]) -> str:
    joined = "\n".join(chapter.title + "\n" + chapter.content[:80] for chapter in chapters[:2])
    bracket = re.search(r"《([^》]{2,30})》", joined)
    if bracket:
        return bracket.group(1)
    title = _remove_chapter_prefix(chapters[0].title)
    return f"{title} 改编剧本" if title else "小说改编剧本"


def _build_logline(chapters: list[Chapter]) -> str:
    first = chapters[0].summary.rstrip("。")
    last = chapters[-1].summary.rstrip("。")
    if first and last and first != last:
        return f"{first}，并在后续章节中推进至：{last}。"
    return first + "。" if first else "一段多章节小说被改编为可继续打磨的剧本初稿。"


def _infer_theme(chapters: list[Chapter], adaptation_mode: str) -> str:
    text = "\n".join(chapter.content for chapter in chapters)
    if any(word in text for word in ["真相", "旧案", "线索", "调查"]):
        base = "追寻真相与自我和解"
    elif any(word in text for word in ["梦想", "舞台", "比赛", "远方"]):
        base = "成长、选择与坚持"
    elif any(word in text for word in ["家", "亲人", "故乡", "母亲", "父亲"]):
        base = "亲情牵绊与归属"
    else:
        base = "人物在关键事件中的选择与改变"
    return f"{base}；改编策略：{adaptation_mode}"


def _extract_characters(chapters: list[Chapter]) -> list[dict[str, str]]:
    text = "\n".join(chapter.content for chapter in chapters)
    names: list[str] = []
    for match in re.finditer(r"^\s*([\u4e00-\u9fffA-Za-z]{2,8})\s*[：:]", text, flags=re.MULTILINE):
        _append_unique(names, match.group(1))
    for match in re.finditer(r"([\u4e00-\u9fff]{2,4})(?:低声|轻声|忽然|沉声|笑着|问|说|回答|喊道|说道)", text):
        _append_unique(names, match.group(1))
    names = [name for name in names if name not in {"第一章", "第二章", "第三章", "第四章"}][:6]
    if not names:
        names = ["主角", "关键人物"]
    elif len(names) == 1:
        names.append("关键人物")

    characters: list[dict[str, str]] = []
    for index, name in enumerate(names, start=1):
        characters.append(
            {
                "id": f"char_{index:03d}",
                "name": name,
                "role": "主角" if index == 1 else "重要角色",
                "description": _character_description(name, index, text),
                "goal": _character_goal(index, text),
            }
        )
    return characters


def _characters_in_text(text: str, characters: list[dict[str, str]]) -> list[str]:
    found = [character["id"] for character in characters if character["name"] in text]
    return found[:4]


def _infer_location(text: str) -> str:
    candidates = ["咖啡馆", "旧仓库", "天台", "街道", "办公室", "车站", "学校", "医院", "家中", "河边", "庭院", "山路"]
    for candidate in candidates:
        if candidate in text:
            return candidate
    return "主要事件发生地"


def _infer_time(text: str) -> str:
    if any(word in text for word in ["凌晨", "黎明"]):
        return "黎明"
    if any(word in text for word in ["夜", "雨夜", "深夜"]):
        return "夜晚"
    if any(word in text for word in ["清晨", "早晨"]):
        return "清晨"
    if "黄昏" in text or "傍晚" in text:
        return "傍晚"
    return "白天"


def _scene_title(chapter_title: str, index: int) -> str:
    title = _remove_chapter_prefix(chapter_title)
    return title or f"场景 {index}"


def _remove_chapter_prefix(title: str) -> str:
    cleaned = re.sub(r"^\s*第[零〇一二三四五六七八九十百千万两\d]+[章节回卷部篇]\s*[:：、.\-]?\s*", "", title)
    cleaned = re.sub(r"^\s*chapter\s+\d+\s*[:：、.\-]?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*[一二三四五六七八九十\d]+[、.．]\s*", "", cleaned)
    return cleaned.strip()


def _build_actions(
    chapter: Chapter,
    location: str,
    scene_characters: list[str],
    characters: list[dict[str, str]],
    detail_level: str,
) -> list[str]:
    sentences = _plain_sentences(chapter.content)
    selected = sentences[:3 if detail_level == "详细" else 2]
    if selected:
        return selected
    main_name = _name_for_id(scene_characters[0], characters)
    return [
        f"{main_name}来到{location}，观察周围环境并意识到事件正在升级。",
        "镜头跟随人物动作推进，保留原章节的关键情绪与信息。",
    ]


def _build_dialogues(chapter: Chapter, scene_characters: list[str], characters: list[dict[str, str]]) -> list[dict[str, str]]:
    by_name = {character["name"]: character["id"] for character in characters}
    dialogues: list[dict[str, str]] = []
    for match in re.finditer(r"^\s*([\u4e00-\u9fffA-Za-z]{2,8})\s*[：:]\s*(.+)$", chapter.content, flags=re.MULTILINE):
        speaker_name = match.group(1).strip()
        line = match.group(2).strip()
        if speaker_name in by_name and line:
            dialogues.append({"speaker": by_name[speaker_name], "line": line, "emotion": _infer_emotion(line)})
    if dialogues:
        return dialogues[:6]

    quote_matches = re.findall(r"[“\"]([^”\"]{2,80})[”\"]", chapter.content)
    if quote_matches:
        return [{"speaker": scene_characters[0], "line": quote_matches[0], "emotion": _infer_emotion(quote_matches[0])}]

    main_name = _name_for_id(scene_characters[0], characters)
    return [
        {"speaker": scene_characters[0], "line": f"这件事不能停在这里，{main_name}必须继续往前走。", "emotion": "克制"},
    ]


def _plain_sentences(text: str) -> list[str]:
    clean = re.sub(r"^\s*[\u4e00-\u9fffA-Za-z]{2,8}\s*[：:].*$", "", text, flags=re.MULTILINE)
    sentences = [item.strip() for item in re.findall(r"[^。！？!?]{8,90}[。！？!?]", clean)]
    return [sentence for sentence in sentences if "：" not in sentence and ":" not in sentence][:4]


def _infer_emotion(line: str) -> str:
    if any(mark in line for mark in ["？", "?"]):
        return "疑问"
    if any(mark in line for mark in ["！", "!"]):
        return "激动"
    if any(word in line for word in ["别怕", "回来", "真相", "等你"]):
        return "克制"
    return "平静"


def _character_description(name: str, index: int, text: str) -> str:
    if index == 1:
        return f"{name}是推动故事前进的核心人物，面对事件时保持主动与观察。"
    if any(word in text for word in ["旧案", "线索", "真相"]):
        return f"{name}掌握关键线索，与主角共同接近事件真相。"
    return f"{name}与主角形成关系张力，推动情节转折。"


def _character_goal(index: int, text: str) -> str:
    if index == 1 and any(word in text for word in ["真相", "旧案", "线索"]):
        return "查清事件真相并完成自我选择"
    if index == 1:
        return "解决章节中的核心冲突"
    return "影响主角判断并推动关键事件发生"


def _name_for_id(character_id: str, characters: list[dict[str, str]]) -> str:
    for character in characters:
        if character["id"] == character_id:
            return character["name"]
    return "角色"


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)
