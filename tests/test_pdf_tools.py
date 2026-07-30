import io

from pypdf import PdfWriter

from disclosure_pipeline.pdf_tools import validate_pdf_bytes


def make_pdf():
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(buffer)
    return buffer.getvalue()


def test_valid_pdf_reports_hash_size_and_pages():
    content = make_pdf()
    result = validate_pdf_bytes(content, min_bytes=1)
    assert result.valid
    assert result.page_count == 1
    assert result.size_bytes == len(content)
    assert len(result.sha256) == 64


def test_non_pdf_is_rejected():
    result = validate_pdf_bytes(b"<html>not a pdf</html>", min_bytes=1)
    assert not result.valid
    assert result.page_count is None
    assert "文件头不是PDF" in result.errors


def test_size_threshold_is_enforced():
    result = validate_pdf_bytes(make_pdf(), min_bytes=100_000)
    assert not result.valid
    assert any("文件大小低于设定下限" in error for error in result.errors)
