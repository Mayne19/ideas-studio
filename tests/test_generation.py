import pytest
from fastapi.testclient import TestClient
from tests.conftest import register_and_login


def _create_project(client: TestClient, headers: dict, name: str = "Test Blog") -> dict:
    resp = client.post("/projects", json={"name": name, "domain": "testblog.com", "language": "fr"}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _generate_article(client: TestClient, headers: dict, project_id: str, **overrides) -> dict:
    payload = {"preferred_title": "Test Article", "keyword": "test keyword", **overrides}
    resp = client.post(f"/projects/{project_id}/articles/generate", json=payload, headers=headers)
    return resp


def test_generate_article_returns_draft_ready(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    resp = _generate_article(client, headers, project["id"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft_ready"
    assert data["title"] == "Test Article"
    assert data["keyword"] == "test keyword"
    assert data["id"]
    assert data["word_count"] > 0


def test_generate_article_respects_preferred_title(client: TestClient):
    headers = register_and_login(client, email="title-test@test.com")
    project = _create_project(client, headers)
    resp = _generate_article(client, headers, project["id"], preferred_title="Mon super article")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Mon super article"


def test_generate_article_requires_auth(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    resp = client.post(f"/projects/{project['id']}/articles/generate", json={})
    assert resp.status_code == 401


def test_generate_article_viewer_cannot(client: TestClient):
    owner_headers = register_and_login(client, email="owner_gen@test.com")
    viewer_headers = register_and_login(client, email="viewer_gen@test.com", name="Viewer")
    project = _create_project(client, owner_headers)

    viewer_id = client.get("/auth/me", headers=viewer_headers).json()["id"]
    from tests.conftest import TestingSessionLocal
    from app.models.project_member import ProjectMember
    import uuid
    db = TestingSessionLocal()
    try:
        db.add(ProjectMember(id=str(uuid.uuid4()), project_id=project["id"], user_id=viewer_id, role="viewer", status="active"))
        db.commit()
    finally:
        db.close()

    resp = client.post(f"/projects/{project['id']}/articles/generate", json={}, headers=viewer_headers)
    assert resp.status_code == 403


def test_generate_article_returns_503_when_no_provider(client: TestClient):
    from app.core.config import settings

    headers = register_and_login(client, email="no_provider@test.com")
    project = _create_project(client, headers)

    old_env = settings.APP_ENV
    old_provider = settings.DEFAULT_LLM_PROVIDER
    old_url = settings.OLLAMA_URL
    try:
        settings.APP_ENV = "production"
        settings.DEFAULT_LLM_PROVIDER = "ollama"
        settings.OLLAMA_URL = "http://127.0.0.1:9"
        resp = client.post(f"/projects/{project['id']}/articles/generate", json={}, headers=headers)
        assert resp.status_code == 503
        assert "Aucun provider IA disponible" in resp.json()["detail"]
    finally:
        settings.APP_ENV = old_env
        settings.DEFAULT_LLM_PROVIDER = old_provider
        settings.OLLAMA_URL = old_url


def test_generate_article_mock_provider_produces_content(client: TestClient):
    headers = register_and_login(client, email="mock_gen@test.com")
    project = _create_project(client, headers)
    resp = _generate_article(client, headers, project["id"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft_ready"
    assert data["provider_name"] == "mock"


def test_auto_generate_ideas_returns_ideas(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    resp = client.post(f"/projects/{project['id']}/ideas/auto-generate", json={"count": 2}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["generated"] >= 1
    assert len(data["ideas"]) >= 1
    for idea in data["ideas"]:
        assert idea["id"]
        assert idea["title"]


def test_auto_generate_ideas_requires_auth(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    resp = client.post(f"/projects/{project['id']}/ideas/auto-generate", json={"count": 1})
    assert resp.status_code == 401


def test_auto_generate_viewer_cannot(client: TestClient):
    owner_headers = register_and_login(client, email="owner_auto@test.com")
    viewer_headers = register_and_login(client, email="viewer_auto@test.com", name="Viewer2")
    project = _create_project(client, owner_headers)

    viewer_id = client.get("/auth/me", headers=viewer_headers).json()["id"]
    from tests.conftest import TestingSessionLocal
    from app.models.project_member import ProjectMember
    import uuid
    db = TestingSessionLocal()
    try:
        db.add(ProjectMember(id=str(uuid.uuid4()), project_id=project["id"], user_id=viewer_id, role="viewer", status="active"))
        db.commit()
    finally:
        db.close()

    resp = client.post(f"/projects/{project['id']}/ideas/auto-generate", json={"count": 1}, headers=viewer_headers)
    assert resp.status_code == 403


def test_openrouter_provider_inherits_openai():
    from app.services.providers.openrouter_provider import OpenRouterLLMProvider
    from app.services.providers.openai_provider import OpenAILLMProvider

    provider = OpenRouterLLMProvider(api_key="test-key")
    assert isinstance(provider, OpenAILLMProvider)
    assert provider.provider_name == "openrouter"
    assert provider.model_name == "google/gemini-2.0-flash-001"
    assert provider.base_url == "https://openrouter.ai/api/v1"


def test_get_llm_provider_auto_falls_back_to_mock(monkeypatch):
    from app.core.config import settings
    from app.services.providers.llm_provider import get_llm_provider, MockLLMProvider

    old_provider = settings.DEFAULT_LLM_PROVIDER
    old_key = settings.OPENROUTER_API_KEY
    old_url = settings.OLLAMA_URL
    old_openai_key = settings.OPENAI_API_KEY
    try:
        settings.DEFAULT_LLM_PROVIDER = "auto"
        settings.OPENROUTER_API_KEY = ""
        settings.OLLAMA_URL = ""
        settings.OPENAI_API_KEY = ""
        provider = get_llm_provider()
        assert isinstance(provider, MockLLMProvider)
    finally:
        settings.DEFAULT_LLM_PROVIDER = old_provider
        settings.OPENROUTER_API_KEY = old_key
        settings.OLLAMA_URL = old_url
        settings.OPENAI_API_KEY = old_openai_key


def test_get_llm_provider_openrouter_returns_mock_when_not_configured(monkeypatch):
    from app.core.config import settings
    from app.services.providers.llm_provider import get_llm_provider, MockLLMProvider

    old_provider = settings.DEFAULT_LLM_PROVIDER
    old_key = settings.OPENROUTER_API_KEY
    try:
        settings.DEFAULT_LLM_PROVIDER = "openrouter"
        settings.OPENROUTER_API_KEY = ""
        provider = get_llm_provider()
        assert isinstance(provider, MockLLMProvider)
    finally:
        settings.DEFAULT_LLM_PROVIDER = old_provider
        settings.OPENROUTER_API_KEY = old_key
