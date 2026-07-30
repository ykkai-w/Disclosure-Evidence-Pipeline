"""披露文档章节标题定位。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping, Sequence

from pypdf import PdfReader

from .models import SectionMatch


DEFAULT_HEADINGS: dict[str, tuple[str, ...]] = {
    "业务概况": (
        "业务概要",
        "报告期内公司从事的主要业务",
        "报告期内公司从事的业务情况",
    ),
    "核心竞争力": ("核心竞争力分析", "报告期内核心竞争力分析"),
    "研发投入": ("研发投入", "研发人员情况", "研发投入情况"),
}


def _normalize_line(value: str) -> str:
    compact = re.sub(r"\s+", "", value)
    compact = re.sub(r"^[一二三四五六七八九十百0-9]+[、.．]\s*", "", compact)
    return compact.strip()


def locate_sections(
    pages: Sequence[str],
    headings: Mapping[str, Sequence[str]] | None = None,
    max_heading_length: int = 80,
) -> list[SectionMatch]:
    """在按页文本中查找章节标题候选。

    返回符合条件的标题行并保留页码，正文范围可结合文档目录和前后章节继续确定。
    """

    selected_headings = headings or DEFAULT_HEADINGS
    matches: list[SectionMatch] = []
    seen: set[tuple[str, int, str]] = set()

    for page_number, text in enumerate(pages, start=1):
        for original_line in (text or "").splitlines():
            line = _normalize_line(original_line)
            if not line or len(line) > max_heading_length:
                continue
            if re.search(r"\.{3,}|…{2,}", line):
                continue
            for section, variants in selected_headings.items():
                for heading in variants:
                    normalized_heading = _normalize_line(heading)
                    if line == normalized_heading or line.endswith(normalized_heading):
                        key = (section, page_number, line)
                        if key not in seen:
                            seen.add(key)
                            matches.append(
                                SectionMatch(
                                    section=section,
                                    heading=heading,
                                    page=page_number,
                                    line=original_line.strip(),
                                )
                            )
                        break
    return matches


def extract_pdf_pages(path: str | Path) -> list[str]:
    reader = PdfReader(str(path), strict=False)
    return [page.extract_text() or "" for page in reader.pages]


def locate_sections_in_pdf(
    path: str | Path,
    headings: Mapping[str, Sequence[str]] | None = None,
) -> list[SectionMatch]:
    return locate_sections(extract_pdf_pages(path), headings=headings)
