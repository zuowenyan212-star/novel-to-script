"""Zero-install local demo server implemented with the Python standard library."""

from __future__ import annotations

import argparse
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
else:
    from .chapter_parser import parse_chapters_payload
    from .graph_builder import build_character_graph_from_yaml
    from .script_generator import generate_script_yaml
    from .yaml_validator import validate_yaml_text


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
                    "mode": "local-demo",
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
                if provider != "local":
                    raise DemoRequestError(
                        "快速启动仅支持本地演示模型。使用七牛云 API 请按 README 安装环境后启动。"
                    )
                result = generate_script_yaml(
                    novel_text=str(payload.get("novel_text", "")),
                    style=str(payload.get("style", "影视剧本")),
                    language=str(payload.get("language", "zh-CN")),
                    provider="local",
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


def _model_options() -> dict[str, Any]:
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
            }
        ],
        "default_provider": "local",
        "default_model": "local-rule",
    }


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
    parser = argparse.ArgumentParser(description="启动零安装本地演示服务器。")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = DemoServer((args.host, args.port), DemoHandler)
    print("AI 小说转剧本工具 - 快速启动")
    print(f"访问地址：http://{args.host}:{args.port}")
    print("快速启动仅使用本地演示模型，按 Ctrl+C 停止服务。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
