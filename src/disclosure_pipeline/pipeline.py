"""采集流程编排。"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .atomic_io import atomic_write_bytes, atomic_write_json, atomic_write_text
from .classification import classify_annual_report_title
from .pdf_tools import validate_pdf_bytes
from .sources.base import DisclosureSource
from .versioning import select_current_version


def _safe_filename(value: str) -> str:
    return re.sub(r'[/\\:*?"<>|\s]+', "_", value).strip("_")


def read_issuers(path: str | Path) -> list[dict[str, str]]:
    """读取发行人CSV，兼容中英文字段名。"""

    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    issuers: list[dict[str, str]] = []
    for row_number, row in enumerate(rows, start=2):
        code = (row.get("code") or row.get("证券代码") or "").strip()
        name = (row.get("name") or row.get("证券简称") or "").strip()
        if not code:
            raise ValueError(f"输入文件第{row_number}行缺少证券代码")
        issuers.append({"code": code.zfill(6), "name": name})
    return issuers


def collect_annual_reports(
    source: DisclosureSource,
    input_csv: str | Path,
    fiscal_year: int,
    output_dir: str | Path,
    download: bool = True,
    min_pdf_bytes: int = 100_000,
) -> dict[str, Any]:
    """运行年度报告采集，并写出可追溯的结果清单。"""

    output = Path(output_dir)
    documents_dir = output / "documents"
    output.mkdir(parents=True, exist_ok=True)
    issuers = read_issuers(input_csv)
    started_at = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, Any]] = []

    for issuer in issuers:
        record: dict[str, Any] = {
            "source": source.name,
            "issuer_code": issuer["code"],
            "issuer_name": issuer["name"],
            "fiscal_year": fiscal_year,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "status": "",
            "decision": None,
            "announcements": [],
            "document": None,
            "error": "",
        }
        try:
            announcements = list(
                source.list_annual_reports(
                    issuer_code=issuer["code"],
                    issuer_name=issuer["name"],
                    fiscal_year=fiscal_year,
                )
            )
            record["announcements"] = [
                {
                    **item.to_dict(),
                    "classification": classify_annual_report_title(
                        item.title, fiscal_year
                    ).to_dict(),
                }
                for item in announcements
            ]
            decision = select_current_version(announcements, fiscal_year)
            record["decision"] = decision.to_dict()
            record["status"] = decision.status

            if decision.selected_record_id and download:
                selected = next(
                    item
                    for item in announcements
                    if item.record_id == decision.selected_record_id
                )
                content = source.download(selected)
                validation = validate_pdf_bytes(content, min_bytes=min_pdf_bytes)
                document_record = {
                    "record_id": selected.record_id,
                    "source_url": selected.document_url,
                    "validation": validation.to_dict(),
                    "relative_path": "",
                }
                if validation.valid:
                    published_date = selected.published_at[:10]
                    filename = (
                        f"{issuer['code']}_{_safe_filename(issuer['name'])}_"
                        f"{fiscal_year}_annual_report_{published_date}_"
                        f"{selected.record_id}.pdf"
                    )
                    destination = documents_dir / filename
                    atomic_write_bytes(destination, content)
                    document_record["relative_path"] = str(
                        destination.relative_to(output)
                    )
                    record["status"] = "downloaded"
                else:
                    record["status"] = "invalid_document"
                record["document"] = document_record
        except Exception as exc:
            record["status"] = "error"
            record["error"] = f"{type(exc).__name__}: {exc}"
        records.append(record)

    finished_at = datetime.now(timezone.utc).isoformat()
    summary = {
        "source": source.name,
        "fiscal_year": fiscal_year,
        "input_file": str(Path(input_csv)),
        "started_at": started_at,
        "finished_at": finished_at,
        "issuer_count": len(issuers),
        "status_counts": {
            status: sum(row["status"] == status for row in records)
            for status in sorted({row["status"] for row in records})
        },
    }
    atomic_write_text(
        output / "records.jsonl",
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n" for row in records
        ),
    )
    atomic_write_json(output / "run_summary.json", summary)
    return {"summary": summary, "records": records}


def raw_response_recorder(output_dir: str | Path):
    """创建原始响应记录函数，供来源适配器使用。"""

    directory = Path(output_dir) / "raw_responses"
    counter = 0

    def record(value: dict[str, Any]) -> None:
        nonlocal counter
        counter += 1
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        atomic_write_json(directory / f"{timestamp}_{counter:04d}.json", value)

    return record
