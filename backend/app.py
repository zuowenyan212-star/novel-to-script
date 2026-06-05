"""FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .file_extractor import FileExtractionError, extract_text_from_file
from .llm_client import LLMConfigurationError, LLMGenerationError
from .script_generator import generate_script_payload, parse_chapter_payload, validate_yaml_payload


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="AI 小说转剧本工具", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class ParseChaptersRequest(BaseModel):
    novel_text: str = Field(default="", description="完整小说文本")


class GenerateScriptRequest(BaseModel):
    novel_text: str
    style: str = "影视剧本"
    language: str = "zh-CN"
    adaptation_mode: str = "忠于原文"
    detail_level: str = "标准"
    model_mode: str = "local"


class ValidateYamlRequest(BaseModel):
    yaml_text: str
    repair: bool = True


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/example")
def example() -> dict[str, str]:
    sample_path = BASE_DIR.parents[0] / "examples" / "novel_sample.txt"
    return {"novel_text": sample_path.read_text(encoding="utf-8")}


@app.post("/api/extract-text")
async def extract_text_api(file: UploadFile = File(...)):
    try:
        content = await file.read()
        return extract_text_from_file(file.filename or "uploaded.txt", content).as_dict()
    except FileExtractionError as exc:
        return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": f"文件识别失败：{exc}"})


@app.post("/api/parse-chapters")
def parse_chapters_api(payload: ParseChaptersRequest) -> dict[str, object]:
    return parse_chapter_payload(payload.novel_text)


@app.post("/api/generate-script")
def generate_script_api(payload: GenerateScriptRequest):
    try:
        return generate_script_payload(
            payload.novel_text,
            style=payload.style,
            language=payload.language,
            adaptation_mode=payload.adaptation_mode,
            detail_level=payload.detail_level,
            model_mode=payload.model_mode,
        )
    except LLMConfigurationError as exc:
        return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})
    except LLMGenerationError as exc:
        return JSONResponse(status_code=502, content={"success": False, "error": str(exc)})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": f"AI 生成失败：{exc}"})


@app.post("/api/validate-yaml")
def validate_yaml_api(payload: ValidateYamlRequest) -> dict[str, object]:
    return validate_yaml_payload(payload.yaml_text, repair=payload.repair)
