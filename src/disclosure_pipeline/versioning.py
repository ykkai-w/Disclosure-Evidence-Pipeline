"""年度报告版本选择。"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Sequence

from .classification import classify_annual_report_title
from .models import Announcement, VersionDecision


def _date_key(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = datetime.strptime(value[:10], "%Y-%m-%d")
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _calendar_date(value: str) -> date:
    """保留披露来源展示的自然日，不让时区换算改变公告日期。"""

    return date.fromisoformat(value[:10])


def select_current_version(
    announcements: Sequence[Announcement], fiscal_year: int
) -> VersionDecision:
    """从同一发行人的公告中选择当前完整年度报告。

    先排除非正文公告，再选择发布日期最新的完整报告。最新日期只有一份时直接
    采用；同日有多份时，仅在其中恰有一份明确标注为修订、更正或更新版本时采用。
    其余同日冲突返回 ambiguous。
    """

    classifications = {
        item.record_id: classify_annual_report_title(item.title, fiscal_year)
        for item in announcements
    }
    statuses: dict[str, str] = {}
    candidates: list[Announcement] = []
    for item in announcements:
        classification = classifications[item.record_id]
        if classification.is_cancelled:
            statuses[item.record_id] = "cancelled"
        elif classification.is_full_annual_report:
            candidates.append(item)
        else:
            statuses[item.record_id] = "not_candidate"

    if not candidates:
        return VersionDecision(
            status="not_found",
            selected_record_id=None,
            reason="没有找到符合标题规则的完整年度报告",
            record_statuses=statuses,
            candidate_record_ids=[],
        )

    candidates.sort(
        key=lambda item: (
            _calendar_date(item.published_at),
            _date_key(item.published_at),
            item.record_id,
        )
    )
    latest_date = max(_calendar_date(item.published_at) for item in candidates)
    latest = [
        item
        for item in candidates
        if _calendar_date(item.published_at) == latest_date
    ]

    selected: Announcement | None = None
    if len(latest) == 1:
        selected = latest[0]
        reason = "采用发布日期最新的完整年度报告"
    else:
        marked = [
            item
            for item in latest
            if classifications[item.record_id].is_explicitly_versioned
        ]
        if len(marked) == 1:
            selected = marked[0]
            reason = "同日存在多份正文，采用唯一明确标注的修订、更正或更新版本"
        else:
            for item in candidates:
                statuses[item.record_id] = (
                    "ambiguous" if item in latest else "superseded"
                )
            return VersionDecision(
                status="ambiguous",
                selected_record_id=None,
                reason="最新日期存在多份无法仅凭标题区分的完整报告",
                record_statuses=statuses,
                candidate_record_ids=[item.record_id for item in candidates],
            )

    for item in candidates:
        statuses[item.record_id] = (
            "current" if item.record_id == selected.record_id else "superseded"
        )
    return VersionDecision(
        status="selected",
        selected_record_id=selected.record_id,
        reason=reason,
        record_statuses=statuses,
        candidate_record_ids=[item.record_id for item in candidates],
    )
