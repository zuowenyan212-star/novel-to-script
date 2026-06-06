import io
from fastapi import HTTPException, UploadFile

try:
    from docx import Document
except Exception:
    Document = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None


async def extract_text_from_upload(file: UploadFile) -> dict:
    """Extract text from txt/md/docx/image files.

    Note:
    - .docx is supported through python-docx.
    - legacy .doc is not directly supported because it needs external office converters.
    - image OCR needs local Tesseract OCR installed.
    """
    filename = file.filename or ""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    if ext in {"txt", "md"}:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("gbk", errors="ignore")
        return {
            "text": text,
            "filename": filename,
            "file_type": ext,
            "message": "文本文件解析成功",
        }

    if ext == "docx":
        if Document is None:
            raise HTTPException(status_code=400, detail="缺少 python-docx 依赖，无法解析 Word 文件")
        try:
            document = Document(io.BytesIO(content))
            paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
            return {
                "text": text,
                "filename": filename,
                "file_type": ext,
                "message": "Word 文件解析成功",
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Word 解析失败：{exc}")

    if ext == "doc":
        raise HTTPException(status_code=400, detail="暂不支持旧版 .doc，请另存为 .docx 后上传")

    if ext in {"png", "jpg", "jpeg", "webp", "bmp"}:
        if Image is None or pytesseract is None:
            raise HTTPException(
                status_code=400,
                detail="图片 OCR 依赖未安装。请安装 pillow、pytesseract，并确保本机已安装 Tesseract OCR。"
            )
        try:
            image = Image.open(io.BytesIO(content))
            try:
                text = pytesseract.image_to_string(image, lang="chi_sim+eng")
            except Exception:
                text = pytesseract.image_to_string(image)
            return {
                "text": text.strip(),
                "filename": filename,
                "file_type": ext,
                "message": "图片 OCR 解析完成",
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"图片识别失败：{exc}")

    raise HTTPException(status_code=400, detail="暂不支持该文件类型，请上传 txt、md、docx 或图片文件")
