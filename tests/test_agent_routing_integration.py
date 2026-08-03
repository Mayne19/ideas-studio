"""Chemin complet UI → assignation en base → provider réellement utilisé par le pipeline.

Ces tests couvrent le trou laissé par tests/test_agents.py, qui n'exerçait que
`_resolve_provider` avec des agent_id legacy codés en dur : une assignation créée
depuis l'UI (agent_id canonique) n'était jamais retrouvée par le code de production,
qui interrogeait les alias legacy.
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import register_and_login, TestingSessionLocal


@pytest.fixture
def no_agent_env_override(monkeypatch):
    """Neutralise les AGENT_*_PROVIDER du .env local.

    Sans cela, la résolution retomberait sur la variable d'environnement du poste
    de dev et les assertions « aucun provider » dépendraient de la machine.
    """
    from app.core.config import settings

    for field in type(settings).model_fields:
        if field.startswith("AGENT_") and field.endswith(("_PROVIDER", "_MODEL")):
            monkeypatch.setattr(settings, field, "", raising=False)
    return settings


# ── Canonicalisation des agent_id ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "legacy_id,canonical_id",
    [
        ("content_writer", "writer"),
        ("title_generator", "meta_writer"),
        ("meta_description_writer", "meta_writer"),
        ("editor_revisor", "editor"),
        ("quality_rater", "quality_gate"),
        ("humanization_engine", "humanizer"),
        ("eeat_checker", "eeat_reviewer"),
        ("internal_link_builder", "internal_link_planner"),
    ],
)
def test_legacy_aliases_resolve_to_canonical(legacy_id, canonical_id):
    from app.services.agents.agent_registry import resolve_agent_id

    assert resolve_agent_id(legacy_id) == canonical_id


def test_canonical_ids_resolve_to_themselves():
    from app.services.agents.agent_registry import resolve_agent_id

    for agent_id in ("writer", "meta_writer", "editor", "quality_gate", "idea_generator"):
        assert resolve_agent_id(agent_id) == agent_id


def test_every_alias_targets_an_existing_visible_agent():
    """Un alias ne doit jamais pointer vers un agent absent ou invisible dans l'UI."""
    from app.services.agents.agent_registry import list_agents, get_agent

    for agent in list_agents():
        if not agent.alias_of:
            continue
        target = get_agent(agent.alias_of)
        assert target is not None, f"{agent.agent_id} pointe vers un agent inexistant"
        assert target.visible_in_frontend, (
            f"{agent.agent_id} pointe vers {target.agent_id}, invisible dans l'UI : "
            "l'assignation serait impossible à créer"
        )
        assert not target.alias_of, "alias en chaîne interdit"


def test_pipeline_call_sites_use_configurable_agents():
    """Les agents interrogés par le pipeline doivent être assignables depuis l'UI."""
    from app.services.agents.agent_registry import get_agent, resolve_agent_id

    called_by_pipeline = [
        "writer", "meta_writer", "faq_generator", "editor",
        "quality_gate", "seo_optimizer", "fact_checker", "idea_generator",
    ]
    for agent_id in called_by_pipeline:
        assert resolve_agent_id(agent_id) == agent_id
        agent = get_agent(agent_id)
        assert agent is not None and agent.visible_in_frontend, (
            f"'{agent_id}' est appelé par le pipeline mais n'est pas configurable dans l'UI"
        )


# ── UI → base → routeur ────────────────────────────────────────────────────────


def _setup_project_with_provider(client: TestClient, provider: str = "openai") -> tuple[dict, str, str]:
    headers = register_and_login(client, email=f"routing-{provider}@test.com")
    project = client.post(
        "/projects", json={"name": "Routing Test", "language": "fr"}, headers=headers
    ).json()
    resp = client.post(
        "/settings/ai-providers",
        json={
            "provider": provider,
            "label": f"Test {provider}",
            "api_key": "sk-routing-test",
            "model": "test-model",
            "project_id": project["id"],
            "is_default": False,
            "enabled": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return headers, project["id"], resp.json()["id"]


def test_assignment_created_from_ui_is_used_by_pipeline(client: TestClient):
    """Le cœur du bug : assigner un provider au Rédacteur doit changer le provider réel."""
    from app.services.agents.agent_router import AgentRouter

    headers, project_id, provider_id = _setup_project_with_provider(client, "openai")

    resp = client.put(
        "/settings/ai-agents/assignments",
        json={
            "agent_id": "writer",
            "provider_id": provider_id,
            "project_id": project_id,
            "enabled": True,
            "priority": 0,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    db = TestingSessionLocal()
    try:
        router = AgentRouter(db=db)
        # Le pipeline appelle l'agent canonique...
        resolved = router._resolve_provider("writer", project_id=project_id)
        assert resolved is not None and resolved.provider_name == "openai"
        # ...et le code legacy encore en place doit retrouver la même assignation.
        legacy = AgentRouter(db=db)._resolve_provider("content_writer", project_id=project_id)
        assert legacy is not None and legacy.provider_name == "openai"
    finally:
        db.close()


def test_legacy_assignment_is_honoured_by_canonical_lookup(client: TestClient):
    """Les assignations historiques (agent_id legacy en base) restent fonctionnelles."""
    from app.services.agents.agent_router import AgentRouter
    from app.models.agent_assignment import AgentAssignment

    headers, project_id, provider_id = _setup_project_with_provider(client, "gemini")

    db = TestingSessionLocal()
    try:
        db.add(
            AgentAssignment(
                project_id=project_id,
                agent_id="editor_revisor",  # ancien ID, tel qu'écrit par les versions précédentes
                provider_id=provider_id,
                enabled=True,
                priority=0,
            )
        )
        db.commit()

        resolved = AgentRouter(db=db)._resolve_provider("editor", project_id=project_id)
        assert resolved is not None and resolved.provider_name == "gemini"
    finally:
        db.close()


def test_disabled_assignment_falls_back_to_project_default(client: TestClient, no_agent_env_override):
    from app.services.agents.agent_router import AgentRouter

    headers, project_id, provider_id = _setup_project_with_provider(client, "openai")
    client.put(
        "/settings/ai-agents/assignments",
        json={
            "agent_id": "writer",
            "provider_id": provider_id,
            "project_id": project_id,
            "enabled": False,
            "priority": 0,
        },
        headers=headers,
    )

    db = TestingSessionLocal()
    try:
        # Aucun provider par défaut sur ce projet : la résolution doit renoncer
        # plutôt que d'utiliser une assignation désactivée.
        assert AgentRouter(db=db)._resolve_provider("writer", project_id=project_id) is None
    finally:
        db.close()


def test_assignment_is_scoped_to_its_project(client: TestClient, no_agent_env_override):
    """Une assignation d'un projet ne doit pas fuiter sur un autre projet."""
    from app.services.agents.agent_router import AgentRouter

    headers, project_id, provider_id = _setup_project_with_provider(client, "openai")
    other_project = client.post(
        "/projects", json={"name": "Autre", "language": "fr"}, headers=headers
    ).json()

    client.put(
        "/settings/ai-agents/assignments",
        json={
            "agent_id": "writer",
            "provider_id": provider_id,
            "project_id": project_id,
            "enabled": True,
            "priority": 0,
        },
        headers=headers,
    )

    db = TestingSessionLocal()
    try:
        assert AgentRouter(db=db)._resolve_provider("writer", project_id=other_project["id"]) is None
    finally:
        db.close()


# ── Cycle de vie des assignations ─────────────────────────────────────────────


def test_deleting_provider_removes_its_assignments(client: TestClient):
    from app.models.agent_assignment import AgentAssignment

    headers, project_id, provider_id = _setup_project_with_provider(client, "openai")
    client.put(
        "/settings/ai-agents/assignments",
        json={
            "agent_id": "writer",
            "provider_id": provider_id,
            "project_id": project_id,
            "enabled": True,
            "priority": 0,
        },
        headers=headers,
    )

    resp = client.delete(f"/settings/ai-providers/{provider_id}", headers=headers)
    assert resp.status_code == 204

    db = TestingSessionLocal()
    try:
        orphans = db.query(AgentAssignment).filter(
            AgentAssignment.provider_id == provider_id
        ).all()
        assert orphans == [], "les assignations doivent disparaître avec leur provider"
    finally:
        db.close()

    listed = client.get(
        f"/settings/ai-agents/assignments?project_id={project_id}", headers=headers
    )
    assert listed.status_code == 200
    assert listed.json() == []


def test_cleanup_orphan_assignments(client: TestClient):
    from app.models.agent_assignment import AgentAssignment
    from app.services.agents.agent_assignment_service import cleanup_orphan_assignments

    headers, project_id, provider_id = _setup_project_with_provider(client, "openai")

    db = TestingSessionLocal()
    try:
        db.add(
            AgentAssignment(
                project_id=project_id,
                agent_id="writer",
                provider_id="provider-supprime-hors-api",
                enabled=True,
                priority=0,
            )
        )
        db.commit()

        removed = cleanup_orphan_assignments(db)
        db.commit()
        assert removed == 1
        assert cleanup_orphan_assignments(db) == 0
    finally:
        db.close()


# ── Sécurité : plus d'auto-promotion admin ────────────────────────────────────


def test_reading_agents_never_grants_admin(client: TestClient):
    """Un GET ne doit jamais promouvoir son appelant en administrateur plateforme."""
    from app.models.user import User

    register_and_login(client, email="first-admin@test.com")  # 1er inscrit = admin
    headers = register_and_login(client, email="regular-user@test.com")

    assert client.get("/settings/ai-agents", headers=headers).status_code == 403

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "regular-user@test.com").first()
        assert user is not None and user.is_platform_admin is False
    finally:
        db.close()


# ── Cohérence des providers supportés ─────────────────────────────────────────


def test_every_supported_provider_is_constructible():
    """Un provider listé dans l'UI doit produire un client réel, pas planter à l'exécution."""
    from app.routers.ai_providers import SUPPORTED_PROVIDERS
    from app.services.providers.llm_provider import build_provider_from_config
    from app.core.security import encrypt_secret

    class _Config:
        def __init__(self, provider, defaults):
            self.id = "cfg-test"
            self.provider = provider
            self.api_key_encrypted = encrypt_secret("sk-test-key")
            self.model = defaults["default_model"] or None
            self.base_url = defaults["default_base_url"] or None

    for provider, defaults in SUPPORTED_PROVIDERS.items():
        built = build_provider_from_config(_Config(provider, defaults))
        assert built is not None, f"'{provider}' est proposé dans l'UI mais non constructible"
        assert built.provider_name == provider or provider == "custom", (
            f"{provider} -> provider_name={built.provider_name}"
        )


def test_anthropic_provider_uses_recommended_default_model():
    from app.services.providers.anthropic_provider import AnthropicLLMProvider

    provider = AnthropicLLMProvider(api_key="sk-ant-test")
    assert provider.provider_name == "anthropic"
    assert provider.model_name == "claude-opus-5"
    assert provider.is_mock is False


def test_provider_without_api_key_is_not_built():
    from app.services.providers.llm_provider import build_provider_from_config

    class _Config:
        id = "cfg-nokey"
        provider = "anthropic"
        api_key_encrypted = ""
        model = None
        base_url = None

    assert build_provider_from_config(_Config()) is None


def test_unknown_provider_is_rejected():
    from app.services.providers.llm_provider import build_provider_from_config
    from app.core.security import encrypt_secret

    class _Config:
        id = "cfg-unknown"
        provider = "provider-inexistant"
        api_key_encrypted = encrypt_secret("sk-test")
        model = None
        base_url = None

    assert build_provider_from_config(_Config()) is None


# ── Suivi des coûts : une estimation n'est pas un coût constaté ────────────────


def test_estimated_cost_is_not_reported_as_actual():
    """Sans tokens remontés par le provider, actual_cost doit rester nul."""
    from app.services.agents.agent_router import call_agent

    _, result = call_agent("writer", "generate_text", "Un prompt de test")
    assert result.actual_cost is None
    assert result.cost_status in ("not_tracked", "estimated", "unknown_price")


def test_measured_usage_produces_actual_cost(monkeypatch):
    """Quand le provider remonte ses tokens réels, ils priment sur l'estimation."""
    from app.services.agents import agent_router
    from app.services.providers.llm_provider import LLMProvider

    class _MeasuredProvider(LLMProvider):
        is_mock = False
        provider_name = "openai"
        model_name = "gpt-4o-mini"

        def __init__(self):
            self.last_usage = {"input_tokens": 1234, "output_tokens": 567}

        def generate_text(self, prompt, system=None, temperature=0.7):
            return "réponse"

        def generate_json(self, prompt, schema_hint=None):
            return {}

        def is_available(self):
            return True

    monkeypatch.setattr(
        agent_router.AgentRouter, "get_provider", lambda self, *a, **k: _MeasuredProvider()
    )

    _, result = agent_router.call_agent("writer", "generate_text", "prompt")
    assert result.input_tokens == 1234
    assert result.output_tokens == 567
    assert result.tokens == 1801
    if result.estimated_cost is not None:
        assert result.actual_cost == result.estimated_cost
