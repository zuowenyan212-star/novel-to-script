"""Zero-install local demo server implemented with the Python standard library."""

from __future__ import annotations

import argparse
import getpass
import os
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend.chapter_parser import parse_chapters_payload
    from backend.graph_builder import build_character_graph_from_yaml
    from backend.script_generator import generate_script_yaml
    from backend.yaml_validator import validate_yaml_text
    from backend.visual_assistant import generate_video_assist
else:
    from .chapter_parser import parse_chapters_payload
    from .graph_builder import build_character_graph_from_yaml
    from .script_generator import generate_script_yaml
    from .yaml_validator import validate_yaml_text
    from .visual_assistant import generate_video_assist


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
MAX_REQUEST_BYTES = 20 * 1024 * 1024


class DemoRequestError(ValueError):
    pass


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "NovelToScriptQuickStart/1.0"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send_file(
                BASE_DIR / "templates" / "index.html",
                "text/html; charset=utf-8",
            )
            return
        if path == "/health":
            self._send_json(
                {
                    "status": "ok",
                    "server": "quick-start",
                    "mode": "quick-start",
                    "qiniu_configured": _has_qiniu_api_key(),
                }
            )
            return
        if path == "/api/example":
            sample = PROJECT_ROOT / "examples" / "novel_sample.txt"
            text = sample.read_text(encoding="utf-8") if sample.exists() else ""
            self._send_json({"novel_text": text})
            return
        if path == "/api/models":
            self._send_json(_model_options())
            return
        if path.startswith("/static/"):
            self._serve_static(path)
            return
        self._send_json({"detail": "接口不存在"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/extract-text":
                filename, content = self._read_multipart_file()
                self._send_json(_extract_text(filename, content))
                return

            payload = self._read_json()
            if path == "/api/parse-chapters":
                self._send_json(
                    parse_chapters_payload(str(payload.get("novel_text", "")))
                )
                return
            if path == "/api/generate-script":
                provider = str(payload.get("provider", "local") or "local")
                result = generate_script_yaml(
                    novel_text=str(payload.get("novel_text", "")),
                    style=str(payload.get("style", "影视剧本")),
                    language=str(payload.get("language", "zh-CN")),
                    provider=provider,
                    model=str(payload.get("model", "local-rule")),
                    adaptation_style=str(
                        payload.get("adaptation_style", "faithful")
                    ),
                )
                self._send_json(result)
                return
            if path == "/api/validate-yaml":
                self._send_json(
                    validate_yaml_text(str(payload.get("yaml_text", "")))
                )
                return
            if path == "/api/character-graph":
                self._send_json(
                    build_character_graph_from_yaml(
                        str(payload.get("yaml_text", ""))
                    )
                )
                return
            if path == "/api/video-assist":
                self._send_json(
                    generate_video_assist(
                        novel_text=str(payload.get("novel_text", "")),
                        yaml_text=str(payload.get("yaml_text", "")),
                        provider=str(payload.get("provider", "local") or "local"),
                        model=str(payload.get("model", "")) or None,
                        visual_style=str(payload.get("visual_style", "manga") or "manga"),
                    )
                )
                return
            self._send_json({"detail": "接口不存在"}, status=HTTPStatus.NOT_FOUND)
        except DemoRequestError as exc:
            self._send_json({"detail": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json(
                {"detail": "请求体不是有效的 JSON。"},
                status=HTTPStatus.BAD_REQUEST,
            )
        except Exception as exc:
            self._send_json(
                {"detail": f"请求处理失败：{exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def _serve_static(self, request_path: str) -> None:
        relative = unquote(request_path.removeprefix("/static/"))
        static_root = (BASE_DIR / "static").resolve()
        target = (static_root / relative).resolve()
        if target != static_root and static_root not in target.parents:
            self._send_json({"detail": "禁止访问"}, status=HTTPStatus.FORBIDDEN)
            return

        content_types = {
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }
        self._send_file(
            target,
            content_types.get(target.suffix.lower(), "application/octet-stream"),
        )

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_REQUEST_BYTES:
            raise DemoRequestError("请求内容过大，快速启动模式最大支持 20 MB。")
        return self.rfile.read(length)

    def _read_json(self) -> dict[str, Any]:
        raw = self._read_body()
        data = json.loads(raw.decode("utf-8") if raw else "{}")
        if not isinstance(data, dict):
            raise DemoRequestError("JSON 请求体必须是对象。")
        return data

    def _read_multipart_file(self) -> tuple[str, bytes]:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise DemoRequestError("文件上传请求格式错误。")

        message = BytesParser(policy=default).parsebytes(
            (
                f"Content-Type: {content_type}\r\n"
                "MIME-Version: 1.0\r\n\r\n"
            ).encode("utf-8")
            + self._read_body()
        )
        for part in message.iter_parts():
            if part.get_content_disposition() != "form-data":
                continue
            if part.get_param("name", header="content-disposition") != "file":
                continue
            filename = Path(part.get_filename() or "uploaded.txt").name
            return filename, part.get_payload(decode=True) or b""
        raise DemoRequestError("未找到上传文件。")

    def _send_json(
        self,
        data: Any,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"detail": "文件不存在"}, status=HTTPStatus.NOT_FOUND)
            return
        raw = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class DemoServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def _clean_env_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().strip('"').strip("'")


def _env_path() -> Path:
    return PROJECT_ROOT / ".env"


def _load_dotenv_for_quick_start() -> None:
    """Load .env without python-dotenv for quick-start mode."""
    path = _env_path()
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _has_qiniu_api_key() -> bool:
    key = _clean_env_value(os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"))
    return key not in {
        "",
        "your_qiniu_api_key_here",
        "your_api_key",
        "你的七牛云API_KEY",
        "你的七牛云api_key",
    }


def _qiniu_model() -> str:
    return _clean_env_value(os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL")) or "deepseek-v3"


def _qiniu_base_url() -> str:
    return _clean_env_value(os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")) or "https://api.qnaigc.com/v1"


def _model_options() -> dict[str, Any]:
    qiniu_model = _qiniu_model()
    qiniu_configured = _has_qiniu_api_key()

    return {
        "providers": [
            {
                "value": "local",
                "label": "本地演示模型",
                "models": [
                    {
                        "value": "local-rule",
                        "label": "本地规则演示模型（无需 API Key）",
                    }
                ],
            },
            {
                "value": "qiniu",
                "label": "七牛云 API" + ("（已配置）" if qiniu_configured else "（需配置 API Key）"),
                "models": [
                    {
                        "value": qiniu_model,
                        "label": f"七牛云 {qiniu_model}",
                    },
                    {"value": "deepseek-v3", "label": "七牛云 DeepSeek V3"},
                    {"value": "deepseek-chat", "label": "七牛云 DeepSeek Chat"},
                ],
            },
        ],
        "default_provider": "qiniu" if qiniu_configured else "local",
        "default_model": qiniu_model if qiniu_configured else "local-rule",
        "qiniu_configured": qiniu_configured,
        "qiniu_base_url": _qiniu_base_url(),
    }


def _write_qiniu_env(api_key: str, model: str, base_url: str, use_system_proxy: str) -> None:
    content = f"""# Quick-start generated Qiniu config
LLM_PROVIDER=qiniu
LLM_API_KEY={api_key}
LLM_BASE_URL={base_url}
LLM_MODEL={model}
LLM_USE_SYSTEM_PROXY={use_system_proxy}
USE_MOCK_LLM=false
APP_HOST=127.0.0.1
APP_PORT=8000
MAX_INPUT_CHARS=30000
"""
    _env_path().write_text(content, encoding="utf-8")
    os.environ["LLM_PROVIDER"] = "qiniu"
    os.environ["LLM_API_KEY"] = api_key
    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_MODEL"] = model
    os.environ["LLM_USE_SYSTEM_PROXY"] = use_system_proxy


def _setup_qiniu_interactively() -> None:
    """Prompt user for Qiniu API settings when quick-start launches."""
    _load_dotenv_for_quick_start()
    if _has_qiniu_api_key():
        print(f"已检测到七牛云配置：模型 {_qiniu_model()}，接口 {_qiniu_base_url()}")
        return

    print("\n未检测到七牛云 API Key。")
    print("快速启动可以直接调用七牛云模型；也可以跳过，继续使用本地演示模型。")
    answer = input("是否现在配置七牛云 API Key？输入 y 配置，直接回车跳过：").strip().lower()
    if answer not in {"y", "yes"}:
        print("已跳过七牛云配置，页面默认使用本地演示模型。")
        return

    api_key = getpass.getpass("请输入七牛云 API Key（输入时不会显示）：").strip()
    if not api_key:
        print("未输入 API Key，继续使用本地演示模型。")
        return

    model = input("请输入模型名，默认 deepseek-v3：").strip() or "deepseek-v3"
    base_url = input("请输入 Base URL，默认 https://api.qnaigc.com/v1：").strip() or "https://api.qnaigc.com/v1"
    proxy_answer = input("是否使用系统代理？需要代理访问七牛云时输入 y，默认 n：").strip().lower()
    use_proxy = "true" if proxy_answer in {"y", "yes"} else "false"

    _write_qiniu_env(api_key=api_key, model=model, base_url=base_url, use_system_proxy=use_proxy)
    print(f"已写入 .env，快速启动页面将默认使用七牛云模型：{model}")


def _extract_text(filename: str, content: bytes) -> dict[str, str]:
    if not content:
        raise DemoRequestError("上传文件为空。")

    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        text = _decode_text(content)
        message = "文本文件解析成功"
    elif suffix == ".docx":
        text = _extract_docx(content)
        message = "Word 文件解析成功"
    elif suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        raise DemoRequestError(
            "快速启动不包含图片 OCR。请按 README 安装环境并配置 Tesseract 后使用。"
        )
    else:
        raise DemoRequestError("快速启动支持上传 txt、md 和 docx 文件。")

    return {
        "text": text.strip(),
        "filename": filename,
        "file_type": suffix.removeprefix("."),
        "message": message,
    }


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _extract_docx(content: bytes) -> str:
    try:
        with ZipFile(BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml")
    except (BadZipFile, KeyError) as exc:
        raise DemoRequestError("Word 文件解析失败，请确认文件是有效的 .docx。") from exc

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as exc:
        raise DemoRequestError("Word 文档结构异常。") from exc

    word_namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    paragraphs: list[str] = []
    for paragraph in root.findall(f".//{{{word_namespace}}}p"):
        parts = [
            node.text or ""
            for node in paragraph.iter()
            if node.tag == f"{{{word_namespace}}}t"
        ]
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def main() -> None:
    parser = argparse.ArgumentParser(description="启动快速体验服务器。")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--setup-qiniu",
        action="store_true",
        help="启动前交互式配置七牛云 API Key，让快速启动也可以调用大模型。",
    )
    args = parser.parse_args()

    _load_dotenv_for_quick_start()
    if args.setup_qiniu:
        _setup_qiniu_interactively()

    server = DemoServer((args.host, args.port), DemoHandler)
    print("AI 小说转剧本工具 - 快速启动")
    print(f"访问地址：http://{args.host}:{args.port}")
    if _has_qiniu_api_key():
        print(f"七牛云模型已启用：{_qiniu_model()}，页面默认选择七牛云 API。")
    else:
        print("未配置七牛云 API Key，页面默认使用本地演示模型。")
    print("按 Ctrl+C 停止服务。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
