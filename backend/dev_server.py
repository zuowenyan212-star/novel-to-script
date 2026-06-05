"""Zero-dependency local HTTP server for demos before installing FastAPI."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import unquote, urlparse


if __package__ in {None, ""}:  # Support `python backend/dev_server.py`.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend.llm_client import LLMConfigurationError, LLMGenerationError
    from backend.script_generator import generate_script_payload, parse_chapter_payload, validate_yaml_payload
else:
    from .llm_client import LLMConfigurationError, LLMGenerationError
    from .script_generator import generate_script_payload, parse_chapter_payload, validate_yaml_payload


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[0]


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "NovelToScriptDemo/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/" or self.path.startswith("/?"):
            self._send_file(BASE_DIR / "templates" / "index.html", "text/html; charset=utf-8")
            return
        if self.path == "/health":
            self._send_json({"status": "ok"})
            return
        if self.path == "/api/example":
            sample = PROJECT_ROOT / "examples" / "novel_sample.txt"
            self._send_json({"novel_text": sample.read_text(encoding="utf-8")})
            return
        if self.path.startswith("/static/"):
            self._serve_static()
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
            if self.path == "/api/parse-chapters":
                self._send_json(parse_chapter_payload(str(payload.get("novel_text", ""))))
                return
            if self.path == "/api/generate-script":
                result = generate_script_payload(
                    str(payload.get("novel_text", "")),
                    style=str(payload.get("style", "影视剧本")),
                    language=str(payload.get("language", "zh-CN")),
                    adaptation_mode=str(payload.get("adaptation_mode", "忠于原文")),
                    detail_level=str(payload.get("detail_level", "标准")),
                )
                self._send_json(result)
                return
            if self.path == "/api/validate-yaml":
                self._send_json(validate_yaml_payload(str(payload.get("yaml_text", "")), bool(payload.get("repair", True))))
                return
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except LLMConfigurationError as exc:
            self._send_json({"success": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except LLMGenerationError as exc:
            self._send_json({"success": False, "error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
        except Exception as exc:
            self._send_json({"success": False, "error": f"请求处理失败：{exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _serve_static(self) -> None:
        relative = unquote(urlparse(self.path).path.removeprefix("/static/"))
        target = (BASE_DIR / "static" / relative).resolve()
        static_root = (BASE_DIR / "static").resolve()
        if static_root not in target.parents and target != static_root:
            self._send_json({"error": "Forbidden"}, status=HTTPStatus.FORBIDDEN)
            return
        content_type = "text/plain; charset=utf-8"
        if target.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif target.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        self._send_file(target, content_type)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        data = json.loads(raw or "{}")
        if not isinstance(data, dict):
            raise ValueError("JSON 请求体必须是对象。")
        return data

    def _send_json(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        raw = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the zero-dependency demo server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    print(f"Serving AI 小说转剧本工具 at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
