import json

from disclosure_pipeline.sources.cninfo import CninfoSource


class FakeResponse:
    def __init__(self, payload, status_code=200, content=b""):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload, ensure_ascii=False)
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, data, headers, timeout):
        self.calls.append(("POST", url, data))
        if "topSearch" in url:
            return FakeResponse(
                [{"code": "000001", "zwjc": "示例公司", "orgId": "org-demo"}]
            )
        return FakeResponse(
            {
                "announcements": [
                    {
                        "announcementId": "a1",
                        "announcementTitle": "示例公司2025年年度报告",
                        "announcementTime": 1774828800000,
                        "adjunctUrl": "finalpage/demo.pdf",
                        "secCode": "000001",
                        "secName": "示例公司",
                    }
                ],
                "totalRecordNum": 1,
            }
        )

    def get(self, url, headers, timeout):
        self.calls.append(("GET", url, None))
        return FakeResponse({}, content=b"%PDF-demo")


def test_cninfo_adapter_uses_normalized_announcement(monkeypatch):
    monkeypatch.setattr("disclosure_pipeline.sources.cninfo.time.sleep", lambda _: None)
    session = FakeSession()
    source = CninfoSource(session=session, pause_seconds=0)
    rows = source.list_annual_reports("000001", "示例公司", 2025)
    assert len(rows) == 1
    assert rows[0].record_id == "a1"
    assert rows[0].document_url.endswith("finalpage/demo.pdf")
    assert rows[0].source_metadata["org_id"] == "org-demo"
    assert any(
        call[2].get("seDate") == "2026-01-01~2026-12-31"
        for call in session.calls
        if call[0] == "POST" and "hisAnnouncement" in call[1]
    )
