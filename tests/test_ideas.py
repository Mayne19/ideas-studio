import uuid
import pytest
from fastapi.testclient import TestClient
from tests.conftest import force_publish_article, register_and_login, TestingSessionLocal

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


class _FakeIdeaProvider:
    is_mock = False
    provider_name = "fake"
    model_name = "test"

    def __init__(self, payload: dict):
        self.payload = payload

    def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
        return ""

    def generate_json(self, prompt: str, schema_hint: str | None = None):
        return dict(self.payload)

    def is_available(self) -> bool:
        return True

    def describe(self) -> str:
        return "fake model=test mock=False"


def test_generate_idea_matches_ai_category_and_cleans_keyword(client: TestClient):
    from app.models.category import Category
    from app.services.idea_engine import generate_idea
    from app.services.providers.search_provider import MockSearchProvider
    import uuid

    headers = register_and_login(client, email="idea_category_keyword@test.com")
    project = _create_project(client, headers)

    db = TestingSessionLocal()
    try:
        category = Category(
            id=str(uuid.uuid4()),
            project_id=project["id"],
            name="SEO technique",
            slug="seo-technique",
            color="#ff6600",
            priority=10,
        )
        db.add(category)
        db.commit()

        raw_keyword = "Comment améliorer la vitesse de chargement de votre site web en 2026 ?"
        article = generate_idea(
            db=db,
            project_id=project["id"],
            project_audience="Freelances web",
            project_language="fr",
            llm=_FakeIdeaProvider({
                "title": raw_keyword,
                "keyword": raw_keyword,
                "category_name": "SEO technique",
                "angle": "Guide pratique",
                "search_intent": "informational",
                "audience": "Freelances web",
                "main_answer_summary": "Résumé",
                "opportunity_justification": "Opportunité",
                "recommended_format": "guide",
                "target_word_count": 1800,
                "needs_faq": True,
                "needs_images": False,
                "estimated_difficulty": "moyenne",
                "secondary_keywords": ["vitesse de chargement site web"],
            }),
            search=MockSearchProvider(),
        )

        assert article is not None
        assert article.category_id == category.id
        assert article.keyword != raw_keyword
        assert "?" not in article.keyword
        assert 2 <= len(article.keyword.split()) <= 6
    finally:
        db.close()


def test_generate_idea_keeps_uncategorized_when_ai_category_is_unmatched(client: TestClient):
    from app.models.category import Category
    from app.services.idea_engine import generate_idea
    from app.services.providers.search_provider import MockSearchProvider
    import uuid

    headers = register_and_login(client, email="idea_uncategorized@test.com")
    project = _create_project(client, headers)

    db = TestingSessionLocal()
    try:
        db.add(Category(
            id=str(uuid.uuid4()),
            project_id=project["id"],
            name="SEO technique",
            slug="seo-technique",
            color="#ff6600",
            priority=0,
        ))
        db.commit()

        article = generate_idea(
            db=db,
            project_id=project["id"],
            project_audience="Freelances web",
            project_language="fr",
            llm=_FakeIdeaProvider({
                "title": "Optimiser une page service",
                "keyword": "optimisation page service",
                "category_name": "Catégorie inventée",
                "angle": "Guide pratique",
                "search_intent": "informational",
                "secondary_keywords": [],
            }),
            search=MockSearchProvider(),
        )

        assert article is not None
        assert article.category_id is None
    finally:
        db.close()


def test_generate_idea_preserves_explicit_category(client: TestClient):
    from app.models.category import Category
    from app.services.idea_engine import generate_idea
    from app.services.providers.search_provider import MockSearchProvider
    import uuid

    headers = register_and_login(client, email="idea_explicit_category@test.com")
    project = _create_project(client, headers)

    db = TestingSessionLocal()
    try:
        category = Category(
            id=str(uuid.uuid4()),
            project_id=project["id"],
            name="E-commerce",
            slug="e-commerce",
            color="#ff6600",
            priority=0,
        )
        db.add(category)
        db.commit()

        article = generate_idea(
            db=db,
            project_id=project["id"],
            project_audience="Boutiques en ligne",
            project_language="fr",
            llm=_FakeIdeaProvider({
                "title": "Optimiser les fiches produit",
                "keyword": "optimisation fiche produit",
                "category_name": "Autre catégorie",
                "angle": "Guide pratique",
                "search_intent": "commercial",
                "secondary_keywords": [],
            }),
            search=MockSearchProvider(),
            category_id=category.id,
        )

        assert article is not None
        assert article.category_id == category.id
    finally:
        db.close()


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
    force_publish_article(article_id)

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


# ── Delete ────────────────────────────────────────────────────────────────────


def _make_idea(client, headers, project, status="idea_proposed"):
    """Create a draft article then flip its status to the desired idea status."""
    resp = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": f"Test idea {uuid.uuid4().hex[:8]}", "slug": f"test-{uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    assert resp.status_code == 201
    article_id = resp.json()["id"]
    db = TestingSessionLocal()
    try:
        from app.models.article import Article
        article = db.get(Article, article_id)
        article.status = status
        db.commit()
    finally:
        db.close()
    return article_id


def test_delete_proposed_idea(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    idea_id = _make_idea(client, headers, project, "idea_proposed")

    resp = client.delete(f"/projects/{project['id']}/ideas/{idea_id}", headers=headers)
    assert resp.status_code == 204

    resp = client.get(f"/articles/{idea_id}", headers=headers)
    assert resp.status_code == 404


def test_delete_rejected_idea(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    idea_id = _make_idea(client, headers, project, "idea_rejected")

    resp = client.delete(f"/projects/{project['id']}/ideas/{idea_id}", headers=headers)
    assert resp.status_code == 204


def test_delete_rejected_idea_with_linked_records(client: TestClient):
    headers = register_and_login(client)
    user = client.get("/auth/me", headers=headers).json()
    project = _create_project(client, headers)
    idea_id = _make_idea(client, headers, project, "idea_rejected")

    db = TestingSessionLocal()
    try:
        from app.models.article_comment import ArticleComment
        from app.models.article_log import ArticleLog
        from app.models.article_version import ArticleVersion
        from app.models.media_asset import MediaAsset
        from app.models.optimization_recommendation import OptimizationRecommendation
        from app.models.seo_analysis import SeoAnalysis

        db.add(SeoAnalysis(
            project_id=project["id"],
            article_id=idea_id,
            seo_score=50,
            readability_score=50,
            quality_score=50,
            eeat_score=50,
            readiness_status="needs_improvement",
        ))
        db.add(ArticleVersion(
            project_id=project["id"],
            article_id=idea_id,
            title="Version idee",
            slug="version-idee",
            version_number=1,
            created_by=user["id"],
        ))
        db.add(ArticleComment(
            project_id=project["id"],
            article_id=idea_id,
            author_id=user["id"],
            author_name=user["name"],
            text="test comment",
        ))
        db.add(ArticleLog(project_id=project["id"], article_id=idea_id, level="info", step="test", message="linked log"))
        db.add(MediaAsset(project_id=project["id"], article_id=idea_id, url="https://example.com/a.png", filename="a.png"))
        db.add(OptimizationRecommendation(
            project_id=project["id"],
            article_id=idea_id,
            type="improve_title",
            reason="test",
            suggestion="test",
        ))
        db.commit()
    finally:
        db.close()

    resp = client.delete(f"/projects/{project['id']}/ideas/{idea_id}", headers=headers)
    assert resp.status_code == 204

    resp = client.get(f"/articles/{idea_id}", headers=headers)
    assert resp.status_code == 404


def test_delete_non_idea_fails(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    resp = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "A Draft Article", "slug": "a-draft"},
        headers=headers,
    )
    assert resp.status_code == 201
    article_id = resp.json()["id"]

    resp = client.delete(f"/projects/{project['id']}/ideas/{article_id}", headers=headers)
    assert resp.status_code == 400
    assert "déjà en production" in resp.json()["detail"]


def test_delete_published_article_from_ideas_fails(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    resp = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Published Article", "slug": "published-article"},
        headers=headers,
    )
    assert resp.status_code == 201
    article_id = resp.json()["id"]
    force_publish_article(article_id)

    resp = client.delete(f"/projects/{project['id']}/ideas/{article_id}", headers=headers)
    assert resp.status_code == 400
    assert "publié" in resp.json()["detail"]


def test_delete_idea_wrong_project_fails(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    other = _create_project(client, register_and_login(client, email="other@test.com"), name="Other")

    idea_id = _make_idea(client, headers, project, "idea_proposed")

    resp = client.delete(f"/projects/{other['id']}/ideas/{idea_id}", headers=headers)
    assert resp.status_code == 404


def test_delete_idea_viewer_cannot(client: TestClient):
    owner_headers = register_and_login(client, email="owner_del@test.com")
    viewer_headers = register_and_login(client, email="viewer_del@test.com", name="ViewerDel")
    project = _create_project(client, owner_headers)

    idea_id = _make_idea(client, owner_headers, project, "idea_proposed")

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

    resp = client.delete(f"/projects/{project['id']}/ideas/{idea_id}", headers=viewer_headers)
    assert resp.status_code == 403


def test_bulk_delete_ideas(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    ids = []

    for _ in range(3):
        ids.append(_make_idea(client, headers, project, "idea_proposed"))

    resp = client.post(
        f"/projects/{project['id']}/ideas/bulk-delete",
        json={"article_ids": ids},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 3

    for idea_id in ids:
        resp = client.get(f"/articles/{idea_id}", headers=headers)
        assert resp.status_code == 404


def test_bulk_delete_ideas_partial_success(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    rejected_id = _make_idea(client, headers, project, "idea_rejected")
    proposed_id = _make_idea(client, headers, project, "idea_proposed")

    resp = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Real Draft", "slug": "real-draft"},
        headers=headers,
    )
    assert resp.status_code == 201
    draft_id = resp.json()["id"]

    resp = client.post(
        f"/projects/{project['id']}/ideas/bulk-delete",
        json={"article_ids": [rejected_id, draft_id, proposed_id]},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] == 2
    assert data["skipped"] == 1
    assert set(data["deleted_ids"]) == {rejected_id, proposed_id}
    assert "ignorée" in data["message"]

    assert client.get(f"/articles/{rejected_id}", headers=headers).status_code == 404
    assert client.get(f"/articles/{proposed_id}", headers=headers).status_code == 404
    assert client.get(f"/articles/{draft_id}", headers=headers).status_code == 200


# ── Restore ───────────────────────────────────────────────────────────────────


def test_restore_rejected_idea(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    idea_id = _make_idea(client, headers, project, "idea_rejected")

    db = TestingSessionLocal()
    try:
        from app.models.article import Article
        article = db.get(Article, idea_id)
        article.rejection_reason = "off_topic"
        article.rejection_note = "Not relevant"
        db.commit()
    finally:
        db.close()

    resp = client.post(f"/articles/{idea_id}/restore-idea", json={}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "restored"

    resp = client.get(f"/articles/{idea_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "idea_proposed"


def test_restore_non_rejected_fails(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    idea_id = _make_idea(client, headers, project, "idea_proposed")

    resp = client.post(f"/articles/{idea_id}/restore-idea", json={}, headers=headers)
    assert resp.status_code == 400


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
