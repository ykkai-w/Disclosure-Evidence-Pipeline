"""披露来源适配器接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from ..models import Announcement


class DisclosureSource(ABC):
    """不同披露网站可以实现的最小接口。"""

    name: str

    @abstractmethod
    def list_annual_reports(
        self,
        issuer_code: str,
        issuer_name: str,
        fiscal_year: int,
    ) -> Sequence[Announcement]:
        """返回可能相关的年度报告公告。"""

    @abstractmethod
    def download(self, announcement: Announcement) -> bytes:
        """下载公告对应的文档。"""
