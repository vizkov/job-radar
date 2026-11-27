import sys
import zipfile
import zlib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import render_pdf as rp  # noqa: E402


def cmap(*codes):
    body = "".join(f"<{i:04X}> <{c}>\n" for i, c in enumerate(codes, 1))
    return b"stream\n" + zlib.compress(f"{len(codes)} beginbfchar\n{body}endbfchar".encode()) + b"endstream"


def test_ligature_characters_are_found_in_the_character_map():
    assert rp.ligatures_in(cmap("0066", "FB01", "fb02")) == ["\ufb01", "\ufb02"]
    assert rp.ligatures_in(cmap("0066", "0069")) == []


def test_browser_metadata_is_blanked_without_moving_any_byte():
    pdf = rb"1 0 obj <</Title (Jane Doe) /Creator (Mozilla/5.0 \(Windows\) HeadlessChrome) /Producer (Skia/PDF m1)>>"
    out = rp.blank_browser_metadata(pdf)
    assert len(out) == len(pdf) and b"Jane Doe" in out and b"Chrome" not in out and b"Skia" not in out


def test_page_carries_the_name_as_its_title():
    assert "<title>Jane Doe</title>" in rp.page("", "x", "Jane Doe")


@pytest.mark.skipif(not rp.find_browser(), reason="no Chrome or Edge")
def test_a_real_render_has_no_ligatures_or_browser_metadata(tmp_path):
    out = tmp_path / "r.pdf"
    rp.print_pdf(rp.page("", "<p>workflow flaws, fixed efficiently, official offline files</p>" * 20, "Jane Doe"), out)
    pdf = out.read_bytes()
    assert rp.ligatures_in(pdf) == [] and b"HeadlessChrome" not in pdf and b"Skia/PDF" not in pdf


def test_a_word_file_carries_the_name_not_the_library(tmp_path):
    docx = pytest.importorskip("docx")
    import render_resume as rr
    out = tmp_path / "r.docx"
    rr.to_docx({"headline": "H", "sections": [], "skills": []}, {"name": "Jane Doe"}, out)
    p = docx.Document(out).core_properties
    assert (p.author, p.last_modified_by, p.title, p.comments) == ("Jane Doe", "Jane Doe", "Jane Doe", "") and p.created.year >= 2026
    with zipfile.ZipFile(out) as z:
        assert not any(b"python-docx" in z.read(n) for n in z.namelist())
