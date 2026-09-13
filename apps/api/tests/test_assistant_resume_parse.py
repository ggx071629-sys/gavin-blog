from __future__ import annotations

import io
import subprocess
import sys

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from app.assistant_resume import parse as module
from app.assistant_resume.download import worker_environment


def pdf_fixture(texts: list[str | None], *, password: str | None = None) -> bytes:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    for value in texts:
        page = writer.add_blank_page(width=612, height=792)
        stream = DecodedStreamObject()
        if value is None:
            image = DecodedStreamObject()
            image.set_data(b"\x00")
            image.update(
                {
                    NameObject("/Type"): NameObject("/XObject"),
                    NameObject("/Subtype"): NameObject("/Image"),
                    NameObject("/Width"): NumberObject(1),
                    NameObject("/Height"): NumberObject(1),
                    NameObject("/ColorSpace"): NameObject("/DeviceGray"),
                    NameObject("/BitsPerComponent"): NumberObject(8),
                }
            )
            page[NameObject("/Resources")] = DictionaryObject(
                {
                    NameObject("/XObject"): DictionaryObject(
                        {NameObject("/Im0"): writer._add_object(image)}
                    ),
                }
            )
            stream.set_data(b"q 100 0 0 100 0 0 cm /Im0 Do Q")
        else:
            page[NameObject("/Resources")] = DictionaryObject(
                {
                    NameObject("/Font"): DictionaryObject(
                        {NameObject("/F1"): writer._add_object(font)}
                    ),
                }
            )
            escaped = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream.set_data(f"BT /F1 12 Tf 20 700 Td ({escaped}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    if password is not None:
        writer.encrypt(password)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_pdf_text_pages_and_unsupported_files():
    parsed = module.parse_pdf(pdf_fixture(["Public engineering experience", "Backend projects"]))
    assert parsed.pages == ("Public engineering experience", "Backend projects")
    assert "第 1 页" in parsed.body and "第 2 页" in parsed.body
    assert parsed.parser_version == "pypdf-6.18.0-text-v1"
    for body, code in (
        (pdf_fixture([None]), "text_unavailable"),
        (pdf_fixture(["Text page", None]), "text_unavailable"),
        (pdf_fixture([""], password=""), "encrypted_pdf"),
        (pdf_fixture([""], password="password"), "encrypted_pdf"),
        (pdf_fixture([""]), "text_unavailable"),
        (pdf_fixture(["page"] * 21), "too_many_pages"),
        (pdf_fixture(["x" * (module.MAX_CHARS + 1)]), "text_too_large"),
        (b"%PDF-corrupt", "parse_failed"),
    ):
        with pytest.raises(module.ParseError, match=f"^{code}$"):
            module.parse_pdf(body)


def test_parser_memory_and_io_are_enforced_in_real_process(tmp_path):
    secret = tmp_path / "private.txt"
    secret.write_text("must not be read", encoding="utf-8")
    code = """
import sys
from app.assistant_resume.isolation import limit_memory, restrict_io, MEMORY_BYTES
assert limit_memory(), 'resource limits unavailable'
try:
    value = bytearray(MEMORY_BYTES * 2)
except MemoryError:
    pass
else:
    raise AssertionError('memory limit was not enforced')
import socket, sqlite3
restrict_io()
blocked = 0
actions = [
    lambda: socket.socket(),
    lambda: sqlite3.connect(':memory:'),
    lambda: open(sys.argv[1]),
]
for action in actions:
    try:
        action()
    except PermissionError:
        blocked += 1
assert blocked == 3
print('memory-and-io-enforced')
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(secret)],
        capture_output=True,
        env=worker_environment(),
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert result.stdout.strip() == b"memory-and-io-enforced"


def test_parser_deadline_and_unavailable_boundary(monkeypatch, capsys):
    real_run = subprocess.run

    def sleeping_worker(args, **kwargs):
        return real_run([sys.executable, "-c", "import time; time.sleep(5)"], **kwargs)

    monkeypatch.setattr(module.subprocess, "run", sleeping_worker)
    monkeypatch.setattr(module, "PARSE_SECONDS", 0.05)
    with pytest.raises(module.ParseError, match="^parse_timeout$"):
        module.parse_pdf(b"%PDF-1.7 fixture")
    monkeypatch.setattr(module, "limit_memory", lambda: False)
    module.main()
    assert '"parser_unavailable"' in capsys.readouterr().out
