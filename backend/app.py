from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .chapter_parser import parse_chapters_payload
from .config import get_settings
from .file_parser import extract_text_from_upload
from .graph_builder import build_character_graph_from_yaml
from .schemas import (
    ExtractTextResponse,
    GenerateScriptRequest,
    GenerateScriptResponse,
    GraphRequest,
    ParseChaptersRequest,
    ParseChaptersResponse,
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
    version="1.1.0",
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
    return {
        "status": "ok",
        "version": "1.1.0",
        "default_provider": settings.llm_provider,
        "default_model": settings.llm_model,
        "mock_mode": settings.use_mock_llm,
    }


@app.get("/api/example")
async def get_example():
    if EXAMPLE_PATH.exists():
        return {"novel_text": EXAMPLE_PATH.read_text(encoding="utf-8")}
    return {"novel_text": ""}


@app.get("/api/models")
async def get_models():
    """Return model options for the frontend selector."""
    return {
        "providers": [
            {
                "value": "local",
                "label": "本地演示模型",
                "models": [
                    {"value": "local-rule", "label": "本地规则演示模型（无需 API Key）"}
                ],
            },
            {
                "value": "qiniu",
                "label": "七牛云 API",
                "models": [
                    {"value": settings.llm_model or "deepseek-v3", "label": f"七牛云 {settings.llm_model or 'deepseek-v3'}"},
                    {"value": "deepseek-v3", "label": "七牛云 DeepSeek V3"},
                    {"value": "deepseek-chat", "label": "七牛云 DeepSeek Chat"},
                ],
            },
        ],
        "default_provider": "local",
        "default_model": "local-rule",
    }


@app.post("/api/extract-text", response_model=ExtractTextResponse)
async def extract_text_api(file: UploadFile = File(...)):
    return await extract_text_from_upload(file)


@app.post("/api/parse-chapters", response_model=ParseChaptersResponse)
async def parse_chapters_api(payload: ParseChaptersRequest):
    return parse_chapters_payload(payload.novel_text)


@app.post("/api/generate-script", response_model=GenerateScriptResponse)
async def generate_script_api(payload: GenerateScriptRequest):
    result = generate_script_yaml(
        novel_text=payload.novel_text,
        style=payload.style,
        language=payload.language,
        provider=payload.provider,
        model=payload.model,
    )
    return result


@app.post("/api/validate-yaml", response_model=ValidateYamlResponse)
async def validate_yaml_api(payload: ValidateYamlRequest):
    result = validate_yaml_text(payload.yaml_text)
    return result


@app.post("/api/character-graph")
async def character_graph_api(payload: GraphRequest):
    return build_character_graph_from_yaml(payload.yaml_text)
