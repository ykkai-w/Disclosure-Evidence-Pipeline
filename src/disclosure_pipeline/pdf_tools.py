"""PDF文件校验。"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

from pypdf import PdfReader

from .models import PdfValidation


def validate_pdf_bytes(content: bytes, min_bytes: int = 1_000) -> PdfValidation:
    """检查文件头、大小、可读页数，并计算SHA-256。"""

    errors: list[str] = []
    digest = hashlib.sha256(content).hexdigest()
    if not content.startswith(b"%PDF"):
        errors.append("文件头不是PDF")
    if len(content) < min_bytes:
        errors.append(f"文件大小低于设定下限{min_bytes}字节")

    page_count: int | None = None
    if content.startswith(b"%PDF"):
        try:
            page_count = len(PdfReader(io.BytesIO(content), strict=False).pages)
            if page_count < 1:
                errors.append("PDF没有可读页面")
        except Exception as exc:
            errors.append(f"PDF结构无法读取：{type(exc).__name__}")

    return PdfValidation(
        valid=not errors,
        sha256=digest,
        size_bytes=len(content),
        page_count=page_count,
        errors=errors,
    )


def validate_pdf(path: str | Path, min_bytes: int = 1_000) -> PdfValidation:
    return validate_pdf_bytes(Path(path).read_bytes(), min_bytes=min_bytes)
