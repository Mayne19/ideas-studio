"""Revalidation : secret en en-tête, jamais dans l'URL, jamais dans les
erreurs. Tests hors ligne (faux client HTTP, fausse session)."""
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from app.services import publication_revalidation_service as svc

SECRET = "s3cr3t-value-123"
URL = "https://www.example.com/api/ideas-studio/revalidate"


class FakeDb:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class RecordingClient:
    calls: list[dict] = []
    fail_with: Exception | None = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, **kwargs):
        RecordingClient.calls.append({"url": url, **kwargs})
        if RecordingClient.fail_with:
            raise RecordingClient.fail_with
        return SimpleNamespace(raise_for_status=lambda: None)


@pytest.fixture
def target(monkeypatch):
    t = SimpleNamespace(
        revalidate_url=URL, revalidate_secret="encrypted",
        last_sync_status=None, last_sync_error=None, last_synced_at=None,
    )
    monkeypatch.setattr(svc, "_primary_target", lambda db, project_id: t)
    monkeypatch.setattr(svc, "decrypt_secret", lambda value: SECRET)
    monkeypatch.setattr(svc.httpx, "Client", RecordingClient)
    monkeypatch.setattr("app.core.ssrf_guard.assert_safe_external_url", lambda url, **kw: None)
    RecordingClient.calls = []
    RecordingClient.fail_with = None
    return t


def _article():
    return SimpleNamespace(id="a1", slug="mon-article")


def test_secret_sent_in_header_and_body_not_query(target):
    result = svc.trigger_project_revalidation(FakeDb(), SimpleNamespace(id="p1"), article=_article())
    assert result["revalidated"] is True
    call = RecordingClient.calls[0]
    assert call["url"] == URL
    assert "params" not in call
    assert call["headers"]["X-Ideas-Studio-Secret"] == SECRET
    assert call["json"]["secret"] == SECRET
    assert call["json"]["slug"] == "mon-article"


def test_errors_are_redacted(target):
    request = httpx.Request("POST", f"{URL}?secret={SECRET}")
    RecordingClient.fail_with = httpx.HTTPStatusError(
        f"Client error '401 Unauthorized' for url '{URL}?secret={SECRET}'",
        request=request, response=httpx.Response(401, request=request),
    )
    result = svc.trigger_project_revalidation(FakeDb(), SimpleNamespace(id="p1"), article=_article())
    assert result["revalidated"] is False
    assert SECRET not in result["message"]
    assert SECRET not in target.last_sync_error
    assert "secret=***" in target.last_sync_error


def test_unsafe_revalidate_url_is_refused_before_sending(target, monkeypatch):
    def refuse(url, **kw):
        raise HTTPException(status_code=400, detail="URL pointe vers une adresse réseau interne")

    monkeypatch.setattr("app.core.ssrf_guard.assert_safe_external_url", refuse)
    result = svc.trigger_project_revalidation(FakeDb(), SimpleNamespace(id="p1"))
    assert result["revalidated"] is False
    assert RecordingClient.calls == []
    assert "refusée" in target.last_sync_error


def test_redact_secrets_masks_known_values_and_url_params():
    assert svc.redact_secrets("x secret=abc&token=def y", None) == "x secret=***&token=*** y"
    assert svc.redact_secrets(f"boom {SECRET}", SECRET) == "boom ***"
    assert svc.redact_secrets(None, SECRET) is None
