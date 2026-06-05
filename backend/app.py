from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from .chapter_parser import parse_chapters_payload
from .config import get_settings
from .schemas import (
    ParseChaptersRequest,
    ParseChaptersResponse,
    GenerateScriptRequest,
    GenerateScriptResponse,
    ValidateYamlRequest,
    ValidateYamlResponse,
)
from .script_generator import generate_script_yaml
from .yaml_validator import validate_yaml_text


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
EXAMPLE_PATH = ROOT_DIR / "examples" / "novel_sample.txt"

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="将 3 个章节以上小说文本转换为结构化 YAML 剧本。",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "mock_mode": settings.use_mock_llm,
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok", "mock_mode": settings.use_mock_llm}


@app.get("/api/example")
async def get_example():
    if EXAMPLE_PATH.exists():
        return {"novel_text": EXAMPLE_PATH.read_text(encoding="utf-8")}
    return {"novel_text": ""}


@app.post("/api/parse-chapters", response_model=ParseChaptersResponse)
async def parse_chapters_api(payload: ParseChaptersRequest):
    return parse_chapters_payload(payload.novel_text)


@app.post("/api/generate-script", response_model=GenerateScriptResponse)
async def generate_script_api(payload: GenerateScriptRequest):
    result = generate_script_yaml(
        novel_text=payload.novel_text,
        style=payload.style,
        language=payload.language,
    )
    return result


@app.post("/api/validate-yaml", response_model=ValidateYamlResponse)
async def validate_yaml_api(payload: ValidateYamlRequest):
    result = validate_yaml_text(payload.yaml_text)
    return result
