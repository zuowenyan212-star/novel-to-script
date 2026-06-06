from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ParseChaptersRequest(BaseModel):
    novel_text: str = Field(..., min_length=1)


class ChapterInfo(BaseModel):
    chapter_id: str
    title: str
    word_count: int
    summary: str = ""


class ParseChaptersResponse(BaseModel):
    chapter_count: int
    total_word_count: int
    chapters: List[ChapterInfo]


class GenerateScriptRequest(BaseModel):
    novel_text: str = Field(..., min_length=1)
    style: str = "影视剧本"
    language: str = "zh-CN"
    provider: str = "local"
    model: Optional[str] = None
    # v0.3: adaptation style selector.
    # values: faithful / dramatic / colloquial
    adaptation_style: str = "faithful"


class ValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    label: str
    role: str = ""
    description: str = ""


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: int = 1
    label: str = ""
    relation: str = "neutral"
    relation_label: str = "同场"
    color: str = "#94a3b8"
    evidence: str = ""


class CharacterGraph(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class GenerateScriptResponse(BaseModel):
    success: bool
    yaml: str = ""
    data: Optional[Dict[str, Any]] = None
    validation: ValidationResult
    chapter_count: int = 0
    message: str = ""
    mock_mode: bool = False
    provider: str = "local"
    model: str = ""
    graph: CharacterGraph = Field(default_factory=CharacterGraph)


class ValidateYamlRequest(BaseModel):
    yaml_text: str = Field(..., min_length=1)


class ValidateYamlResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    data: Optional[Dict[str, Any]] = None


class GraphRequest(BaseModel):
    yaml_text: str = Field(..., min_length=1)


class ExtractTextResponse(BaseModel):
    text: str
    filename: str = ""
    file_type: str = ""
    message: str = ""


class VideoAssistRequest(BaseModel):
    novel_text: str = ""
    yaml_text: str = ""
    provider: str = "local"
    model: Optional[str] = None
    visual_style: str = "manga"


class ShotSuggestion(BaseModel):
    scene_id: str = ""
    scene_title: str = ""
    shot: str = ""
    camera: str = ""
    prompt: str = ""


class EmotionSuggestion(BaseModel):
    scene_id: str = ""
    character: str = ""
    emotion: str = ""
    micro_expression: str = ""
    prompt: str = ""


class ScenePromptSuggestion(BaseModel):
    scene_id: str = ""
    scene_title: str = ""
    location: str = ""
    atmosphere: str = ""
    prompt: str = ""


class VideoAssistResponse(BaseModel):
    success: bool
    message: str = ""
    provider: str = "local"
    model: str = ""
    visual_style: str = "manga"
    storyboard: List[ShotSuggestion] = Field(default_factory=list)
    emotions: List[EmotionSuggestion] = Field(default_factory=list)
    scene_prompts: List[ScenePromptSuggestion] = Field(default_factory=list)
    raw: str = ""
