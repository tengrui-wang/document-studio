import json
from threading import Event
import httpx
import pytest

from document_studio.api import APIClient, APIError
from document_studio.common import Cancelled
from document_studio.storage import Credentials
from document_studio.word_tools import word_to_pdf


def test_claude_protocol_usage_and_model_pagination():
    requests, usage = [], []
    def handler(request):
        requests.append(request)
        assert request.headers["x-api-key"] == "test-only"
        assert request.headers["anthropic-version"] == "2023-06-01"
        if request.method == "GET":
            if request.url.query:
                return httpx.Response(200, json={"data": [{"id": "b"}], "has_more": False})
            return httpx.Response(200, json={"data": [{"id": "a"}], "has_more": True, "last_id": "a"})
        body = json.loads(request.content)
        assert body["system"] == "system"
        assert body["max_tokens"] > 0
        return httpx.Response(200, json={"content": [{"type": "text", "text": "OK"}], "usage": {"input_tokens": 2, "output_tokens": 1}, "stop_reason": "end_turn"})
    client = APIClient({"provider": "anthropic", "base_url": "https://example.com/v1"}, "test-only",
                       transport=httpx.MockTransport(handler), usage=lambda a, b: usage.append((a, b)))
    assert client.models() == ["a", "b"]
    assert client.complete("a", "system", "test") == "OK"
    assert usage == [(2, 1)]
    client.close()


def test_rate_limit_retry_and_cancel():
    attempts = []
    def handler(request):
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, json={"data": [{"id": "m"}]})
    event = Event()
    client = APIClient({"provider": "openai", "base_url": "https://example.com/v1"}, "test-only",
                       transport=httpx.MockTransport(handler), cancel=event)
    client.pause = lambda seconds: None
    assert client.models() == ["m"]
    assert len(attempts) == 3
    event.set()
    with pytest.raises(Cancelled):
        client.models()
    client.close()


def test_malformed_usage_never_exposes_provider_text():
    client = APIClient({"provider": "openai", "base_url": "https://example.com/v1"}, "secret-only",
                       transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"usage": {"prompt_tokens": "secret-only"}, "choices": []})))
    with pytest.raises(APIError) as error:
        client.complete("m", "system", "test")
    assert "secret-only" not in str(error.value)
    client.close()


def test_credential_backend_no_plaintext_fallback(monkeypatch):
    from keyring.backends.Windows import WinVaultKeyring
    assert isinstance(Credentials.backend(), WinVaultKeyring)
    def fail(*args):
        raise RuntimeError("secret-only")
    monkeypatch.setattr(WinVaultKeyring, "set_password", fail)
    with pytest.raises(RuntimeError) as error:
        Credentials().set("test", "secret-only")
    assert "secret-only" not in str(error.value)


def test_word_to_pdf_missing_engine(tmp_path, monkeypatch):
    from docx import Document
    Document().save(tmp_path / "test.docx")
    monkeypatch.setattr("document_studio.word_tools.locate_soffice", lambda configured: None)
    with pytest.raises(ValueError, match="Word 或 LibreOffice"):
        word_to_pdf(tmp_path / "test.docx", tmp_path / "test.pdf", {"backend": "libreoffice"}, lambda *a: None, Event())
