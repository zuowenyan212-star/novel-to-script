import re
from typing import Dict, List, Tuple

from .chapter_parser import Chapter, parse_chapters, summarize_content
from .graph_builder import build_character_graph_from_data
from .llm_client import LLMClient, LLMError
from .prompt_templates import build_generation_prompt, build_repair_prompt
from .yaml_validator import validate_yaml_text, dump_yaml


def _extract_dialogues(text: str) -> List[Tuple[str, str, str]]:
    """
    Extract simple Chinese dialogues.
    Returns list of (speaker_guess, line, emotion).
    """
    dialogues: List[Tuple[str, str, str]] = []

    pattern1 = re.compile(r"([\u4e00-\u9fff]{2,4})(?:低声|急忙|冷冷|轻声|大声)?(?:说|说道|问|喊|答|反驳|提醒|叹道)[：:，“”\\s]*[“\"]([^”\"]{1,120})[”\"]")
    for m in pattern1.finditer(text):
        speaker = m.group(1)
        line = m.group(2).strip()
        emotion = "平静"
        if "低声" in m.group(0):
            emotion = "低声"
        elif "急忙" in m.group(0):
            emotion = "急切"
        elif "冷冷" in m.group(0):
            emotion = "冷静"
        elif "大声" in m.group(0) or "喊" in m.group(0):
            emotion = "激动"
        dialogues.append((speaker, line, emotion))

    if not dialogues:
        for i, m in enumerate(re.finditer(r"[“\"]([^”\"]{1,120})[”\"]", text), start=1):
            dialogues.append((f"角色{i}", m.group(1).strip(), "自然"))

    return dialogues[:8]


def _guess_names(text: str) -> List[str]:
    names = []
    patterns = [
        r"([\u4e00-\u9fff]{2,4})(?:低声|急忙|冷冷|轻声|大声)?(?:说|说道|问|喊|答|反驳|提醒|叹道)",
        r"([\u4e00-\u9fff]{2,4})(?:第一次|走进|看着|发现|让|站在|跪在|脸色|沉默|皱眉|转身)",
    ]
    blacklist = {"一个", "旁边", "今日", "第一", "第二", "第三", "小说", "作者", "系统", "他们", "我们", "你们", "时候"}
    for pattern in patterns:
        for name in re.findall(pattern, text):
            if name not in blacklist and name not in names:
                names.append(name)
    if not names:
        names = ["主角"]
    return names[:10]


def _make_characters(chapters: List[Chapter]) -> Tuple[List[Dict], Dict[str, str]]:
    all_text = "\n".join(ch.content for ch in chapters)
    names = _guess_names(all_text)

    for speaker, _, _ in _extract_dialogues(all_text):
        if speaker not in names and not speaker.startswith("角色"):
            names.append(speaker)

    names = names[:12]
    characters = []
    name_to_id = {}
    for idx, name in enumerate(names, start=1):
        char_id = f"char_{idx:03d}"
        name_to_id[name] = char_id
        role = "主角" if idx == 1 else "配角"
        characters.append(
            {
                "id": char_id,
                "name": name,
                "role": role,
                "description": f"{name}是根据小说文本自动识别出的{role}。",
                "goal": "推动剧情发展并完成本阶段故事冲突。",
            }
        )
    return characters, name_to_id


def _build_rule_based_yaml(novel_text: str) -> str:
    chapters = parse_chapters(novel_text)
    characters, name_to_id = _make_characters(chapters)
    fallback_char_id = characters[0]["id"] if characters else "char_001"

    source_chapters = [
        {"id": chapter.chapter_id, "title": chapter.title}
        for chapter in chapters
    ]

    scenes = []
    for idx, chapter in enumerate(chapters, start=1):
        dialogues_raw = _extract_dialogues(chapter.content)

        scene_char_ids = set()
        dialogue_items = []
        for speaker, line, emotion in dialogues_raw:
            speaker_id = name_to_id.get(speaker, fallback_char_id)
            scene_char_ids.add(speaker_id)
            dialogue_items.append(
                {
                    "speaker": speaker_id,
                    "line": line,
                    "emotion": emotion,
                }
            )

        if not dialogue_items:
            scene_char_ids.add(fallback_char_id)

        for name, char_id in name_to_id.items():
            if name in chapter.content:
                scene_char_ids.add(char_id)

        if not scene_char_ids:
            scene_char_ids.add(fallback_char_id)

        sentence_candidates = re.split(r"[。！？!?]\s*", chapter.content)
        actions = []
        for sentence in sentence_candidates:
            sentence = re.sub(r"\s+", "", sentence)
            if not sentence:
                continue
            sentence = re.sub(r"[“\"].*?[”\"]", "", sentence).strip("，,：:")
            if len(sentence) >= 6:
                actions.append(sentence[:120])
            if len(actions) >= 4:
                break

        if not actions:
            actions = [summarize_content(chapter.content, 100)]

        scenes.append(
            {
                "id": f"scene_{idx:03d}",
                "source_chapter": chapter.chapter_id,
                "title": chapter.title,
                "location": "根据原文场景整理",
                "time": "未明确",
                "characters": sorted(scene_char_ids),
                "summary": chapter.summary,
                "action": actions,
                "dialogue": dialogue_items,
                "transition": "切至下一场",
            }
        )

    title = "AI 改编剧本"
    if chapters:
        first_title = re.sub(r"^第\s*[0-9一二三四五六七八九十百千万两〇零]+\s*章\s*", "", chapters[0].title)
        title = first_title.strip() or title

    data = {
        "schema_version": "1.0",
        "title": title,
        "source": {
            "type": "novel",
            "chapters": source_chapters,
        },
        "logline": "一段由多章节小说自动改编而来的结构化剧本初稿。",
        "theme": "人物在冲突中推进故事，并逐步揭示真相。",
        "characters": characters,
        "scenes": scenes,
    }
    return dump_yaml(data)


def _package_result(
    yaml_text: str,
    chapter_count: int,
    message: str,
    mock_mode: bool,
    provider: str,
    model: str = "",
) -> Dict:
    validation = validate_yaml_text(yaml_text)
    graph = build_character_graph_from_data(validation.get("data"))
    return {
        "success": validation["valid"],
        "yaml": yaml_text,
        "data": validation.get("data"),
        "validation": {
            "valid": validation["valid"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        },
        "chapter_count": chapter_count,
        "message": message,
        "mock_mode": mock_mode,
        "provider": provider,
        "model": model,
        "graph": graph,
    }


def generate_script_yaml(
    novel_text: str,
    style: str = "影视剧本",
    language: str = "zh-CN",
    provider: str = "local",
    model: str | None = None,
) -> Dict:
    chapters = parse_chapters(novel_text)
    provider = (provider or "local").lower()

    if len(chapters) < 3:
        return {
            "success": False,
            "yaml": "",
            "data": None,
            "validation": {
                "valid": False,
                "errors": [f"当前仅检测到 {len(chapters)} 个章节，请至少输入 3 个章节。"],
                "warnings": [],
            },
            "chapter_count": len(chapters),
            "message": "章节数量不足，未调用大模型。",
            "mock_mode": provider == "local",
            "provider": provider,
            "model": model or "",
            "graph": {"nodes": [], "edges": []},
        }

    chapter_payload = {
        "chapter_count": len(chapters),
        "total_word_count": sum(c.word_count for c in chapters),
        "chapters": [
            {
                "chapter_id": c.chapter_id,
                "title": c.title,
                "word_count": c.word_count,
                "summary": c.summary,
            }
            for c in chapters
        ],
    }

    # Page-level local provider is now the stable no-key demo path.
    if provider == "local":
        yaml_text = _build_rule_based_yaml(novel_text)
        return _package_result(
            yaml_text=yaml_text,
            chapter_count=len(chapters),
            message="本地演示模型已生成可演示 YAML，无需 API Key。",
            mock_mode=True,
            provider="local",
            model=model or "local-rule",
        )

    client = LLMClient()

    # Backward compatibility: if old env still sets USE_MOCK_LLM=true, use local generator.
    if client.is_mock() and provider != "qiniu":
        yaml_text = _build_rule_based_yaml(novel_text)
        return _package_result(
            yaml_text=yaml_text,
            chapter_count=len(chapters),
            message="Mock 模式已生成可演示 YAML。",
            mock_mode=True,
            provider="local",
            model="local-rule",
        )

    try:
        prompt = build_generation_prompt(novel_text, chapter_payload, style, language)
        yaml_text = client.generate_text(prompt, provider=provider, model=model)
        validation = validate_yaml_text(yaml_text)

        if not validation["valid"]:
            repair_prompt = build_repair_prompt(yaml_text, validation["errors"])
            repaired_yaml = client.generate_text(repair_prompt, provider=provider, model=model)
            repaired_validation = validate_yaml_text(repaired_yaml)
            if repaired_validation["valid"]:
                yaml_text = repaired_yaml

        return _package_result(
            yaml_text=yaml_text,
            chapter_count=len(chapters),
            message="剧本生成完成。",
            mock_mode=False,
            provider=provider,
            model=model or "",
        )
    except LLMError as exc:
        return {
            "success": False,
            "yaml": "",
            "data": None,
            "validation": {
                "valid": False,
                "errors": [str(exc)],
                "warnings": [],
            },
            "chapter_count": len(chapters),
            "message": str(exc),
            "mock_mode": False,
            "provider": provider,
            "model": model or "",
            "graph": {"nodes": [], "edges": []},
        }
