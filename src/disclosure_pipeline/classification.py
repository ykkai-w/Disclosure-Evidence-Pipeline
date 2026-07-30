"""公告标题分类。"""

from __future__ import annotations

import re

from .models import TitleClassification


def _normalize_title(title: str) -> str:
    text = re.sub(r"<[^>]+>", "", title or "")
    return re.sub(r"\s+", " ", text).strip()


def classify_annual_report_title(title: str, fiscal_year: int) -> TitleClassification:
    """判断标题是否为指定会计年度的完整年度报告。

    判断采用收敛的标题语法。标题必须以规范的年度报告名称结尾，仅允许在末尾
    添加修订、更正或更新标记。摘要、英文版、H股版、取消公告和说明公告均排除。
    """

    normalized = _normalize_title(title)
    compact = re.sub(r"\s+", "", normalized)

    is_abstract = "摘要" in compact
    is_english = bool(re.search(r"英文|english", compact, re.IGNORECASE))
    is_h_share = bool(re.search(r"(?:H|Ｈ)股", compact, re.IGNORECASE))
    is_cancelled = "取消" in compact
    is_explanatory_notice = bool(
        re.search(r"(?:提示性公告|更正公告|补充公告|说明公告)$", compact)
    )
    is_revised = "修订" in compact and not is_explanatory_notice
    is_corrected = "更正" in compact and not is_explanatory_notice
    is_updated = "更新" in compact and not is_explanatory_notice

    year = re.escape(str(fiscal_year))
    full_report_pattern = re.compile(
        rf"{year}(?:年年度报告|年度报告|年年报|年报)"
        rf"(?:[（(][^）)]*(?:修订|更正|更新)[^）)]*[）)])?$"
    )
    title_matches = bool(full_report_pattern.search(compact))
    excluded = (
        is_abstract
        or is_english
        or is_h_share
        or is_cancelled
        or is_explanatory_notice
    )
    is_full = title_matches and not excluded

    if is_full:
        reason = "标题符合完整年度报告格式"
    elif is_abstract:
        reason = "标题标明为摘要"
    elif is_english:
        reason = "标题标明为英文版"
    elif is_h_share:
        reason = "标题标明为H股披露版本"
    elif is_cancelled:
        reason = "标题标明公告已取消"
    elif is_explanatory_notice:
        reason = "标题为说明性公告而非报告正文"
    else:
        reason = "标题不符合指定年度完整报告格式"

    return TitleClassification(
        normalized_title=normalized,
        is_full_annual_report=is_full,
        is_abstract=is_abstract,
        is_english=is_english,
        is_h_share=is_h_share,
        is_cancelled=is_cancelled,
        is_explanatory_notice=is_explanatory_notice,
        is_revised=is_revised,
        is_corrected=is_corrected,
        is_updated=is_updated,
        reason=reason,
    )
