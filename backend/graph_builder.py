from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

from .yaml_codec import load_yaml


FRIENDLY_KEYWORDS = [
    "帮助", "帮忙", "保护", "守护", "信任", "支持", "并肩", "同行", "同伴", "伙伴",
    "朋友", "兄弟", "姐妹", "师徒", "安慰", "救", "感谢", "扶", "搀扶", "拥抱",
    "点头", "微笑", "答应", "同意", "照顾", "并肩作战",
]

HOSTILE_KEYWORDS = [
    "敌", "敌人", "仇", "仇恨", "恨", "杀", "刺", "攻击", "拔剑", "出手", "威胁",
    "逼问", "质问", "争执", "反驳", "怒", "怒视", "冷冷", "冷笑", "背叛", "陷害",
    "诬告", "罪", "偷", "打", "骂", "冲突", "对峙", "不信", "怀疑", "隐瞒",
]


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _read_yaml(yaml_text: str) -> Optional[Dict[str, Any]]:
    try:
        data = load_yaml(yaml_text)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _scene_text(scene: Dict[str, Any], char_id_to_name: Dict[str, str]) -> str:
    parts: List[str] = []

    for field in ["title", "summary", "location", "time", "transition"]:
        if scene.get(field):
            parts.append(_stringify(scene.get(field)))

    for action in scene.get("action", []) or []:
        parts.append(_stringify(action))

    for dialogue in scene.get("dialogue", []) or scene.get("dialogues", []) or []:
        if not isinstance(dialogue, dict):
            parts.append(_stringify(dialogue))
            continue
        speaker = _stringify(dialogue.get("speaker_name") or char_id_to_name.get(_stringify(dialogue.get("speaker")), ""))
        line = _stringify(dialogue.get("line") or dialogue.get("text") or dialogue.get("content"))
        emotion = _stringify(dialogue.get("emotion"))
        parts.append(f"{speaker} {emotion} {line}")

    return "。".join(part for part in parts if part)


def _score_relation(text: str) -> Tuple[int, int]:
    friendly = sum(text.count(keyword) for keyword in FRIENDLY_KEYWORDS)
    hostile = sum(text.count(keyword) for keyword in HOSTILE_KEYWORDS)
    return friendly, hostile


def _relation_from_scores(friendly_score: int, hostile_score: int) -> Tuple[str, str, str]:
    if hostile_score > friendly_score:
        return "hostile", "敌对", "#ef4444"
    if friendly_score > hostile_score:
        return "friendly", "友好", "#22c55e"
    return "neutral", "同场", "#94a3b8"


def build_character_graph_from_data(data: Optional[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Build a character relationship graph.

    v0.4 upgrade:
    - nodes still come from characters/scenes/dialogue.
    - edges are no longer only "co-appearance".
    - the scene text is scanned for relationship signals.
    - red hostile edges represent conflict/opposition.
    - green friendly edges represent alliance/support.
    - gray neutral edges remain for co-appearance without clear polarity.
    """
    if not isinstance(data, dict):
        return {"nodes": [], "edges": []}

    char_id_to_name: Dict[str, str] = {}
    char_meta: Dict[str, Dict[str, str]] = {}

    for item in data.get("characters", []) or []:
        if not isinstance(item, dict):
            name = _stringify(item)
            if name:
                char_id_to_name[name] = name
                char_meta[name] = {"role": "", "description": ""}
            continue

        char_id = _stringify(item.get("id") or item.get("name"))
        name = _stringify(item.get("name") or item.get("id"))
        if not char_id or not name:
            continue

        char_id_to_name[char_id] = name
        char_meta[char_id] = {
            "role": _stringify(item.get("role")),
            "description": _stringify(item.get("description")),
        }

    nodes: Dict[str, Dict[str, Any]] = {}
    edge_stats: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def ensure_node(char_id_or_name: str) -> None:
        value = _stringify(char_id_or_name)
        if not value:
            return
        name = char_id_to_name.get(value, value)
        meta = char_meta.get(value, {})
        nodes[value] = {
            "id": value,
            "label": name,
            "role": meta.get("role", ""),
            "description": meta.get("description", ""),
        }

    for char_id in char_id_to_name:
        ensure_node(char_id)

    for scene in data.get("scenes", []) or []:
        if not isinstance(scene, dict):
            continue

        scene_people: List[str] = []

        for value in scene.get("characters", []) or []:
            char_id = _stringify(value.get("id") if isinstance(value, dict) else value)
            if char_id:
                scene_people.append(char_id)
                ensure_node(char_id)

        for dialogue in scene.get("dialogue", []) or scene.get("dialogues", []) or []:
            if isinstance(dialogue, dict):
                speaker = _stringify(dialogue.get("speaker") or dialogue.get("character"))
                if speaker:
                    scene_people.append(speaker)
                    ensure_node(speaker)

        unique_people = list(dict.fromkeys(scene_people))
        if len(unique_people) < 2:
            continue

        text = _scene_text(scene, char_id_to_name)
        friendly_score, hostile_score = _score_relation(text)

        for a, b in combinations(unique_people, 2):
            key = tuple(sorted([a, b]))
            stat = edge_stats.setdefault(
                key,
                {
                    "weight": 0,
                    "friendly": 0,
                    "hostile": 0,
                    "evidence": [],
                },
            )
            stat["weight"] += 1
            stat["friendly"] += friendly_score
            stat["hostile"] += hostile_score

            summary = _stringify(scene.get("summary") or scene.get("title"))
            if summary and summary not in stat["evidence"]:
                stat["evidence"].append(summary)

    edges: List[Dict[str, Any]] = []
    for (source, target), stat in edge_stats.items():
        relation, relation_label, color = _relation_from_scores(
            int(stat.get("friendly", 0)),
            int(stat.get("hostile", 0)),
        )
        weight = int(stat.get("weight", 1))
        evidence_items = stat.get("evidence", [])[:2]
        evidence = "；".join(evidence_items)

        if relation == "neutral":
            label = f"同场 {weight} 次"
        else:
            label = f"{relation_label}｜同场 {weight} 次"

        edges.append(
            {
                "source": source,
                "target": target,
                "weight": weight,
                "relation": relation,
                "relation_label": relation_label,
                "color": color,
                "label": label,
                "evidence": evidence,
            }
        )

    return {"nodes": list(nodes.values()), "edges": edges}


def build_character_graph_from_yaml(yaml_text: str) -> Dict[str, List[Dict[str, Any]]]:
    return build_character_graph_from_data(_read_yaml(yaml_text))
