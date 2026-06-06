from itertools import combinations
from typing import Any, Dict, List, Tuple

import yaml


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _read_yaml(yaml_text: str) -> Dict[str, Any] | None:
    try:
        data = yaml.safe_load(yaml_text)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def build_character_graph_from_data(data: Dict[str, Any] | None) -> Dict[str, List[Dict[str, Any]]]:
    """Build a character relationship graph.

    Relationship rule:
    characters appearing in the same scene are connected. Edge weight equals
    the number of scenes in which the two characters co-appear.
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
    edge_weights: Dict[Tuple[str, str], int] = {}

    def ensure_node(char_id_or_name: str):
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
        for a, b in combinations(unique_people, 2):
            key = tuple(sorted([a, b]))
            edge_weights[key] = edge_weights.get(key, 0) + 1

    edges = []
    for (source, target), weight in edge_weights.items():
        edges.append({
            "source": source,
            "target": target,
            "weight": weight,
            "label": f"同场 {weight} 次",
        })

    return {"nodes": list(nodes.values()), "edges": edges}


def build_character_graph_from_yaml(yaml_text: str) -> Dict[str, List[Dict[str, Any]]]:
    return build_character_graph_from_data(_read_yaml(yaml_text))
