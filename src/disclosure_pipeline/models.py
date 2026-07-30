"""项目内使用的数据结构。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Announcement:
    """一条来源公告及其必要的出处信息。"""

    source: str
    record_id: str
    issuer_code: str
    issuer_name: str
    title: str
    published_at: str
    document_url: str
    detail_url: str = ""
    source_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TitleClassification:
    """公告标题的可解释分类结果。"""

    normalized_title: str
    is_full_annual_report: bool
    is_abstract: bool
    is_english: bool
    is_h_share: bool
    is_cancelled: bool
    is_explanatory_notice: bool
    is_revised: bool
    is_corrected: bool
    is_updated: bool
    reason: str

    @property
    def is_explicitly_versioned(self) -> bool:
        return self.is_revised or self.is_corrected or self.is_updated

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VersionDecision:
    """一组同类公告的版本选择结果。"""

    status: str
    selected_record_id: str | None
    reason: str
    record_statuses: dict[str, str]
    candidate_record_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PdfValidation:
    """PDF文件的结构检查与摘要信息。"""

    valid: bool
    sha256: str
    size_bytes: int
    page_count: int | None
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SectionMatch:
    """一处章节标题命中。页码从1开始。"""

    section: str
    heading: str
    page: int
    line: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
