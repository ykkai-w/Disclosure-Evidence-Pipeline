from disclosure_pipeline.models import Announcement
from disclosure_pipeline.versioning import select_current_version


def announcement(record_id, title, date):
    return Announcement(
        source="fixture",
        record_id=record_id,
        issuer_code="000001",
        issuer_name="示例公司",
        title=title,
        published_at=date,
        document_url=f"https://example.test/{record_id}.pdf",
    )


def test_latest_revision_replaces_original():
    rows = [
        announcement("a1", "示例公司2025年年度报告", "2026-03-30"),
        announcement(
            "a2",
            "示例公司2025年年度报告（修订版）",
            "2026-04-02T09:00:00+08:00",
        ),
        announcement("a3", "示例公司2025年年度报告摘要", "2026-03-30"),
    ]
    decision = select_current_version(rows, 2025)
    assert decision.status == "selected"
    assert decision.selected_record_id == "a2"
    assert decision.record_statuses == {
        "a3": "not_candidate",
        "a1": "superseded",
        "a2": "current",
    }


def test_same_day_unique_marked_version_is_selected():
    rows = [
        announcement(
            "a1", "示例公司2025年年度报告", "2026-03-30T00:00:00Z"
        ),
        announcement(
            "a2", "示例公司2025年年度报告（更正版）", "2026-03-30"
        ),
    ]
    decision = select_current_version(rows, 2025)
    assert decision.selected_record_id == "a2"


def test_same_day_unresolved_tie_is_explicit():
    rows = [
        announcement("a1", "甲公司2025年年度报告", "2026-03-30"),
        announcement("a2", "乙公司2025年年度报告", "2026-03-30"),
    ]
    decision = select_current_version(rows, 2025)
    assert decision.status == "ambiguous"
    assert decision.selected_record_id is None
    assert set(decision.record_statuses.values()) == {"ambiguous"}


def test_mixed_timezone_formats_sort_without_error():
    rows = [
        announcement("a1", "示例公司2025年年度报告", "2026-03-30"),
        announcement(
            "a2", "示例公司2025年年度报告（修订版）", "2026-04-01T00:00:00Z"
        ),
    ]
    decision = select_current_version(rows, 2025)
    assert decision.selected_record_id == "a2"


def test_local_midnight_and_plain_date_remain_same_publication_day():
    rows = [
        announcement(
            "a1",
            "示例公司2025年年度报告",
            "2026-03-30T00:00:00+08:00",
        ),
        announcement(
            "a2", "示例公司2025年年度报告（更正版）", "2026-03-30"
        ),
    ]
    decision = select_current_version(rows, 2025)
    assert decision.status == "selected"
    assert decision.selected_record_id == "a2"
