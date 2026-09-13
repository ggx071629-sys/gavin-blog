from __future__ import annotations

import base64
import io
import json
import socket
import ssl
import subprocess
import sys
from types import SimpleNamespace

import pytest

from app.assistant_resume import download as module


def resolver(host, port, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))]


class Response:
    def __init__(self, body=b"%PDF-1.7 fixture", status=200, headers=None):
        self.status = status
        self.headers = {"Content-Type": "application/pdf", **(headers or {})}
        self.body = io.BytesIO(body)

    def getheader(self, name):
        return self.headers.get(name)

    def read(self, size):
        return self.body.read(size)


def connections(responses, calls):
    class Connection:
        def __init__(self, host, address, timeout):
            calls.append({"host": host, "address": address, "timeout": timeout})
            self.response = responses.pop(0)
            self.sock = None

        def request(self, method, target, headers):
            calls[-1].update(method=method, target=target, headers=headers)

        def getresponse(self):
            return self.response

        def close(self):
            calls[-1]["closed"] = True

    return Connection


def test_trusted_download_pins_each_redirect_and_preserves_tls_hostname(monkeypatch):
    calls = []
    result = module.fetch_pdf(
        "https://resume.example/start",
        ("resume.example",),
        force_refresh=True,
        resolver=resolver,
        connection_factory=connections(
            [
                Response(status=302, headers={"Location": "/resume.pdf"}),
                Response(),
            ],
            calls,
        ),
    )
    assert result.startswith(b"%PDF-")
    assert [call["target"] for call in calls] == ["/start", "/resume.pdf"]
    assert all(call["address"] == "8.8.8.8" and call["closed"] for call in calls)
    assert all(
        call["headers"]
        == {"Accept": "application/pdf", "Accept-Encoding": "identity", "Cache-Control": "no-cache"}
        for call in calls
    )
    recorded = {}

    class RawSocket:
        def settimeout(self, value):
            recorded["timeout"] = value

        def connect(self, address):
            recorded["address"] = address

        def close(self):
            pass

    def wrap(context, raw, *, server_hostname):
        assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        recorded["server_hostname"] = server_hostname
        return raw

    monkeypatch.setattr(module.socket, "socket", lambda *args: RawSocket())
    monkeypatch.setattr(module.ssl.SSLContext, "wrap_socket", wrap)
    conn = module.PinnedHTTPSConnection("resume.example", "8.8.8.8", 5)
    conn.connect()
    assert recorded["address"] == ("8.8.8.8", 443)
    assert recorded["server_hostname"] == "resume.example"
    conn.close()


def test_untrusted_targets_and_mixed_dns_are_rejected_without_connecting():
    for url in (
        "http://resume.example/a",
        "https://resume.example:444/a",
        "https://user:secret@resume.example/a",
        "https://resume.example/a#fragment",
        "https://8.8.8.8/a",
        "https://evil.example/a",
        "https://resume.example./a",
        "https://resume.example\\@evil.example/a",
        "https://resume.example/a\nheader",
    ):
        with pytest.raises(module.DownloadError, match="^blocked_host$"):
            module.checked_url(url, ("resume.example",))
    for address in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "ff02::1"):

        def mixed(host, port, address=address, **kwargs):
            return resolver(host, port) + [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))
            ]

        with pytest.raises(module.DownloadError, match="^blocked_host$"):
            module.fetch_pdf(
                "https://resume.example/a?secret=never-log",
                ("resume.example",),
                resolver=mixed,
                connection_factory=lambda *args: pytest.fail("connected"),
            )
    calls = []
    with pytest.raises(module.DownloadError, match="^blocked_host$"):
        module.fetch_pdf(
            "https://resume.example/a",
            ("resume.example",),
            resolver=resolver,
            connection_factory=connections(
                [
                    Response(status=302, headers={"Location": "https://evil.example/x"}),
                ],
                calls,
            ),
        )
    assert len(calls) == 1 and calls[0]["closed"]


def test_download_file_redirect_and_retry_limits():
    samples = [
        (Response(body=b"<html>not pdf</html>"), "not_pdf"),
        (Response(headers={"Content-Type": "text/html"}), "not_pdf"),
        (Response(headers={"Content-Encoding": "gzip"}), "not_pdf"),
        (Response(headers={"Content-Length": str(module.MAX_BYTES + 1)}), "too_large"),
        (Response(body=b"%PDF-" + b"x" * module.MAX_BYTES), "too_large"),
    ]
    for response, code in samples:
        with pytest.raises(module.DownloadError, match=f"^{code}$"):
            module.fetch_pdf(
                "https://resume.example/a",
                ("resume.example",),
                resolver=resolver,
                connection_factory=connections([response], []),
            )
    responses = [Response(status=302, headers={"Location": "/again"}) for _ in range(4)]
    calls = []
    with pytest.raises(module.DownloadError, match="^download_failed$"):
        module.fetch_pdf(
            "https://resume.example/a",
            ("resume.example",),
            resolver=resolver,
            connection_factory=connections(responses, calls),
        )
    assert len(calls) == 4
    with pytest.raises(module.DownloadError) as error:
        module.fetch_pdf(
            "https://resume.example/a",
            ("resume.example",),
            resolver=resolver,
            connection_factory=connections(
                [
                    Response(
                        status=429,
                        headers={
                            "Retry-After": "120",
                        },
                    )
                ],
                [],
            ),
        )
    assert error.value.transient and error.value.retry_after == 120


def test_download_child_environment_hash_and_real_deadline(monkeypatch):
    monkeypatch.setenv("GAVIN_CHAT_API_KEY", "must-not-inherit")
    monkeypatch.setenv("HTTPS_PROXY", "must-not-inherit")
    real_run = subprocess.run
    body = b"%PDF-1.7 isolated"

    def completed(args, **kwargs):
        assert "GAVIN_CHAT_API_KEY" not in kwargs["env"]
        assert "HTTPS_PROXY" not in kwargs["env"]
        assert kwargs["stderr"] == subprocess.DEVNULL
        assert "secret" not in " ".join(args)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "body": base64.b64encode(body).decode(),
                }
            ).encode(),
        )

    monkeypatch.setattr(module.subprocess, "run", completed)
    result = module.download_pdf("https://resume.example/a?secret=x", ("resume.example",))
    assert result.body == body
    assert result.sha256 == module.hashlib.sha256(body).hexdigest()

    def sleeping_worker(args, **kwargs):
        return real_run([sys.executable, "-c", "import time; time.sleep(5)"], **kwargs)

    monkeypatch.setattr(module, "TOTAL_SECONDS", 0.05)
    monkeypatch.setattr(module.subprocess, "run", sleeping_worker)
    with pytest.raises(module.DownloadError, match="^download_timeout$"):
        module.download_pdf("https://resume.example/a", ("resume.example",))
