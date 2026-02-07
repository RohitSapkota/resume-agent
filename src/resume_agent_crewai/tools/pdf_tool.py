from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from pypdf import PdfReader


def _normalize_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _wrap_line(line: str, max_chars: int) -> list[str]:
    if not line.strip():
        return [""]

    words = line.split()
    wrapped: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            wrapped.append(current)
            current = word
            continue
        for part in textwrap.wrap(word, width=max(8, max_chars)):
            wrapped.append(part)
        current = ""

    if current:
        wrapped.append(current)
    return wrapped


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_simple_text_pdf(lines: list[str]) -> bytes:
    page_width = 612
    page_height = 792
    margin = 48
    font_size = 11
    line_height = 14
    text_top = page_height - margin
    lines_per_page = max(1, int((page_height - (2 * margin)) / line_height))

    pages: list[list[str]] = [
        lines[i : i + lines_per_page] for i in range(0, len(lines), lines_per_page)
    ] or [[]]

    objects: list[tuple[int, bytes]] = []
    max_obj_num = 3 + (len(pages) * 2)

    objects.append((1, b"<< /Type /Catalog /Pages 2 0 R >>"))

    kids = []
    for idx in range(len(pages)):
        page_obj_num = 4 + (idx * 2)
        kids.append(f"{page_obj_num} 0 R")
    pages_body = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>".encode(
        "utf-8"
    )
    objects.append((2, pages_body))

    objects.append((3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))

    for idx, page_lines in enumerate(pages):
        page_obj_num = 4 + (idx * 2)
        content_obj_num = 5 + (idx * 2)

        content_ops = [
            "BT",
            f"/F1 {font_size} Tf",
            f"{line_height} TL",
            f"{margin} {text_top} Td",
        ]
        for line in page_lines:
            content_ops.append(f"({_escape_pdf_text(line)}) Tj")
            content_ops.append("T*")
        content_ops.append("ET")

        content_stream = "\n".join(content_ops).encode("utf-8")
        content_body = (
            f"<< /Length {len(content_stream)} >>\nstream\n".encode("utf-8")
            + content_stream
            + b"\nendstream"
        )

        page_body = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj_num} 0 R >>"
        ).encode("utf-8")

        objects.append((page_obj_num, page_body))
        objects.append((content_obj_num, content_body))

    objects.sort(key=lambda item: item[0])

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    parts = [header]
    offsets = [0] * (max_obj_num + 1)
    cursor = len(header)

    for obj_num, obj_body in objects:
        obj_blob = f"{obj_num} 0 obj\n".encode("utf-8") + obj_body + b"\nendobj\n"
        offsets[obj_num] = cursor
        parts.append(obj_blob)
        cursor += len(obj_blob)

    xref_offset = cursor
    xref_lines = [f"xref\n0 {max_obj_num + 1}\n", "0000000000 65535 f \n"]
    for obj_num in range(1, max_obj_num + 1):
        xref_lines.append(f"{offsets[obj_num]:010d} 00000 n \n")
    trailer = (
        f"trailer\n<< /Size {max_obj_num + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    )
    parts.append("".join(xref_lines).encode("utf-8"))
    parts.append(trailer.encode("utf-8"))

    return b"".join(parts)


class ReadResumePdfInput(BaseModel):
    pdf_path: str = Field(
        default="src/resume_agent_crewai/Resume.pdf",
        description="Path to the source resume PDF file.",
    )


class ReadResumePdfTool(BaseTool):
    name: str = "read_resume_pdf"
    description: str = (
        "Read text from a resume PDF file and return normalized plain text. "
        "Use this before analyzing or rewriting resume content."
    )
    args_schema: Type[BaseModel] = ReadResumePdfInput

    def _run(self, pdf_path: str = "src/resume_agent_crewai/Resume.pdf") -> str:
        path = Path(pdf_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Resume PDF not found: {path}")

        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)

        extracted = _normalize_text("\n".join(pages))
        if not extracted:
            raise ValueError(f"Could not extract text from PDF: {path}")
        return extracted


class WriteResumePdfInput(BaseModel):
    resume_text: str = Field(
        ...,
        description="Final factual resume text that should be written to a PDF.",
    )
    output_path: str = Field(
        default="src/resume_agent_crewai/resume_updated.pdf",
        description="Output path for the updated resume PDF file.",
    )


class WriteResumePdfTool(BaseTool):
    name: str = "write_resume_pdf"
    description: str = (
        "Write resume text into a new PDF file and return the output file path. "
        "Use this after resume updates are finalized."
    )
    args_schema: Type[BaseModel] = WriteResumePdfInput

    def _run(
        self,
        resume_text: str,
        output_path: str = "src/resume_agent_crewai/resume_updated.pdf",
    ) -> str:
        content = _normalize_text(resume_text)
        if not content:
            raise ValueError("resume_text is empty. Cannot create PDF.")

        out_path = Path(output_path).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        max_chars = 100
        lines_to_draw: list[str] = []
        for raw_line in content.splitlines():
            lines_to_draw.extend(_wrap_line(raw_line, max_chars))

        pdf_bytes = _build_simple_text_pdf(lines_to_draw)
        out_path.write_bytes(pdf_bytes)
        return str(out_path)
