import re
from typing import Dict, List, Optional, Tuple

from .chapter_parser import Chapter, parse_chapters, summarize_content
from .graph_builder import build_character_graph_from_data
from .llm_client import LLMClient, LLMError
from .prompt_templates import build_generation_prompt, build_repair_prompt
from .yaml_validator import validate_yaml_text, dump_yaml


ADAPTATION_STYLE_LABELS = {
    "faithful": "忠于原文",
    "dramatic": "增强戏剧冲突化",
    "colloquial": "口语化",
}

# v0.3.1: local demo mode uses conservative name extraction to avoid
# false characters like "王林苦笑", "台上朗声", "一眼沉声".
NAME_BLACKLIST = {
    "一个", "旁边", "今日", "第一", "第二", "第三", "第四", "小说", "作者", "系统",
    "他们", "我们", "你们", "她们", "时候", "众人", "有人", "没人", "男人", "女人",
    "少年", "少女", "老人", "商人", "衙役", "大人", "台上", "台下", "一眼", "这个",
    "那个", "这里", "那里", "几句", "这件", "此事", "真相", "众臣", "所有", "其他",
}

NAME_SUFFIXES = [
    "苦笑", "冷笑", "微笑", "轻笑", "大笑", "朗声", "沉声", "低声", "轻声", "大声",
    "急忙", "冷冷", "缓缓", "忽然", "终于", "无奈", "叹气", "叹息", "一愣", "皱眉",
    "摇头", "点头", "抬头", "低头", "开口", "笑着", "看着", "说道", "说完", "问道",
]

ACTION_OR_SPEECH_HINTS = (
    "低声|急忙|冷冷|轻声|大声|苦笑|冷笑|微笑|朗声|沉声|笑着|皱眉|摇头|点头|"
    "叹气|叹息|一愣|开口|深吸|看着|发现|让|站在|跪在|脸色|沉默|转身|走进|"
    "抬头|低头|缓缓|终于|忽然|说道|说|问道|问|喊道|喊|答道|回答|反驳|提醒|叹道"
)

SPEECH_VERBS = "说|说道|问|问道|喊|喊道|答|答道|回答|反驳|提醒|叹道|道"


def _clean_name(raw: str) -> str:
    """Clean a guessed Chinese speaker name.

    The rule-based local generator is not meant to replace NER. It only needs
    stable demo output, so we prefer precision over recall.
    """
    if not raw:
        return ""

    name = re.sub(r"[^\u4e00-\u9fff]", "", raw).strip()
    if not name:
        return ""

    # Remove common action/emotion words accidentally attached to a name.
    changed = True
    while changed:
        changed = False
        for suffix in sorted(NAME_SUFFIXES, key=len, reverse=True):
            if name.endswith(suffix) and len(name) - len(suffix) >= 2:
                name = name[: -len(suffix)]
                changed = True
                break

    if name in NAME_BLACKLIST:
        return ""

    if any(bad in name for bad in ["这个", "那个", "这里", "那里", "怎么", "什么"]):
        return ""

    # Reject obvious narration fragments.
    if name.endswith(("的", "了", "着", "过")):
        return ""

    # Most Chinese fiction names are 2-3 characters. We allow 4 only for
    # compound surnames or fictional full names, but reject common phrase-like
    # starts to reduce false positives.
    if len(name) < 2 or len(name) > 4:
        return ""

    if len(name) == 4 and not name.startswith(("欧阳", "司马", "上官", "诸葛", "东方", "南宫", "令狐", "宇文")):
        # Four-character names are possible, but local demo should avoid
        # creating false names from action phrases.
        return ""

    return name


def _extract_speaker_from_prefix(prefix: str) -> str:
    """Infer speaker from the text before a quote or speech verb."""
    if not prefix:
        return ""

    # Keep only the current sentence tail.
    segment = re.split(r"[。！？!?\n]", prefix)[-1]
    segment = segment[-30:]

    # Prefer candidates directly followed by action/speech hints.
    candidates = re.findall(rf"([\u4e00-\u9fff]{{2,4}})(?=(?:{ACTION_OR_SPEECH_HINTS}))", segment)
    for candidate in reversed(candidates):
        cleaned = _clean_name(candidate)
        if cleaned:
            return cleaned

    # Then try the beginning of the segment, e.g. 林安深吸一口气，说道
    m = re.match(r"\s*([\u4e00-\u9fff]{2,4})", segment)
    if m:
        cleaned = _clean_name(m.group(1))
        if cleaned:
            return cleaned

    # Last fallback: take the last short Chinese chunk before the quote.
    chunks = re.findall(r"[\u4e00-\u9fff]{2,4}", segment)
    for chunk in reversed(chunks):
        cleaned = _clean_name(chunk)
        if cleaned:
            return cleaned

    return ""


def _guess_emotion(context: str) -> str:
    if "低声" in context:
        return "低声"
    if "急忙" in context:
        return "急切"
    if "冷冷" in context or "沉声" in context:
        return "冷静"
    if "大声" in context or "喊" in context:
        return "激动"
    if "苦笑" in context or "无奈" in context:
        return "无奈"
    if "朗声" in context:
        return "郑重"
    return "平静"


def _extract_dialogues(text: str) -> List[Tuple[str, str, str]]:
    """Extract simple Chinese dialogues as (speaker, line, emotion).

    v0.3.1 fixes the previous greedy speaker regex by inferring the speaker
    from the prefix before the quote and cleaning action/emotion suffixes.
    """
    dialogues: List[Tuple[str, str, str]] = []

    # Pattern A: speaker context + speech verb + quote
    pattern = re.compile(
        rf"([^。！？!?\n]{{0,40}}?)(?:{SPEECH_VERBS})[：:，,\s]*[“\"]([^”\"]{{1,160}})[”\"]"
    )
    for m in pattern.finditer(text):
        context = m.group(1) or ""
        line = m.group(2).strip()
        speaker = _extract_speaker_from_prefix(context)
        if not speaker:
            continue
        dialogues.append((speaker, line, _guess_emotion(context + m.group(0))))

    # Pattern B: quote + speaker said, e.g. “别动。”王林低声说。
    pattern_after = re.compile(
        rf"[“\"]([^”\"]{{1,160}})[”\"][，,\s]*([^。！？!?\n]{{0,24}}?)(?:{SPEECH_VERBS})"
    )
    for m in pattern_after.finditer(text):
        line = m.group(1).strip()
        context = m.group(2) or ""
        speaker = _extract_speaker_from_prefix(context)
        if not speaker:
            continue
        item = (speaker, line, _guess_emotion(context + m.group(0)))
        if item not in dialogues:
            dialogues.append(item)

    # Fallback: quoted lines with generic speakers only if no valid speaker is found.
    if not dialogues:
        for i, m in enumerate(re.finditer(r"[“\"]([^”\"]{1,120})[”\"]", text), start=1):
            dialogues.append((f"角色{i}", m.group(1).strip(), "自然"))

    # Deduplicate while preserving order.
    result: List[Tuple[str, str, str]] = []
    seen = set()
    for speaker, line, emotion in dialogues:
        key = (speaker, line)
        if key in seen:
            continue
        seen.add(key)
        result.append((speaker, line, emotion))

    return result[:12]


def _guess_names(text: str) -> List[str]:
    """Conservatively guess character names for local demo generation."""
    names: List[str] = []

    # Dialogue speakers are the most reliable source.
    for speaker, _, _ in _extract_dialogues(text):
        cleaned = _clean_name(speaker)
        if cleaned and cleaned not in names and not cleaned.startswith("角色"):
            names.append(cleaned)

    # Add names appearing before common action/speech hints.
    patterns = [
        rf"([\u4e00-\u9fff]{{2,4}})(?=(?:{ACTION_OR_SPEECH_HINTS}))",
        r"^\s*([\u4e00-\u9fff]{2,4})(?:第一次|走进|看着|发现|让|站在|跪在|脸色|沉默|皱眉|转身)",
    ]
    for pattern in patterns:
        for raw_name in re.findall(pattern, text, flags=re.MULTILINE):
            cleaned = _clean_name(raw_name)
            if cleaned and cleaned not in names:
                names.append(cleaned)

    if not names:
        names = ["主角"]

    return names[:8]


def _make_characters(chapters: List[Chapter]) -> Tuple[List[Dict], Dict[str, str]]:
    all_text = "\n".join(ch.content for ch in chapters)
    names = _guess_names(all_text)

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


def _adapt_dialogue_line(line: str, adaptation_style: str) -> str:
    line = line.strip()
    if not line:
        return line

    if adaptation_style == "dramatic":
        if not line.endswith(("。", "！", "？", "!", "?")):
            line += "！"
        if len(line) < 12:
            line = line.rstrip("。！？!?") + "，这件事不会就这样结束！"
        return line

    if adaptation_style == "colloquial":
        replacements = {
            "大人": "您",
            "今日": "今天",
            "此事": "这事",
            "为何": "为什么",
            "不可": "不行",
            "并非": "不是",
        }
        for old, new in replacements.items():
            line = line.replace(old, new)
        if not line.endswith(("。", "！", "？", "!", "?")):
            line += "。"
        return line

    return line


def _build_rule_based_yaml(novel_text: str, adaptation_style: str = "faithful") -> str:
    chapters = parse_chapters(novel_text)
    characters, name_to_id = _make_characters(chapters)
    char_id_to_name = {item["id"]: item["name"] for item in characters}
    fallback_char_id = characters[0]["id"] if characters else "char_001"
    style_label = ADAPTATION_STYLE_LABELS.get(adaptation_style, "忠于原文")

    source_chapters = [
        {"id": chapter.chapter_id, "title": chapter.title}
        for chapter in chapters
    ]

    scenes = []
    chapter_scripts = []
    dialogue_index = []
    dialogue_counter = 1

    for idx, chapter in enumerate(chapters, start=1):
        dialogues_raw = _extract_dialogues(chapter.content)

        scene_char_ids = set()
        dialogue_items = []
        scene_id = f"scene_{idx:03d}"

        for speaker, line, emotion in dialogues_raw:
            speaker_id = name_to_id.get(speaker, fallback_char_id)
            scene_char_ids.add(speaker_id)
            adapted_line = _adapt_dialogue_line(line, adaptation_style)
            dialogue_id = f"dialogue_{dialogue_counter:03d}"
            dialogue_counter += 1

            speaker_name = char_id_to_name.get(speaker_id, speaker)
            dialogue_item = {
                "id": dialogue_id,
                "speaker": speaker_id,
                "speaker_name": speaker_name,
                "line": adapted_line,
                "emotion": emotion,
            }
            dialogue_items.append(dialogue_item)
            dialogue_index.append(
                {
                    "id": dialogue_id,
                    "chapter_id": chapter.chapter_id,
                    "chapter_title": chapter.title,
                    "scene_id": scene_id,
                    "speaker": speaker_id,
                    "speaker_name": speaker_name,
                    "line": adapted_line,
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
                if adaptation_style == "dramatic":
                    sentence = sentence[:110] + "，现场气氛随之紧绷。"
                elif adaptation_style == "colloquial":
                    sentence = sentence[:120].replace("第一次", "头一回")
                else:
                    sentence = sentence[:120]
                actions.append(sentence)
            if len(actions) >= 4:
                break

        if not actions:
            actions = [summarize_content(chapter.content, 100)]

        if adaptation_style == "dramatic":
            transition = "快速切至下一场，保留悬念"
        elif adaptation_style == "colloquial":
            transition = "自然转到下一场"
        else:
            transition = "切至下一场"

        scenes.append(
            {
                "id": scene_id,
                "source_chapter": chapter.chapter_id,
                "title": chapter.title,
                "location": "根据原文场景整理",
                "time": "未明确",
                "characters": sorted(scene_char_ids),
                "summary": chapter.summary,
                "action": actions,
                "dialogue": dialogue_items,
                "transition": transition,
            }
        )

        chapter_scripts.append(
            {
                "chapter_id": chapter.chapter_id,
                "chapter_title": chapter.title,
                "summary": chapter.summary,
                "scene_ids": [scene_id],
            }
        )

    title = "AI 改编剧本"
    if chapters:
        first_title = re.sub(r"^第\s*[0-9一二三四五六七八九十百千万两〇零]+\s*章\s*", "", chapters[0].title)
        title = first_title.strip() or title

    if adaptation_style == "dramatic":
        logline = "一段强化冲突、悬念与情绪张力的小说改编剧本初稿。"
        theme = "人物在更强烈的矛盾和选择中推动故事发展。"
    elif adaptation_style == "colloquial":
        logline = "一段更适合直接表演和口语表达的小说改编剧本初稿。"
        theme = "通过自然对白和清晰场景推进人物关系。"
    else:
        logline = "一段忠于原文情节与人物关系的结构化剧本初稿。"
        theme = "人物在原文冲突中推进故事，并逐步揭示真相。"

    data = {
        "schema_version": "1.1",
        "title": title,
        "source": {
            "type": "novel",
            "chapters": source_chapters,
        },
        "logline": logline,
        "theme": theme,
        "adaptation_style": style_label,
        "characters": characters,
        "chapter_scripts": chapter_scripts,
        "scenes": scenes,
        "dialogue_index": dialogue_index,
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
    model: Optional[str] = None,
    adaptation_style: str = "faithful",
) -> Dict:
    chapters = parse_chapters(novel_text)
    provider = (provider or "local").lower()
    adaptation_style = adaptation_style or "faithful"

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

    if provider == "local":
        yaml_text = _build_rule_based_yaml(novel_text, adaptation_style=adaptation_style)
        return _package_result(
            yaml_text=yaml_text,
            chapter_count=len(chapters),
            message="本地演示模型已生成 v0.3.1 YAML，无需 API Key。",
            mock_mode=True,
            provider="local",
            model=model or "local-rule",
        )

    client = LLMClient()

    if client.is_mock() and provider != "qiniu":
        yaml_text = _build_rule_based_yaml(novel_text, adaptation_style=adaptation_style)
        return _package_result(
            yaml_text=yaml_text,
            chapter_count=len(chapters),
            message="Mock 模式已生成可演示 YAML。",
            mock_mode=True,
            provider="local",
            model="local-rule",
        )

    try:
        prompt = build_generation_prompt(novel_text, chapter_payload, style, language, adaptation_style)
        yaml_text = client.generate_text(prompt, provider=provider, model=model)
        validation = validate_yaml_text(yaml_text)

        if not validation["valid"]:
            repair_prompt = build_repair_prompt(yaml_text, validation["errors"], adaptation_style)
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
