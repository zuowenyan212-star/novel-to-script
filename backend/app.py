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
from .visual_assistant import generate_video_assist
from .schemas import (
    ExtractTextResponse,
    GenerateScriptRequest,
    GenerateScriptResponse,
    GraphRequest,
    ParseChaptersRequest,
    ParseChaptersResponse,
    ValidateYamlRequest,
    ValidateYamlResponse,
    VideoAssistRequest,
    VideoAssistResponse,
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
    version="1.4.0",
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
        "version": "1.4.0",
        "default_provider": settings.llm_provider,
        "default_model": settings.llm_model,
        "mock_mode": settings.use_mock_llm,
    }


@app.get("/api/example")
async def get_example():
    if EXAMPLE_PATH.exists():
        return {"novel_text": EXAMPLE_PATH.read_text(encoding="utf-8")}
    return {"novel_text": ""}



def _has_qiniu_api_key() -> bool:
    key = (settings.llm_api_key or settings.openai_api_key or "").strip()
    return key not in {
        "",
        "your_qiniu_api_key_here",
        "your_api_key",
        "你的七牛云API_KEY",
        "你的七牛云api_key",
    }


@app.get("/api/models")
async def get_models():
    """Return model options for the frontend selector."""
    qiniu_model = settings.llm_model or "deepseek-v3"
    qiniu_configured = _has_qiniu_api_key()
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
                "label": "七牛云 API" + ("（已配置）" if qiniu_configured else "（需配置 API Key）"),
                "models": [
                    {"value": qiniu_model, "label": f"七牛云 {qiniu_model}"},
                    {"value": "deepseek-v3", "label": "七牛云 DeepSeek V3"},
                    {"value": "deepseek-chat", "label": "七牛云 DeepSeek Chat"},
                ],
            },
        ],
        "default_provider": "qiniu" if qiniu_configured else "local",
        "default_model": qiniu_model if qiniu_configured else "local-rule",
        "qiniu_configured": qiniu_configured,
        "qiniu_base_url": settings.llm_base_url,
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
        adaptation_style=payload.adaptation_style,
    )
    return result


@app.post("/api/validate-yaml", response_model=ValidateYamlResponse)
async def validate_yaml_api(payload: ValidateYamlRequest):
    result = validate_yaml_text(payload.yaml_text)
    return result


@app.post("/api/character-graph")
async def character_graph_api(payload: GraphRequest):
    return build_character_graph_from_yaml(payload.yaml_text)


@app.post("/api/video-assist", response_model=VideoAssistResponse)
async def video_assist_api(payload: VideoAssistRequest):
    return generate_video_assist(
        novel_text=payload.novel_text,
        yaml_text=payload.yaml_text,
        provider=payload.provider,
        model=payload.model,
        visual_style=payload.visual_style,
    )
