"""YAML helpers with a standard-library fallback for the generated subset."""

from __future__ import annotations

import json
import re
from typing import Any


try:
    import yaml as _pyyaml
except Exception:  # PyYAML is optional for the zero-install demo server.
    _pyyaml = None


class SimpleYamlError(ValueError):
    """Raised when the fallback parser cannot understand the YAML input."""


def dump_yaml(data: Any) -> str:
    if _pyyaml is not None:
        return _pyyaml.safe_dump(data, allow_unicode=True, sort_keys=False, indent=2)
    return "\n".join(_dump_lines(data, 0)) + "\n"


def load_yaml(text: str) -> Any:
    cleaned = strip_code_fence(text)
    if _pyyaml is not None:
        return _pyyaml.safe_load(cleaned)
    return _load_simple_yaml(cleaned)


def strip_code_fence(text: str) -> str:
    cleaned = (text or "").strip()
    match = re.match(
        r"^```(?:yaml|yml)?\s*(.*?)\s*```$",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else cleaned


def _dump_lines(value: Any, indent: int) -> list[str]:
    space = " " * indent
    if isinstance(value, dict):
        if not value:
            return [space + "{}"]
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{space}{key}:")
                lines.extend(_dump_lines(item, indent + 2))
            else:
                lines.append(f"{space}{key}: {_format_scalar(item)}")
        return lines

    if isinstance(value, list):
        if not value:
            return [space + "[]"]
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(space + "-")
                lines.extend(_dump_lines(item, indent + 2))
            else:
                lines.append(f"{space}- {_format_scalar(item)}")
        return lines

    return [space + _format_scalar(value)]


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _load_simple_yaml(text: str) -> Any:
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    lines = _prepare_lines(text)
    if not lines:
        return None
    value, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise SimpleYamlError(f"第 {index + 1} 行附近存在无法识别的内容。")
    return value


def _prepare_lines(text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        expanded = raw.replace("\t", "  ")
        indent = len(expanded) - len(expanded.lstrip(" "))
        lines.append((indent, expanded.strip()))
    return lines


def _parse_block(
    lines: list[tuple[int, str]],
    index: int,
    indent: int,
) -> tuple[Any, int]:
    if index >= len(lines):
        return None, index
    current_indent, content = lines[index]
    if current_indent < indent:
        return None, index
    if current_indent > indent:
        raise SimpleYamlError(f"第 {index + 1} 行缩进不正确。")
    if content.startswith("-"):
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_list(
    lines: list[tuple[int, str]],
    index: int,
    indent: int,
) -> tuple[list[Any], int]:
    items: list[Any] = []
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent != indent or not content.startswith("-"):
            break
        remainder = content[1:].strip()
        index += 1

        if not remainder:
            if index < len(lines) and lines[index][0] > indent:
                item, index = _parse_block(lines, index, lines[index][0])
            else:
                item = None
        elif _looks_like_mapping_item(remainder):
            key, raw_value = remainder.split(":", 1)
            item = {
                key.strip(): (
                    _parse_scalar(raw_value.strip()) if raw_value.strip() else None
                )
            }
            if index < len(lines) and lines[index][0] > indent:
                extra, index = _parse_block(lines, index, lines[index][0])
                if not isinstance(extra, dict):
                    raise SimpleYamlError(f"第 {index + 1} 行应继续填写对象字段。")
                item.update(extra)
        else:
            item = _parse_scalar(remainder)
        items.append(item)
    return items, index


def _parse_dict(
    lines: list[tuple[int, str]],
    index: int,
    indent: int,
) -> tuple[dict[str, Any], int]:
    mapping: dict[str, Any] = {}
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent != indent or content.startswith("-"):
            break
        if ":" not in content:
            raise SimpleYamlError(f"第 {index + 1} 行缺少键值分隔符。")
        key, raw_value = content.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        index += 1
        if raw_value:
            mapping[key] = _parse_scalar(raw_value)
        elif index < len(lines) and lines[index][0] > indent:
            mapping[key], index = _parse_block(lines, index, lines[index][0])
        else:
            mapping[key] = None
    return mapping, index


def _looks_like_mapping_item(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_-]*\s*:", value))


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"null", "none", "~"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value in {"[]", "{}"}:
        return [] if value == "[]" else {}
    if value and value[0] in {'"', "'", "[", "{"}:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value.strip("\"'")
    if re.match(r"^-?\d+$", value):
        return int(value)
    if re.match(r"^-?\d+\.\d+$", value):
        return float(value)
    return value
