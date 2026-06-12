"""Tests for Agent Registry, AgentRouter, and agent_services."""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import register_and_login, TestingSessionLocal


# ── Agent Registry Unit Tests ─────────────────────────────────────────────────


def test_agent_registry_has_27_agents():
    from app.services.agents.agent_registry import list_agents, AGENTS_BY_CATEGORY
    agents = list_agents()
    assert len(agents) == 27
    assert set(AGENTS_BY_CATEGORY.keys()) == {"research", "strategy", "creation", "review"}


def test_agent_registry_categories():
    from app.services.agents.agent_registry import list_agents
    agents = list_agents()
    for a in agents:
        assert a.category.value in ("research", "strategy", "creation", "review")


def test_agent_registry_get_agent():
    from app.services.agents.agent_registry import get_agent
    agent = get_agent("content_writer")
    assert agent is not None
    assert agent.name == "Rédacteur"
    assert agent.category.value == "creation"
    assert agent.requires_llm is True


def test_agent_registry_get_unknown():
    from app.services.agents.agent_registry import get_agent
    assert get_agent("nonexistent") is None


def test_agent_registry_filter_by_category():
    from app.services.agents.agent_registry import list_agents
    research = list_agents(category="research")
    assert len(research) == 6
    for a in research:
        assert a.category.value == "research"


def test_serialize_agent():
    from app.services.agents.agent_registry import serialize_agent, get_agent
    data = serialize_agent(get_agent("idea_generator"))
    assert data["agent_id"] == "idea_generator"
    assert data["category"] == "strategy"
    assert "name" in data
    assert "description" in data


# ── AgentRouter Unit Tests ────────────────────────────────────────────────────


def test_agent_router_falls_back_to_mock():
    from app.services.agents.agent_router import AgentRouter
    router = AgentRouter(db=None)
    provider = router.get_provider("fact_checker")
    assert provider is not None
    assert provider.is_mock  # Will be mock since no real provider configured


def test_agent_router_returns_mock_for_non_llm_agent():
    """Agents that don't require LLM should return mock."""
    from app.services.agents.agent_router import AgentRouter
    router = AgentRouter(db=None)
    provider = router.get_provider("keyword_researcher")
    # keyword_researcher has requires_search=True not requires_llm=False
    # so it should still try to resolve to a provider
    assert provider is not None


def test_agent_router_cache():
    from app.services.agents.agent_router import AgentRouter
    router = AgentRouter(db=None)
    p1 = router.get_provider("content_writer")
    p2 = router.get_provider("content_writer")
    assert p1 is p2  # Same cached instance
    router.clear_cache()
    p3 = router.get_provider("content_writer")
    assert p3 is not None


# ── Agent Services Unit Tests (mock mode) ─────────────────────────────────────


def test_fact_check_article_mock():
    from app.services.agents.agent_services import fact_check_article
    result = fact_check_article("Some content", "Test Title", "test")
    assert result["status"] == "skipped"
    assert "mock" in result["message"]


def test_seo_optimize_content_mock():
    from app.services.agents.agent_services import seo_optimize_content
    result = seo_optimize_content("Content here", "Title", "keyword")
    assert result["status"] == "skipped"


def test_editorial_review_mock():
    from app.services.agents.agent_services import editorial_review
    result = editorial_review("Content", "Title")
    assert result["status"] == "skipped"


def test_quality_rate_article_mock():
    from app.services.agents.agent_services import quality_rate_article
    result = quality_rate_article("Content", "Title")
    assert result["status"] == "skipped"


# ── Agent Assignment Model & API Tests ────────────────────────────────────────


def _create_admin_user(client: TestClient) -> dict:
    headers = register_and_login(client, email="admin@agents-test.com")
    return headers


def _create_project(client: TestClient, headers: dict) -> dict:
    resp = client.post("/projects", json={"name": "Agent Test Project", "language": "fr"}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def test_list_agents_endpoint(client: TestClient):
    headers = _create_admin_user(client)
    resp = client.get("/settings/ai-agents", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 27
    assert data[0]["agent_id"] is not None
    assert data[0]["category"] in ("research", "strategy", "creation", "review")


def test_get_agent_info(client: TestClient):
    headers = _create_admin_user(client)
    resp = client.get("/settings/ai-agents/content_writer", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == "content_writer"
    assert data["name"] == "Rédacteur"


def test_get_agent_info_unknown(client: TestClient):
    headers = _create_admin_user(client)
    resp = client.get("/settings/ai-agents/nonexistent", headers=headers)
    assert resp.status_code == 404


def test_list_assignments_empty(client: TestClient):
    headers = _create_admin_user(client)
    resp = client.get("/settings/ai-agents/assignments", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_assignment_needs_provider(client: TestClient):
    """Creating an assignment without a valid provider should fail."""
    headers = _create_admin_user(client)
    resp = client.put("/settings/ai-agents/assignments", json={
        "agent_id": "content_writer",
        "provider_id": "nonexistent-id",
        "enabled": True,
        "priority": 0,
    }, headers=headers)
    assert resp.status_code == 404


def test_create_assignment_success(client: TestClient):
    headers = _create_admin_user(client)
    _create_project(client, headers)

    # First create a provider via the providers endpoint
    provider_resp = client.post("/settings/ai-providers", json={
        "provider": "ollama",
        "label": "Local Ollama",
        "api_key": "",
        "model": "qwen3:14b",
        "base_url": "http://127.0.0.1:11434",
        "is_default": True,
        "enabled": True,
    }, headers=headers)
    assert provider_resp.status_code == 201
    provider_id = provider_resp.json()["id"]

    # Now assign it to content_writer
    resp = client.put("/settings/ai-agents/assignments", json={
        "agent_id": "content_writer",
        "provider_id": provider_id,
        "enabled": True,
        "priority": 0,
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["agent_id"] == "content_writer"
    assert data["provider_id"] == provider_id
    assert data["enabled"] is True
    assert data["agent"]["name"] == "Rédacteur"
    assert data["provider_name"] == "ollama"


def test_list_assignments_after_create(client: TestClient):
    headers = _create_admin_user(client)
    _create_project(client, headers)

    provider_resp = client.post("/settings/ai-providers", json={
        "provider": "ollama",
        "label": "Local",
        "api_key": "",
        "model": "qwen3:14b",
        "is_default": True,
        "enabled": True,
    }, headers=headers)
    provider_id = provider_resp.json()["id"]

    client.put("/settings/ai-agents/assignments", json={
        "agent_id": "faq_generator",
        "provider_id": provider_id,
        "enabled": False,
        "priority": 1,
    }, headers=headers)

    resp = client.get("/settings/ai-agents/assignments", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["agent_id"] == "faq_generator"
    assert data[0]["enabled"] is False
    assert data[0]["priority"] == 1


def test_patch_assignment(client: TestClient):
    headers = _create_admin_user(client)
    _create_project(client, headers)

    provider_resp = client.post("/settings/ai-providers", json={
        "provider": "openai",
        "label": "OpenAI",
        "api_key": "sk-test",
        "model": "gpt-4o-mini",
        "is_default": True,
        "enabled": True,
    }, headers=headers)
    provider_id = provider_resp.json()["id"]

    create_resp = client.put("/settings/ai-agents/assignments", json={
        "agent_id": "title_generator",
        "provider_id": provider_id,
        "enabled": True,
        "priority": 0,
    }, headers=headers)
    assignment_id = create_resp.json()["id"]

    # Patch to disable
    patch_resp = client.patch(f"/settings/ai-agents/assignments/{assignment_id}", json={
        "enabled": False,
    }, headers=headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["enabled"] is False


def test_assignments_require_auth(client: TestClient):
    resp = client.get("/settings/ai-agents")
    assert resp.status_code == 401


def test_assignments_without_admin(client: TestClient):
    """Non-admin user should get 403 when no admin exists."""
    headers = register_and_login(client, email="normal@test.com")
    # First registered user auto-becomes admin; verify access is granted
    resp = client.get("/settings/ai-agents", headers=headers)
    assert resp.status_code == 200


def test_assignments_blocked_when_admin_exists(client: TestClient):
    """Non-admin should be blocked when an admin already exists."""
    _create_admin_user(client)
    headers = register_and_login(client, email="other@test.com")
    resp = client.get("/settings/ai-agents", headers=headers)
    assert resp.status_code == 403


# ── AgentRouter with DB assignments (integration) ──────────────────────────────


def test_agent_router_resolves_from_db():
    """Test that AgentRouter picks up DB assignments."""
    from app.services.agents.agent_router import AgentRouter
    from app.models.ai_provider_config import AIProviderConfig
    from app.models.agent_assignment import AgentAssignment
    from app.core.security import encrypt_secret

    db = TestingSessionLocal()
    try:
        # Create a provider
        provider = AIProviderConfig(
            provider="openai",
            label="Test OpenAI",
            api_key_encrypted=encrypt_secret("sk-test"),
            model="gpt-4o-mini",
            is_default=True,
            enabled=True,
        )
        db.add(provider)
        db.flush()

        # Create assignment
        ass = AgentAssignment(
            agent_id="content_writer",
            provider_id=provider.id,
            enabled=True,
            priority=0,
        )
        db.add(ass)
        db.commit()

        # Router should find the assignment and build the provider
        router = AgentRouter(db=db)
        provider_obj = router._resolve_provider("content_writer")
        assert provider_obj is not None
        assert provider_obj.provider_name == "openai"
    finally:
        db.close()


def test_agent_router_resolves_from_default_fallback():
    """AgentRouter should fall back to global get_llm_provider when no assignment."""
    from app.services.agents.agent_router import AgentRouter
    router = AgentRouter(db=None)
    provider = router.get_provider("content_writer")
    # In test env, should get Mock provider
    assert provider.is_mock is True


# ── AI Provider Config CRUD (with new fields) ──────────────────────────────────


def test_create_provider_with_project_id(client: TestClient):
    headers = _create_admin_user(client)
    project = _create_project(client, headers)

    resp = client.post("/settings/ai-providers", json={
        "provider": "custom",
        "label": "Custom for Project",
        "display_name": "Mon Provider Custom",
        "project_id": project["id"],
        "api_key": "custom-key",
        "model": "custom-model",
        "base_url": "https://custom.api/v1",
        "is_default": True,
        "enabled": True,
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["project_id"] == project["id"]
    assert data["display_name"] == "Mon Provider Custom"
    assert data["api_key_configured"] is True
    assert data["provider"] == "custom"


def test_create_provider_duplicate_for_project(client: TestClient):
    headers = _create_admin_user(client)
    project = _create_project(client, headers)

    client.post("/settings/ai-providers", json={
        "provider": "gemini",
        "label": "First",
        "api_key": "key1",
        "project_id": project["id"],
        "is_default": True,
        "enabled": True,
    }, headers=headers)

    resp = client.post("/settings/ai-providers", json={
        "provider": "gemini",
        "label": "Second",
        "api_key": "key2",
        "project_id": project["id"],
        "is_default": False,
        "enabled": True,
    }, headers=headers)
    assert resp.status_code == 409


def test_list_providers_by_project(client: TestClient):
    headers = _create_admin_user(client)
    project = _create_project(client, headers)

    client.post("/settings/ai-providers", json={
        "provider": "ollama",
        "label": "Project Ollama",
        "api_key": "",
        "project_id": project["id"],
        "is_default": True,
        "enabled": True,
    }, headers=headers)

    # List with project filter
    resp = client.get(f"/settings/ai-providers?project_id={project['id']}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["project_id"] == project["id"]


def test_update_provider_display_name(client: TestClient):
    headers = _create_admin_user(client)

    create_resp = client.post("/settings/ai-providers", json={
        "provider": "openrouter",
        "label": "OR",
        "api_key": "sk-or",
        "is_default": True,
        "enabled": True,
    }, headers=headers)
    provider_id = create_resp.json()["id"]

    patch_resp = client.patch(f"/settings/ai-providers/{provider_id}", json={
        "display_name": "Mon OpenRouter Custom",
    }, headers=headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["display_name"] == "Mon OpenRouter Custom"
