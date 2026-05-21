import pytest
from fastapi.testclient import TestClient
from tests.conftest import register_and_login, TestingSessionLocal

_REQUIRES_OPENROUTER = pytest.mark.skipif(
    "not __import__('os').environ.get('OPENROUTER_API_KEY') and not __import__('app.core.config', fromlist=['settings']).settings.OPENROUTER_API_KEY",
    reason="OPENROUTER_API_KEY required for real AI generation tests",
)


def _create_project(client: TestClient, headers: dict, name: str = "Test Blog") -> dict:
    resp = client.post("/projects", json={"name": name, "domain": "testblog.com", "language": "fr"}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


# ── Providers (class unit tests, not generation) ─────────────────────────────

def test_mock_llm_provider_generate_text():
    from app.services.providers.llm_provider import MockLLMProvider
    provider = MockLLMProvider()
    result = provider.generate_text("test prompt")
    assert "[Mock]" in result
    assert provider.is_mock is True
    assert provider.is_available() is True


def test_mock_llm_provider_generate_json():
    from app.services.providers.llm_provider import MockLLMProvider
    provider = MockLLMProvider()
    result = provider.generate_json("test prompt")
    assert isinstance(result, dict)


def test_mock_search_provider():
    from app.services.providers.search_provider import MockSearchProvider
    provider = MockSearchProvider()
    results = provider.search("SEO tips", limit=2)
    assert len(results) <= 2
    assert provider.is_mock is True
    assert provider.is_available() is True
    for r in results:
        assert r.title
        assert r.url
        assert r.snippet


def test_get_llm_provider_raises_when_no_real_provider():
    from app.core.config import settings
    from app.services.providers.llm_provider import get_llm_provider, ProviderUnavailableError

    old_provider = settings.DEFAULT_LLM_PROVIDER
    old_key = settings.OPENROUTER_API_KEY
    old_url = settings.OLLAMA_URL
    old_openai_key = settings.OPENAI_API_KEY
    try:
        settings.DEFAULT_LLM_PROVIDER = "auto"
        settings.OPENROUTER_API_KEY = ""
        settings.OLLAMA_URL = ""
        settings.OPENAI_API_KEY = ""
        with pytest.raises(ProviderUnavailableError, match="Aucun provider IA réel disponible"):
            get_llm_provider()
    finally:
        settings.DEFAULT_LLM_PROVIDER = old_provider
        settings.OPENROUTER_API_KEY = old_key
        settings.OLLAMA_URL = old_url
        settings.OPENAI_API_KEY = old_openai_key


def test_get_llm_provider_raises_in_production_when_ollama_unavailable():
    from app.core.config import settings
    from app.services.providers.llm_provider import get_llm_provider, ProviderUnavailableError

    old_env = settings.APP_ENV
    old_provider = settings.DEFAULT_LLM_PROVIDER
    old_url = settings.OLLAMA_URL
    try:
        settings.APP_ENV = "production"
        settings.DEFAULT_LLM_PROVIDER = "ollama"
        settings.OLLAMA_URL = "http://127.0.0.1:9"
        with pytest.raises(ProviderUnavailableError):
            get_llm_provider()
    finally:
        settings.APP_ENV = old_env
        settings.DEFAULT_LLM_PROVIDER = old_provider
        settings.OLLAMA_URL = old_url


def test_get_llm_provider_returns_openai_when_configured(monkeypatch):
    from app.core.config import settings
    from app.services.providers.llm_provider import get_llm_provider
    from app.services.providers.openai_provider import OpenAILLMProvider

    old_provider = settings.DEFAULT_LLM_PROVIDER
    old_key = settings.OPENAI_API_KEY
    old_model = settings.OPENAI_MODEL
    old_orkey = settings.OPENROUTER_API_KEY
    try:
        settings.DEFAULT_LLM_PROVIDER = "openai"
        settings.OPENAI_API_KEY = "test-key"
        settings.OPENAI_MODEL = "gpt-test"
        settings.OPENROUTER_API_KEY = ""
        monkeypatch.setattr(OpenAILLMProvider, "is_available", lambda self: True)
        provider = get_llm_provider()
        assert isinstance(provider, OpenAILLMProvider)
        assert provider.model_name == "gpt-test"
    finally:
        settings.DEFAULT_LLM_PROVIDER = old_provider
        settings.OPENAI_API_KEY = old_key
        settings.OPENAI_MODEL = old_model
        settings.OPENROUTER_API_KEY = old_orkey


def test_get_search_provider_returns_mock_by_default():
    from app.services.providers.search_provider import get_search_provider, MockSearchProvider
    provider = get_search_provider()
    assert isinstance(provider, MockSearchProvider)


# ── Idea Engine (real AI) ─────────────────────────────────────────────────────

@_REQUIRES_OPENROUTER
def test_generate_idea_creates_article_with_idea_proposed(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=headers)
    if resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "idea_proposed"
    assert data["keyword"]
    assert data["id"]


def test_generate_idea_requires_auth(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    resp = client.post(f"/projects/{project['id']}/ideas/generate", json={})
    assert resp.status_code == 401


@_REQUIRES_OPENROUTER
def test_generate_idea_with_context_hint(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    resp = client.post(
        f"/projects/{project['id']}/ideas/generate",
        json={"context_hint": "optimisation images web"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "idea_proposed"


@_REQUIRES_OPENROUTER
def test_generate_idea_respects_preferred_title(client: TestClient):
    headers = register_and_login(client, email="preferred_title@test.com")
    project = _create_project(client, headers)
    resp = client.post(
        f"/projects/{project['id']}/ideas/generate",
        json={"preferred_title": "Mon titre prioritaire"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Mon titre prioritaire"


def test_generate_idea_returns_503_when_provider_unavailable_in_production(client: TestClient):
    from app.core.config import settings

    headers = register_and_login(client, email="llm_down@test.com")
    project = _create_project(client, headers)

    old_env = settings.APP_ENV
    old_provider = settings.DEFAULT_LLM_PROVIDER
    old_url = settings.OLLAMA_URL
    try:
        settings.APP_ENV = "production"
        settings.DEFAULT_LLM_PROVIDER = "ollama"
        settings.OLLAMA_URL = "http://127.0.0.1:9"
        resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=headers)
        assert resp.status_code == 503
        assert "Aucun provider IA réel disponible" in resp.json()["detail"]
    finally:
        settings.APP_ENV = old_env
        settings.DEFAULT_LLM_PROVIDER = old_provider
        settings.OLLAMA_URL = old_url


@_REQUIRES_OPENROUTER
def test_generate_idea_deduplication(client: TestClient):
    """Generating the same keyword twice should return 409 on second attempt."""
    headers = register_and_login(client)
    project = _create_project(client, headers)

    resp1 = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=headers)
    assert resp1.status_code == 200
    keyword = resp1.json()["keyword"]

    from tests.conftest import TestingSessionLocal
    from app.services.idea_engine import _keyword_already_active
    db = TestingSessionLocal()
    try:
        is_active = _keyword_already_active(db, project["id"], keyword)
        assert is_active is True
    finally:
        db.close()


def test_generate_idea_viewer_cannot_generate(client: TestClient):
    owner_headers = register_and_login(client, email="owner@test.com")
    viewer_headers = register_and_login(client, email="viewer@test.com", name="Viewer")
    project = _create_project(client, owner_headers)

    viewer_id = client.get("/auth/me", headers=viewer_headers).json()["id"]

    from tests.conftest import TestingSessionLocal
    from app.models.project_member import ProjectMember
    import uuid
    db = TestingSessionLocal()
    try:
        member = ProjectMember(
            id=str(uuid.uuid4()),
            project_id=project["id"],
            user_id=viewer_id,
            role="viewer",
            status="active",
        )
        db.add(member)
        db.commit()
    finally:
        db.close()

    resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=viewer_headers)
    assert resp.status_code == 403


def test_non_member_cannot_generate_idea(client: TestClient):
    owner_headers = register_and_login(client, email="owner@test.com")
    other_headers = register_and_login(client, email="other@test.com", name="Other")
    project = _create_project(client, owner_headers)

    resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=other_headers)
    assert resp.status_code == 403


# ── Writing Engine (real AI) ──────────────────────────────────────────────────

@_REQUIRES_OPENROUTER
def test_start_writing_produces_draft_ready(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=headers)
    if resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert resp.status_code == 200
    idea_id = resp.json()["id"]

    resp = client.post(f"/articles/{idea_id}/start-writing", headers=headers)
    if resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft_ready"
    assert data["provider_name"] == "openrouter"


@_REQUIRES_OPENROUTER
def test_start_writing_saves_seo_review_json(client: TestClient):
    headers = register_and_login(client, email="seo_review_generation@test.com")
    project = _create_project(client, headers)
    resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=headers)
    if resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert resp.status_code == 200
    idea_id = resp.json()["id"]

    resp = client.post(f"/articles/{idea_id}/start-writing", headers=headers)
    if resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert resp.status_code == 200

    editor = client.get(f"/articles/{idea_id}/editor", headers=headers)
    if editor.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert editor.status_code == 200
    seo_review = editor.json()["seo_review_json"]
    assert seo_review is not None
    assert "score_global" in seo_review
    assert isinstance(seo_review["issues"], list)


@_REQUIRES_OPENROUTER
def test_start_writing_keeps_article_when_seo_review_runtime_fails(client: TestClient):
    from app.services import writing_engine

    headers = register_and_login(client, email="seo_review_runtime_generation@test.com")
    project = _create_project(client, headers)
    resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=headers)
    assert resp.status_code == 200
    idea_id = resp.json()["id"]

    import app.routers.ideas as ideas_router
    original_llm = ideas_router.get_llm_provider

    llm = original_llm()
    original_seo = writing_engine.run_and_store_seo_review
    writing_engine.run_and_store_seo_review = lambda _article: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        resp = client.post(f"/articles/{idea_id}/start-writing", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "draft_ready"

        editor = client.get(f"/articles/{idea_id}/editor", headers=headers)
        assert editor.status_code == 200
        seo_review = editor.json()["seo_review_json"]
        assert seo_review is not None
        assert "seo_expert_runtime" in seo_review["failed_checks"]
    finally:
        writing_engine.run_and_store_seo_review = original_seo


def test_markdown_to_html_supports_tables_and_blockquotes():
    from app.core.markdown import markdown_to_html

    html = markdown_to_html(
        "# Titre\n\n> Citation utile\n\n| Col A | Col B |\n| --- | --- |\n| 1 | 2 |\n"
    )
    assert "<blockquote>" in html
    assert "<table>" in html
    assert "<h1>Titre</h1>" in html


def test_start_writing_invalid_status(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    article_resp = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Published Article", "slug": "published-article"},
        headers=headers,
    )
    article_id = article_resp.json()["id"]
    client.post(f"/articles/{article_id}/publish", headers=headers)

    resp = client.post(f"/articles/{article_id}/start-writing", headers=headers)
    assert resp.status_code == 400


@_REQUIRES_OPENROUTER
def test_start_writing_viewer_cannot(client: TestClient):
    owner_headers = register_and_login(client, email="owner2@test.com")
    viewer_headers = register_and_login(client, email="viewer2@test.com", name="Viewer2")
    project = _create_project(client, owner_headers)
    idea_resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=owner_headers)
    if idea_resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert idea_resp.status_code == 200
    idea_id = idea_resp.json()["id"]

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

    resp = client.post(f"/articles/{idea_id}/start-writing", headers=viewer_headers)
    assert resp.status_code == 403


# ── Reject ─────────────────────────────────────────────────────────────────────

@_REQUIRES_OPENROUTER
def test_reject_idea(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    idea_resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=headers)
    if idea_resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert idea_resp.status_code == 200
    idea_id = idea_resp.json()["id"]

    resp = client.post(
        f"/articles/{idea_id}/reject",
        json={"rejection_reason": "off_topic", "rejection_note": "Not relevant"},
        headers=headers,
    )
    if resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_reject_non_idea_fails(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    article_resp = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "A Draft", "slug": "a-draft", "status": "draft"},
        headers=headers,
    )
    article_id = article_resp.json()["id"]
    resp = client.post(f"/articles/{article_id}/reject", json={}, headers=headers)
    assert resp.status_code == 400


# ── Priority ───────────────────────────────────────────────────────────────────

@_REQUIRES_OPENROUTER
def test_set_priority_sets_idea_priority_status(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    idea_resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=headers)
    if idea_resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert idea_resp.status_code == 200
    idea_id = idea_resp.json()["id"]

    resp = client.post(f"/articles/{idea_id}/priority", json={"priority": 5}, headers=headers)
    if resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] == 5
    assert data["status"] == "idea_priority"


@_REQUIRES_OPENROUTER
def test_priority_viewer_cannot(client: TestClient):
    owner_headers = register_and_login(client, email="owner3@test.com")
    viewer_headers = register_and_login(client, email="viewer3@test.com", name="Viewer3")
    project = _create_project(client, owner_headers)
    idea_resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=owner_headers)
    if idea_resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert idea_resp.status_code == 200
    idea_id = idea_resp.json()["id"]

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

    resp = client.post(f"/articles/{idea_id}/priority", json={"priority": 1}, headers=viewer_headers)
    assert resp.status_code == 403


# ── Manual Draft ───────────────────────────────────────────────────────────────

@_REQUIRES_OPENROUTER
def test_manual_draft_converts_idea_to_draft_ready(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    idea_resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=headers)
    if idea_resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert idea_resp.status_code == 200
    idea_id = idea_resp.json()["id"]

    resp = client.post(f"/articles/{idea_id}/manual-draft", headers=headers)
    if resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft_ready"


def test_manual_draft_non_idea_fails(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    article_resp = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "A Draft", "slug": "a-manual-draft"},
        headers=headers,
    )
    article_id = article_resp.json()["id"]
    resp = client.post(f"/articles/{article_id}/manual-draft", headers=headers)
    assert resp.status_code == 400


# ── Rerun ──────────────────────────────────────────────────────────────────────

@_REQUIRES_OPENROUTER
def test_rerun_writing_produces_draft_ready(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    idea_resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=headers)
    if idea_resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert idea_resp.status_code == 200
    idea_id = idea_resp.json()["id"]

    client.post(f"/articles/{idea_id}/start-writing", headers=headers)
    resp = client.post(f"/articles/{idea_id}/rerun", headers=headers)
    if resp.status_code == 503:
        pytest.skip("LLM provider rate limited, skipping")

    assert resp.status_code == 200
    assert resp.json()["status"] == "draft_ready"


# ── Launch ─────────────────────────────────────────────────────────────────────

@_REQUIRES_OPENROUTER
def test_launch_idea_only_mode(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    resp = client.post(f"/projects/{project['id']}/launch", json={"mode": "idea_only"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == project["id"]
    assert data["mode"] == "idea_only"
    assert data["dry_run"] is False
    assert data["ideas_generated"] >= 1

    for article_id in data["article_ids"]:
        article_resp = client.get(f"/articles/{article_id}", headers=headers)
        assert article_resp.json()["status"] == "idea_proposed"


@_REQUIRES_OPENROUTER
def test_launch_full_article_mode(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    resp = client.post(f"/projects/{project['id']}/launch", json={"mode": "full_article"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "full_article"
    assert data["ideas_generated"] >= 1

    for article_id in data["article_ids"]:
        article_resp = client.get(f"/articles/{article_id}", headers=headers)
        assert article_resp.json()["status"] == "draft_ready"


@_REQUIRES_OPENROUTER
def test_launch_full_article_transmits_fields_and_generates_metadata(client: TestClient):
    from app.models.category import Category
    import uuid

    headers = register_and_login(client, email="launch_full_fields@test.com")
    project = _create_project(client, headers)

    db = TestingSessionLocal()
    try:
        category = Category(
            id=str(uuid.uuid4()),
            project_id=project["id"],
            name="SEO",
            slug="seo",
            color="#ff6600",
            priority=0,
        )
        db.add(category)
        db.commit()
        category_id = category.id
    finally:
        db.close()

    resp = client.post(
        f"/projects/{project['id']}/launch",
        json={
            "mode": "full_article",
            "preferred_title": "Titre utilisateur prioritaire",
            "keyword": "landing page mobile",
            "category_id": category_id,
            "audience": "Founders mobile",
            "angle": "Guide pratique",
            "search_intent": "commercial",
            "include_faq": True,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider_name"] == "openrouter"
    assert len(data["article_ids"]) == 1

    article_resp = client.get(f"/articles/{data['article_ids'][0]}", headers=headers)
    article = article_resp.json()
    assert article["title"] == "Titre utilisateur prioritaire"
    assert article["category_id"] == category_id
    assert article["status"] == "draft_ready"
    assert article["keyword"] == "landing page mobile"
    assert article["reading_time_minutes"] >= 1
    assert article["slug"] == "titre-utilisateur-prioritaire"
    assert article["content"] is not None
    assert len(article["content"]) > 100

    preview = client.get(f"/articles/{article['id']}/preview", headers=headers).json()
    assert preview["faq_json"] is not None


def test_launch_dry_run(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    resp = client.post(f"/projects/{project['id']}/launch", json={"dry_run": True}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["ideas_generated"] == 0


# ── Scheduler ─────────────────────────────────────────────────────────────────

@_REQUIRES_OPENROUTER
def test_generate_daily_ideas_respects_ideas_per_day(client: TestClient):
    headers = register_and_login(client)
    _create_project(client, headers)

    from app.services.scheduler import generate_daily_ideas
    from app.core.config import settings

    db = TestingSessionLocal()
    try:
        result = generate_daily_ideas(db)
        assert result["generated"] <= result["projects"] * settings.IDEAS_PER_DAY
        assert "skipped" in result
    finally:
        db.close()
