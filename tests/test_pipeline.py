import io
import json

from pypdf import PdfWriter

from disclosure_pipeline.models import Announcement
from disclosure_pipeline.pipeline import collect_annual_reports, read_issuers
from disclosure_pipeline.sources.base import DisclosureSource


def make_pdf():
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(buffer)
    return buffer.getvalue()


class FixtureSource(DisclosureSource):
    name = "fixture"

    def list_annual_reports(self, issuer_code, issuer_name, fiscal_year):
        return [
            Announcement(
                source=self.name,
                record_id="r1",
                issuer_code=issuer_code,
                issuer_name=issuer_name,
                title=f"{issuer_name}{fiscal_year}年年度报告",
                published_at="2026-03-30",
                document_url="https://example.test/r1.pdf",
                source_metadata={"fixture": True},
            )
        ]

    def download(self, announcement):
        return make_pdf()


def test_pipeline_writes_traceable_records_without_network(tmp_path):
    input_csv = tmp_path / "issuers.csv"
    input_csv.write_text("证券代码,证券简称\n1,示例公司\n", encoding="utf-8")
    output = tmp_path / "output"

    result = collect_annual_reports(
        source=FixtureSource(),
        input_csv=input_csv,
        fiscal_year=2025,
        output_dir=output,
        min_pdf_bytes=1,
    )

    assert result["summary"]["status_counts"] == {"downloaded": 1}
    record = json.loads(
        (output / "records.jsonl").read_text(encoding="utf-8").strip()
    )
    assert record["decision"]["selected_record_id"] == "r1"
    assert record["document"]["validation"]["page_count"] == 1
    assert (output / record["document"]["relative_path"]).exists()


def test_input_reader_preserves_leading_zeroes(tmp_path):
    source = tmp_path / "issuers.csv"
    source.write_text("code,name\n000001,示例公司\n", encoding="utf-8")
    assert read_issuers(source) == [{"code": "000001", "name": "示例公司"}]
