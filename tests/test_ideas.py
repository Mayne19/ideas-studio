import pytest
from fastapi.testclient import TestClient
from tests.conftest import register_and_login, TestingSessionLocal


def _create_project(client: TestClient, headers: dict, name: str = "Test Blog") -> dict:
    resp = client.post("/projects", json={"name": name, "domain": "testblog.com", "language": "fr"}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _generate_idea(client: TestClient, headers: dict, project_id: str) -> dict:
    resp = client.post(f"/projects/{project_id}/ideas/generate", json={}, headers=headers)
    assert resp.status_code == 200
    return resp.json()


# ── Providers ─────────────────────────────────────────────────────────────────

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


def test_get_llm_provider_returns_mock_by_default():
    from app.services.providers.llm_provider import get_llm_provider, MockLLMProvider
    provider = get_llm_provider()
    assert isinstance(provider, MockLLMProvider)


def test_get_llm_provider_raises_in_production_when_ollama_unavailable(monkeypatch):
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
    try:
        settings.DEFAULT_LLM_PROVIDER = "openai"
        settings.OPENAI_API_KEY = "test-key"
        settings.OPENAI_MODEL = "gpt-test"
        monkeypatch.setattr(OpenAILLMProvider, "is_available", lambda self: True)
        provider = get_llm_provider()
        assert isinstance(provider, OpenAILLMProvider)
        assert provider.model_name == "gpt-test"
    finally:
        settings.DEFAULT_LLM_PROVIDER = old_provider
        settings.OPENAI_API_KEY = old_key
        settings.OPENAI_MODEL = old_model


def test_get_search_provider_returns_mock_by_default():
    from app.services.providers.search_provider import get_search_provider, MockSearchProvider
    provider = get_search_provider()
    assert isinstance(provider, MockSearchProvider)


# ── Idea Engine ────────────────────────────────────────────────────────────────

def test_generate_idea_creates_article_with_idea_proposed(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    resp = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=headers)
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
        assert "Provider IA indisponible" in resp.json()["detail"]
    finally:
        settings.APP_ENV = old_env
        settings.DEFAULT_LLM_PROVIDER = old_provider
        settings.OLLAMA_URL = old_url


def test_generate_idea_deduplication(client: TestClient):
    """Generating the same keyword twice should return 409 on second attempt."""
    headers = register_and_login(client)
    project = _create_project(client, headers)

    # First generation succeeds
    resp1 = client.post(f"/projects/{project['id']}/ideas/generate", json={}, headers=headers)
    assert resp1.status_code == 200
    keyword = resp1.json()["keyword"]

    # Manually trigger dedup by calling generate_idea directly with same keyword
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

    # Register viewer as project member with viewer role
    viewer_resp = client.post("/auth/login", json={"email": "viewer@test.com", "password": "pass1234"})
    viewer_id = client.get("/auth/me", headers=viewer_headers).json()["id"]

    # Add viewer as a project member via direct DB manipulation
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


# ── Writing Engine ─────────────────────────────────────────────────────────────

def test_start_writing_produces_draft_ready(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    idea = _generate_idea(client, headers, project["id"])

    resp = client.post(f"/articles/{idea['id']}/start-writing", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft_ready"


def test_start_writing_converts_markdown_to_html(client: TestClient, monkeypatch):
    from app.routers import ideas as ideas_router

    class FakeArticleLLM:
        is_mock = False
        provider_name = "fake"
        model_name = "test-model"

        def describe(self) -> str:
            return "fake model=test-model mock=False"

        def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
            if "meta title" in prompt.lower():
                return "Meta title de test"
            if "meta description" in prompt.lower():
                return "Meta description de test suffisamment longue pour valider le chemin."
            return "# Intro\n\n## Section test\n\nParagraphe détaillé.\n\n### Sous-section\n\n- Point 1\n- Point 2"

        def generate_json(self, prompt: str, schema_hint: str | None = None):
            return [
                {"heading": "Section test", "notes": "Développer un exemple concret"},
                {"heading": "Sous-section", "notes": "Ajouter des détails utiles"},
            ]

        def is_available(self) -> bool:
            return True

    headers = register_and_login(client, email="markdown_html@test.com")
    project = _create_project(client, headers)
    idea = _generate_idea(client, headers, project["id"])

    monkeypatch.setattr(ideas_router, "get_llm_provider", lambda: FakeArticleLLM())
    resp = client.post(f"/articles/{idea['id']}/start-writing", headers=headers)
    assert resp.status_code == 200

    article_resp = client.get(f"/articles/{idea['id']}", headers=headers)
    content = article_resp.json()["content"]
    assert "<h2>Section test</h2>" in content
    assert "<h3>Sous-section</h3>" in content
    assert "## Section test" not in content


def test_start_writing_saves_seo_review_json(client: TestClient, monkeypatch):
    from app.routers import ideas as ideas_router

    class FakeArticleLLM:
        is_mock = False
        provider_name = "fake"
        model_name = "test-model"

        def describe(self) -> str:
            return "fake model=test-model mock=False"

        def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
            if "meta title" in prompt.lower():
                return "Meta title de test"
            if "meta description" in prompt.lower():
                return "Meta description de test suffisamment longue pour valider le chemin."
            return (
                "# Introduction\n\n"
                "## Reponse rapide\n\n"
                "Selon Google Search Central, il faut d'abord traiter les bases techniques avant d'optimiser le reste.\n\n"
                "## Etapes detaillees\n\n"
                + ("Un paragraphe utile avec exemple concret et source citee. " * 180)
            )

        def generate_json(self, prompt: str, schema_hint: str | None = None):
            prompt_lower = prompt.lower()
            if '"faq"' in (schema_hint or "") or "faq" in prompt_lower:
                return {
                    "faq": [
                        {"question": "Qu'est-ce que le SEO technique ?", "answer": "L'ensemble des bases techniques qui aident l'exploration et l'indexation."},
                        {"question": "Par quoi commencer ?", "answer": "Par le crawl, l'indexation et les signaux essentiels."},
                    ]
                }
            return {
                "outline": [
                    {"heading": "Reponse rapide", "notes": "Donner la reponse principale"},
                    {"heading": "Etapes detaillees", "notes": "Donner un plan concret"},
                ]
            }

        def is_available(self) -> bool:
            return True

    headers = register_and_login(client, email="seo_review_generation@test.com")
    project = _create_project(client, headers)
    idea = _generate_idea(client, headers, project["id"])

    monkeypatch.setattr(ideas_router, "get_llm_provider", lambda: FakeArticleLLM())
    resp = client.post(f"/articles/{idea['id']}/start-writing", headers=headers)
    assert resp.status_code == 200

    editor = client.get(f"/articles/{idea['id']}/editor", headers=headers)
    assert editor.status_code == 200
    seo_review = editor.json()["seo_review_json"]
    assert seo_review is not None
    assert "score_global" in seo_review
    assert isinstance(seo_review["issues"], list)


def test_start_writing_keeps_article_when_seo_review_runtime_fails(client: TestClient, monkeypatch):
    from app.routers import ideas as ideas_router
    from app.services import writing_engine

    class FakeArticleLLM:
        is_mock = False
        provider_name = "fake"
        model_name = "test-model"

        def describe(self) -> str:
            return "fake model=test-model mock=False"

        def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
            if "meta title" in prompt.lower():
                return "Meta title de test"
            if "meta description" in prompt.lower():
                return "Meta description de test suffisamment longue pour valider le chemin."
            return (
                "# Introduction\n\n"
                "## Reponse rapide\n\n"
                "Selon Google Search Central, il faut commencer par la base.\n\n"
                "## Etapes detaillees\n\n"
                + ("Contenu detaille avec source et exemple concret. " * 180)
            )

        def generate_json(self, prompt: str, schema_hint: str | None = None):
            prompt_lower = prompt.lower()
            if '"faq"' in (schema_hint or "") or "faq" in prompt_lower:
                return {
                    "faq": [
                        {"question": "Question 1 ?", "answer": "Reponse 1."},
                        {"question": "Question 2 ?", "answer": "Reponse 2."},
                    ]
                }
            return {
                "outline": [
                    {"heading": "Reponse rapide", "notes": "Donner la reponse"},
                    {"heading": "Etapes detaillees", "notes": "Donner le detail"},
                ]
            }

        def is_available(self) -> bool:
            return True

    headers = register_and_login(client, email="seo_review_runtime_generation@test.com")
    project = _create_project(client, headers)
    idea = _generate_idea(client, headers, project["id"])

    monkeypatch.setattr(ideas_router, "get_llm_provider", lambda: FakeArticleLLM())
    monkeypatch.setattr(writing_engine, "run_and_store_seo_review", lambda _article: (_ for _ in ()).throw(RuntimeError("boom")))

    resp = client.post(f"/articles/{idea['id']}/start-writing", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft_ready"

    editor = client.get(f"/articles/{idea['id']}/editor", headers=headers)
    assert editor.status_code == 200
    seo_review = editor.json()["seo_review_json"]
    assert seo_review is not None
    assert "seo_expert_runtime" in seo_review["failed_checks"]


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


def test_start_writing_viewer_cannot(client: TestClient):
    owner_headers = register_and_login(client, email="owner2@test.com")
    viewer_headers = register_and_login(client, email="viewer2@test.com", name="Viewer2")
    project = _create_project(client, owner_headers)
    idea = _generate_idea(client, owner_headers, project["id"])

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

    resp = client.post(f"/articles/{idea['id']}/start-writing", headers=viewer_headers)
    assert resp.status_code == 403


# ── Reject ─────────────────────────────────────────────────────────────────────

def test_reject_idea(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    idea = _generate_idea(client, headers, project["id"])

    resp = client.post(
        f"/articles/{idea['id']}/reject",
        json={"rejection_reason": "off_topic", "rejection_note": "Not relevant"},
        headers=headers,
    )
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

def test_set_priority_sets_idea_priority_status(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    idea = _generate_idea(client, headers, project["id"])

    resp = client.post(f"/articles/{idea['id']}/priority", json={"priority": 5}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] == 5
    assert data["status"] == "idea_priority"


def test_priority_viewer_cannot(client: TestClient):
    owner_headers = register_and_login(client, email="owner3@test.com")
    viewer_headers = register_and_login(client, email="viewer3@test.com", name="Viewer3")
    project = _create_project(client, owner_headers)
    idea = _generate_idea(client, owner_headers, project["id"])

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

    resp = client.post(f"/articles/{idea['id']}/priority", json={"priority": 1}, headers=viewer_headers)
    assert resp.status_code == 403


# ── Manual Draft ───────────────────────────────────────────────────────────────

def test_manual_draft_converts_idea_to_draft_ready(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    idea = _generate_idea(client, headers, project["id"])

    resp = client.post(f"/articles/{idea['id']}/manual-draft", headers=headers)
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

def test_rerun_writing_produces_draft_ready(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    idea = _generate_idea(client, headers, project["id"])

    client.post(f"/articles/{idea['id']}/start-writing", headers=headers)
    resp = client.post(f"/articles/{idea['id']}/rerun", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft_ready"


# ── Launch ─────────────────────────────────────────────────────────────────────

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

    # Ideas should have status idea_proposed, not draft_ready
    for article_id in data["article_ids"]:
        article_resp = client.get(f"/articles/{article_id}", headers=headers)
        assert article_resp.json()["status"] == "idea_proposed"


def test_launch_full_article_mode(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    resp = client.post(f"/projects/{project['id']}/launch", json={"mode": "full_article"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "full_article"
    assert data["ideas_generated"] >= 1

    # Articles should be draft_ready after full pipeline
    for article_id in data["article_ids"]:
        article_resp = client.get(f"/articles/{article_id}", headers=headers)
        assert article_resp.json()["status"] == "draft_ready"


def test_launch_full_article_transmits_fields_and_generates_metadata(client: TestClient, monkeypatch):
    from app.routers import ideas as ideas_router
    from app.models.category import Category
    import uuid

    class FakeFullArticleLLM:
        is_mock = False
        provider_name = "fake-openai"
        model_name = "test-cloud"

        def describe(self) -> str:
            return "fake-openai model=test-cloud mock=False"

        def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
            if "meta title" in prompt.lower():
                return "Titre SEO test"
            if "meta description" in prompt.lower():
                return "Meta description de test suffisamment longue pour être utilisable en SEO."
            return (
                "# Introduction\n\n"
                "Un paragraphe d'introduction détaillé pour lancer le sujet.\n\n"
                "## Première section\n\n"
                "Un contenu développé avec des explications concrètes et utiles pour l'utilisateur.\n\n"
                "### Exemple\n\n"
                "- Point détaillé 1\n- Point détaillé 2\n\n"
                "> Conseil terrain.\n\n"
                "| Étape | Détail |\n| --- | --- |\n| 1 | Action |\n"
            )

        def generate_json(self, prompt: str, schema_hint: str | None = None):
            prompt_lower = prompt.lower()
            if '"faq"' in (schema_hint or "") or "faq" in prompt_lower:
                return {
                    "faq": [
                        {"question": "Qu'est-ce qu'une landing page ?", "answer": "Une page conçue pour convertir."},
                        {"question": "Pourquoi optimiser le SEO ?", "answer": "Pour attirer un trafic qualifié."},
                    ]
                }
            if '"outline"' in (schema_hint or "") or "plan détaillé" in prompt_lower:
                return {
                    "outline": [
                        {"heading": "Première section", "notes": "Développer le sujet"},
                        {"heading": "Exemple", "notes": "Illustrer avec un cas concret"},
                    ]
                }
            return {
                "title": "Titre généré ignoré",
                "keyword": "mot-clé généré",
                "angle": "Angle généré",
                "search_intent": "informational",
                "audience": "Audience générée",
            }

        def is_available(self) -> bool:
            return True

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

    monkeypatch.setattr(ideas_router, "get_llm_provider", lambda: FakeFullArticleLLM())

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
    assert data["provider_name"] == "fake-openai"
    assert len(data["article_ids"]) == 1

    article_resp = client.get(f"/articles/{data['article_ids'][0]}", headers=headers)
    article = article_resp.json()
    assert article["title"] == "Titre utilisateur prioritaire"
    assert article["category_id"] == category_id
    assert article["status"] == "draft_ready"
    assert article["keyword"] == "landing page mobile"
    assert article["reading_time_minutes"] >= 1
    assert article["slug"] == "titre-utilisateur-prioritaire"
    assert "<h2>Première section</h2>" in article["content"]
    assert "## Première section" not in article["content"]

    preview = client.get(f"/articles/{article['id']}/preview", headers=headers).json()
    assert preview["faq_json"] is not None
    assert "Qu'est-ce qu'une landing page ?" in preview["faq_json"]


def test_launch_dry_run(client: TestClient):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    resp = client.post(f"/projects/{project['id']}/launch", json={"dry_run": True}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["ideas_generated"] == 0


# ── Scheduler ─────────────────────────────────────────────────────────────────

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
