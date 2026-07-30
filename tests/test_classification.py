import pytest

from disclosure_pipeline.classification import classify_annual_report_title


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("甲公司2025年年度报告", True),
        ("甲公司2025年度报告", True),
        ("甲公司2025年报", True),
        ("甲公司2025年年度报告（修订版）", True),
        ("甲公司2025年年度报告摘要", False),
        ("甲公司2025年年度报告（英文版）", False),
        ("H股公告-甲公司2025年年度报告", False),
        ("关于甲公司2025年年度报告的更正公告", False),
        ("甲公司2025年年度报告业绩说明会", False),
        ("甲公司2024年年度报告", False),
    ],
)
def test_title_boundaries(title, expected):
    result = classify_annual_report_title(title, 2025)
    assert result.is_full_annual_report is expected


def test_html_and_spaces_are_normalized():
    result = classify_annual_report_title(
        "<em>甲公司</em> 2025 年年度报告（更正版）", 2025
    )
    assert result.is_full_annual_report
    assert result.is_corrected
    assert "<em>" not in result.normalized_title
