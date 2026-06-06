from pathlib import Path

from backend.dev_server import _extract_text, _model_options
from backend.script_generator import generate_script_yaml


ROOT = Path(__file__).resolve().parents[1]


def test_quick_start_exposes_local_and_qiniu_models():
    options = _model_options()
    assert options["default_provider"] in {"local", "qiniu"}
    provider_values = [item["value"] for item in options["providers"]]
    assert "local" in provider_values
    assert "qiniu" in provider_values


def test_quick_start_template_does_not_require_jinja_rendering():
    html = (ROOT / "backend" / "templates" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "{{" not in html
    assert "{%" not in html
    assert '<table class="data-table character-table">' in html
    assert '<tbody id="dialoguePreview"></tbody>' in html


def test_quick_start_text_upload_uses_standard_library():
    result = _extract_text("novel.txt", "第一章 开端".encode("utf-8"))
    assert result["text"] == "第一章 开端"
    assert result["file_type"] == "txt"


def test_quick_start_local_generation_without_third_party_yaml():
    novel_text = (ROOT / "examples" / "novel_sample.txt").read_text(
        encoding="utf-8"
    )
    result = generate_script_yaml(
        novel_text,
        provider="local",
        model="local-rule",
    )
    assert result["success"] is True
    assert result["validation"]["valid"] is True
    assert result["chapter_count"] >= 3
