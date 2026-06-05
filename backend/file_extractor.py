"""Extract plain text from uploaded novel source files."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
from typing import Callable
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile
from urllib.parse import unquote


SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".docx", ".pdf"}


class FileExtractionError(ValueError):
    """Raised when a file cannot be converted to plain text."""


@dataclass(frozen=True)
class ExtractedText:
    filename: str
    extension: str
    text: str
    source_type: str

    def as_dict(self) -> dict[str, str | int | bool]:
        return {
            "success": True,
            "filename": self.filename,
            "extension": self.extension,
            "source_type": self.source_type,
            "text": self.text,
            "char_count": len(self.text),
        }


def extract_text_from_file(filename: str, content: bytes) -> ExtractedText:
    safe_name = Path(filename or "uploaded.txt").name
    extension = Path(safe_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        supported = "、".join(sorted(SUPPORTED_EXTENSIONS))
        raise FileExtractionError(f"暂不支持 {extension or '无扩展名'} 文件，请上传 {supported}。")
    if not content:
        raise FileExtractionError("上传文件为空，请重新选择文件。")

    if extension in {".txt", ".md", ".markdown"}:
        text = _decode_text(content)
        source_type = "text"
    elif extension == ".docx":
        text = _extract_docx_text(content)
        source_type = "word"
    else:
        text = _extract_pdf_text(content)
        source_type = "pdf"

    cleaned = _clean_text(text)
    if not cleaned:
        raise FileExtractionError("未能从文件中识别到有效文本，请确认文件不是扫描图片或空文档。")
    return ExtractedText(filename=safe_name, extension=extension, text=cleaned, source_type=source_type)


def extract_upload_from_multipart(content_type: str, body: bytes, field_name: str = "file") -> tuple[str, bytes]:
    """Return filename and bytes from a multipart/form-data request body."""
    if "multipart/form-data" not in content_type or "boundary=" not in content_type:
        raise FileExtractionError("文件上传请求格式错误：缺少 multipart/form-data boundary。")

    boundary = _parse_boundary(content_type)
    if not boundary:
        raise FileExtractionError("文件上传请求格式错误：boundary 为空。")

    delimiter = ("--" + boundary).encode("utf-8")
    for raw_part in body.split(delimiter):
        part = raw_part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].rstrip(b"\r\n")

        header_bytes, separator, payload = part.partition(b"\r\n\r\n")
        if not separator:
            header_bytes, separator, payload = part.partition(b"\n\n")
        if not separator:
            continue

        headers = header_bytes.decode("utf-8", errors="replace")
        disposition = _content_disposition(headers)
        if not disposition:
            continue
        if _disposition_value(disposition, "name") != field_name:
            continue

        filename = _disposition_value(disposition, "filename") or _disposition_value(disposition, "filename*")
        filename = _decode_filename(filename) or "uploaded.txt"
        return filename, payload.rstrip(b"\r\n")

    raise FileExtractionError("未找到上传文件字段，请确认表单字段名为 file。")


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _parse_boundary(content_type: str) -> str:
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("boundary="):
            return part.split("=", 1)[1].strip().strip('"')
    return ""


def _content_disposition(headers: str) -> str:
    for line in headers.splitlines():
        if line.lower().startswith("content-disposition:"):
            return line.split(":", 1)[1].strip()
    return ""


def _disposition_value(disposition: str, key: str) -> str:
    for item in disposition.split(";"):
        item = item.strip()
        if item.lower().startswith(key.lower() + "="):
            return item.split("=", 1)[1].strip().strip('"')
    return ""


def _decode_filename(filename: str) -> str:
    if not filename:
        return ""
    if filename.lower().startswith("utf-8''"):
        return unquote(filename[7:])
    return filename


def _extract_docx_text(content: bytes) -> str:
    try:
        with ZipFile(BytesIO(content)) as archive:
            xml = archive.read("word/document.xml")
    except (KeyError, BadZipFile) as exc:
        raise FileExtractionError("Word 文件解析失败，请确认上传的是 .docx 文件。") from exc

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise FileExtractionError("Word 文档结构异常，无法读取正文。") from exc

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        runs: list[str] = []
        for node in paragraph.iter():
            if node.tag == f"{{{namespace['w']}}}t" and node.text:
                runs.append(node.text)
            elif node.tag == f"{{{namespace['w']}}}tab":
                runs.append("\t")
            elif node.tag == f"{{{namespace['w']}}}br":
                runs.append("\n")
        text = "".join(runs).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _extract_pdf_text(content: bytes) -> str:
    extractors: list[Callable[[bytes], str]] = [_extract_pdf_with_pypdf, _extract_pdf_with_pymupdf]
    errors: list[str] = []
    for extractor in extractors:
        try:
            text = extractor(content)
            if text.strip():
                return text
        except ImportError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(f"{extractor.__name__}: {exc}")

    raise FileExtractionError(
        "PDF 解析需要安装 pypdf 或 PyMuPDF；如果 PDF 是扫描图片，还需要先 OCR。"
        + (f" 解析细节：{'；'.join(errors)}" if errors else "")
    )


def _extract_pdf_with_pypdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError as exc:
            raise ImportError("未安装 pypdf/PyPDF2") from exc

    reader = PdfReader(BytesIO(content))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _extract_pdf_with_pymupdf(content: bytes) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise ImportError("未安装 PyMuPDF") from exc

    document = fitz.open(stream=content, filetype="pdf")
    try:
        return "\n".join(page.get_text("text") for page in document)
    finally:
        document.close()


def _clean_text(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()
