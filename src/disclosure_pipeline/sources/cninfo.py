"""巨潮资讯网适配器。"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable, Sequence
from zoneinfo import ZoneInfo

import requests

from ..models import Announcement
from .base import DisclosureSource


class CninfoSource(DisclosureSource):
    """通过巨潮资讯网公开网页接口检索A股年度报告。"""

    name = "cninfo"
    search_url = "https://www.cninfo.com.cn/new/information/topSearch/query"
    announcement_url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    static_base = "https://static.cninfo.com.cn/"
    market_timezone = ZoneInfo("Asia/Shanghai")

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: float = 45,
        pause_seconds: float = 1.0,
        response_recorder: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.pause_seconds = pause_seconds
        self.response_recorder = response_recorder
        self.headers = {
            "User-Agent": "Mozilla/5.0 disclosure-evidence-pipeline/0.1",
            "Referer": "https://www.cninfo.com.cn/",
        }

    def _post(self, url: str, data: dict[str, Any]) -> Any:
        fetched_at = datetime.now(timezone.utc).isoformat()
        response = self.session.post(
            url,
            data=data,
            headers=self.headers,
            timeout=self.timeout,
        )
        record = {
            "source": self.name,
            "request_url": url,
            "request_data": data,
            "fetched_at": fetched_at,
            "http_status": response.status_code,
            "response_text": response.text,
        }
        if self.response_recorder:
            self.response_recorder(record)
        response.raise_for_status()
        time.sleep(self.pause_seconds)
        return response.json()

    def _find_issuer(
        self, issuer_code: str, issuer_name: str
    ) -> dict[str, Any] | None:
        payload = self._post(
            self.search_url, {"keyWord": issuer_code, "maxNum": 10}
        )
        match = next(
            (item for item in payload if str(item.get("code", "")) == issuer_code),
            None,
        )
        if match or not issuer_name:
            return match
        payload = self._post(
            self.search_url, {"keyWord": issuer_name, "maxNum": 10}
        )
        return next(
            (
                item
                for item in payload
                if str(item.get("code", "")) == issuer_code
                or str(item.get("zwjc", "")).replace(" ", "")
                == issuer_name.replace(" ", "")
            ),
            None,
        )

    def list_annual_reports(
        self,
        issuer_code: str,
        issuer_name: str,
        fiscal_year: int,
    ) -> Sequence[Announcement]:
        issuer = self._find_issuer(issuer_code, issuer_name)
        if not issuer:
            return []

        org_id = str(issuer["orgId"])
        publication_year = fiscal_year + 1
        date_window = (
            f"{publication_year}-01-01~{publication_year}-12-31"
        )
        page_size = 30
        page_number = 1
        rows: list[dict[str, Any]] = []

        while True:
            data = {
                "pageNum": page_number,
                "pageSize": page_size,
                "column": "szse",
                "tabName": "fulltext",
                "stock": f"{issuer_code},{org_id}",
                "category": "category_ndbg_szsh",
                "seDate": date_window,
                "isHLtitle": "true",
            }
            payload = self._post(self.announcement_url, data)
            page_rows = payload.get("announcements") or []
            rows.extend(page_rows)
            total = int(
                payload.get("totalRecordNum")
                or payload.get("totalAnnouncement")
                or 0
            )
            if (
                not page_rows
                or len(page_rows) < page_size
                or (total and len(rows) >= total)
            ):
                break
            page_number += 1
            if page_number > 100:
                raise RuntimeError("公告分页超过100页，已停止检索")

        announcements: list[Announcement] = []
        for row in rows:
            timestamp = row.get("announcementTime")
            published_at = (
                datetime.fromtimestamp(
                    timestamp / 1000, self.market_timezone
                ).isoformat()
                if timestamp
                else ""
            )
            record_id = str(row.get("announcementId", ""))
            adjunct = str(row.get("adjunctUrl", "")).lstrip("/")
            detail_url = (
                "https://www.cninfo.com.cn/new/disclosure/detail?"
                f"stockCode={issuer_code}&announcementId={record_id}"
                f"&orgId={org_id}"
            )
            announcements.append(
                Announcement(
                    source=self.name,
                    record_id=record_id,
                    issuer_code=str(row.get("secCode") or issuer_code),
                    issuer_name=str(row.get("secName") or issuer_name),
                    title=str(row.get("announcementTitle", "")),
                    published_at=published_at,
                    document_url=self.static_base + adjunct,
                    detail_url=detail_url,
                    source_metadata={
                        "org_id": org_id,
                        "announcement_time_ms": timestamp,
                        "publication_window": date_window,
                    },
                )
            )
        return announcements

    def download(self, announcement: Announcement) -> bytes:
        response = self.session.get(
            announcement.document_url,
            headers=self.headers,
            timeout=max(self.timeout, 180),
        )
        response.raise_for_status()
        return response.content
