import json
from typing import Any, Dict, List, Optional

from .llm_client import LLMClient, LLMError, strip_markdown_fence
from .yaml_codec import load_yaml


STYLE_LABELS = {
    "manga": "漫剧风格，画面有漫画分镜感、强情绪特写、适合 AI 漫剧短片",
    "live": "真人短剧风格，写实镜头、演员表演、短视频节奏",
    "cinematic": "电影感风格，强调光影、景别、镜头运动和氛围",
    "anime": "动画风格，二次元画面、夸张表情、动作清晰",
}


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_load_yaml(yaml_text: str) -> Dict[str, Any]:
    try:
        data = load_yaml(yaml_text or "")
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _scene_brief(data: Dict[str, Any], limit: int = 6) -> List[Dict[str, Any]]:
    char_map = {
        str(item.get("id")): str(item.get("name") or item.get("id"))
        for item in data.get("characters", []) or []
        if isinstance(item, dict)
    }
    scenes = []
    for scene in (data.get("scenes", []) or [])[:limit]:
        if not isinstance(scene, dict):
            continue
        people = []
        for cid in scene.get("characters", []) or []:
            cid = str(cid.get("id") if isinstance(cid, dict) else cid)
            people.append(char_map.get(cid, cid))
        lines = []
        for dialogue in scene.get("dialogue", []) or []:
            if isinstance(dialogue, dict):
                speaker = dialogue.get("speaker_name") or char_map.get(str(dialogue.get("speaker")), dialogue.get("speaker", ""))
                line = dialogue.get("line", "")
                emotion = dialogue.get("emotion", "")
                lines.append(f"{speaker}（{emotion}）：{line}")
        scenes.append(
            {
                "scene_id": scene.get("id", ""),
                "scene_title": scene.get("title", ""),
                "location": scene.get("location", ""),
                "time": scene.get("time", ""),
                "characters": people,
                "summary": scene.get("summary", ""),
                "action": scene.get("action", [])[:4] if isinstance(scene.get("action"), list) else [],
                "dialogue": lines[:6],
            }
        )
    return scenes


def _build_prompt(novel_text: str, yaml_text: str, visual_style: str) -> str:
    data = _safe_load_yaml(yaml_text)
    scenes = _scene_brief(data)
    style_text = STYLE_LABELS.get(visual_style, STYLE_LABELS["manga"])

    compact_novel = (novel_text or "")[:6000]
    compact_yaml = json.dumps(
        {
            "title": data.get("title", ""),
            "characters": data.get("characters", [])[:12] if isinstance(data.get("characters"), list) else [],
            "scenes": scenes,
        },
        ensure_ascii=False,
    )

    return f"""
你是短剧导演、分镜师和 AI 视频提示词专家。请基于小说原文和已生成剧本，输出 AI 短片制作建议。

视觉风格：{style_text}

必须只输出 JSON，不要输出 Markdown，不要输出解释。JSON 结构必须如下：
{{
  "storyboard": [
    {{
      "scene_id": "scene_001",
      "scene_title": "场景标题",
      "shot": "分镜建议，例如：中景建立场景，随后切主角特写",
      "camera": "镜头语言，例如：低机位、推镜、过肩镜头",
      "prompt": "用于 AI 短片/图像生成的中文提示词"
    }}
  ],
  "emotions": [
    {{
      "scene_id": "scene_001",
      "character": "角色名",
      "emotion": "当前情绪",
      "micro_expression": "微表情，例如：眼神闪躲、嘴角压低、眉心收紧",
      "prompt": "角色表演/微表情提示词"
    }}
  ],
  "scene_prompts": [
    {{
      "scene_id": "scene_001",
      "scene_title": "场景标题",
      "location": "地点",
      "atmosphere": "氛围",
      "prompt": "场景描绘提示词"
    }}
  ]
}}

要求：
1. storyboard 至少 3 条，最多 8 条。
2. emotions 至少 3 条，最多 12 条，必须标清角色。
3. scene_prompts 至少 3 条，最多 8 条。
4. prompt 要适合后续生成 AI 短片或关键帧。
5. 不要虚构与原文完全无关的新人物。

已生成剧本摘要：
{compact_yaml}

小说原文节选：
{compact_novel}
""".strip()


def _extract_json(text: str) -> Dict[str, Any]:
    cleaned = strip_markdown_fence(text or "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}


def _normalize_items(items: Any, fields: List[str], limit: int) -> List[Dict[str, str]]:
    normalized = []
    if not isinstance(items, list):
        return normalized
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        normalized.append({field: str(item.get(field, "") or "") for field in fields})
    return normalized


def generate_video_assist(
    novel_text: str,
    yaml_text: str,
    provider: str = "local",
    model: Optional[str] = None,
    visual_style: str = "manga",
) -> Dict[str, Any]:
    provider = (provider or "local").lower()
    if provider == "local":
        return {
            "success": False,
            "message": "分镜建议、角色情绪捕获和场景提示词需要选择大模型。请将模型方案切换为“七牛云 API”后再使用。",
            "provider": provider,
            "model": model or "",
            "visual_style": visual_style,
            "storyboard": [],
            "emotions": [],
            "scene_prompts": [],
            "raw": "",
        }

    try:
        client = LLMClient()
        prompt = _build_prompt(novel_text, yaml_text, visual_style)
        raw = client.generate_text(prompt, provider=provider, model=model)
        data = _extract_json(raw)

        storyboard = _normalize_items(
            data.get("storyboard"),
            ["scene_id", "scene_title", "shot", "camera", "prompt"],
            8,
        )
        emotions = _normalize_items(
            data.get("emotions"),
            ["scene_id", "character", "emotion", "micro_expression", "prompt"],
            12,
        )
        scene_prompts = _normalize_items(
            data.get("scene_prompts"),
            ["scene_id", "scene_title", "location", "atmosphere", "prompt"],
            8,
        )

        if not (storyboard or emotions or scene_prompts):
            return {
                "success": False,
                "message": "大模型已返回内容，但未解析到有效 JSON 结构。请重试或检查模型输出。",
                "provider": provider,
                "model": model or "",
                "visual_style": visual_style,
                "storyboard": [],
                "emotions": [],
                "scene_prompts": [],
                "raw": raw,
            }

        return {
            "success": True,
            "message": "AI 短片辅助建议生成完成。",
            "provider": provider,
            "model": model or "",
            "visual_style": visual_style,
            "storyboard": storyboard,
            "emotions": emotions,
            "scene_prompts": scene_prompts,
            "raw": raw,
        }
    except LLMError as exc:
        return {
            "success": False,
            "message": str(exc),
            "provider": provider,
            "model": model or "",
            "visual_style": visual_style,
            "storyboard": [],
            "emotions": [],
            "scene_prompts": [],
            "raw": "",
        }
