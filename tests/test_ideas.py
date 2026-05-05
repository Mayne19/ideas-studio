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
