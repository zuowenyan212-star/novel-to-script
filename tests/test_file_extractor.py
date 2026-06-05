from io import BytesIO
import unittest
from zipfile import ZipFile

from backend.file_extractor import FileExtractionError, extract_text_from_file


def make_docx_bytes(text: str) -> bytes:
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "</w:t></w:r></w:p><w:p><w:r><w:t>")
    )
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{escaped}</w:t></w:r></w:p>
  </w:body>
</w:document>"""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


class FileExtractorTest(unittest.TestCase):
    def test_extracts_utf8_text_file(self):
        result = extract_text_from_file("novel.txt", "第一章\n正文".encode("utf-8"))

        self.assertEqual(result.source_type, "text")
        self.assertIn("第一章", result.text)

    def test_extracts_docx_file(self):
        result = extract_text_from_file("novel.docx", make_docx_bytes("第一章 雨夜\n林舟回来。"))

        self.assertEqual(result.source_type, "word")
        self.assertIn("林舟回来", result.text)

    def test_rejects_unsupported_file_type(self):
        with self.assertRaises(FileExtractionError):
            extract_text_from_file("novel.exe", b"data")


if __name__ == "__main__":
    unittest.main()

