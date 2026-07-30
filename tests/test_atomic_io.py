import json

from disclosure_pipeline.atomic_io import atomic_write_json, atomic_write_text


def test_atomic_writes_replace_existing_file(tmp_path):
    destination = tmp_path / "nested" / "value.txt"
    atomic_write_text(destination, "old")
    atomic_write_text(destination, "new")
    assert destination.read_text(encoding="utf-8") == "new"
    assert list(destination.parent.glob("*.part")) == []


def test_atomic_json_keeps_unicode(tmp_path):
    destination = tmp_path / "result.json"
    atomic_write_json(destination, {"标题": "年度报告"})
    assert json.loads(destination.read_text(encoding="utf-8")) == {
        "标题": "年度报告"
    }
