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


class ValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class GenerateScriptResponse(BaseModel):
    success: bool
    yaml: str = ""
    data: Optional[Dict[str, Any]] = None
    validation: ValidationResult
    chapter_count: int = 0
    message: str = ""
    mock_mode: bool = False


class ValidateYamlRequest(BaseModel):
    yaml_text: str = Field(..., min_length=1)


class ValidateYamlResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    data: Optional[Dict[str, Any]] = None
