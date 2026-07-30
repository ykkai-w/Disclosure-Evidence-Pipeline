"""命令行入口。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .classification import classify_annual_report_title
from .pdf_tools import validate_pdf
from .pipeline import collect_annual_reports, raw_response_recorder
from .sections import locate_sections_in_pdf
from .sources.cninfo import CninfoSource


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="disclosure-pipeline",
        description="上市公司披露文档采集、版本判断、文件校验与章节定位",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify = subparsers.add_parser("classify-title", help="判断公告标题类型")
    classify.add_argument("title")
    classify.add_argument("--year", type=int, required=True)

    validate = subparsers.add_parser("validate-pdf", help="检查PDF文件")
    validate.add_argument("path", type=Path)
    validate.add_argument("--min-bytes", type=int, default=1_000)

    locate = subparsers.add_parser("locate-sections", help="定位常见章节标题")
    locate.add_argument("path", type=Path)

    collect = subparsers.add_parser("collect", help="从披露来源检索年度报告")
    collect.add_argument("--source", choices=["cninfo"], default="cninfo")
    collect.add_argument("--input", type=Path, required=True)
    collect.add_argument("--year", type=int, required=True)
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--no-download", action="store_true")
    collect.add_argument("--min-pdf-bytes", type=int, default=100_000)
    collect.add_argument("--pause", type=float, default=1.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "classify-title":
        result = classify_annual_report_title(args.title, args.year)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "validate-pdf":
        result = validate_pdf(args.path, min_bytes=args.min_bytes)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.valid else 1
    if args.command == "locate-sections":
        result = [row.to_dict() for row in locate_sections_in_pdf(args.path)]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "collect":
        source = CninfoSource(
            pause_seconds=args.pause,
            response_recorder=raw_response_recorder(args.output),
        )
        result = collect_annual_reports(
            source=source,
            input_csv=args.input,
            fiscal_year=args.year,
            output_dir=args.output,
            download=not args.no_download,
            min_pdf_bytes=args.min_pdf_bytes,
        )
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
        return 0
    raise AssertionError(f"未处理的命令：{args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
