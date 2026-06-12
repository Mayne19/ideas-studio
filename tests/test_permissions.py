"""Tests for project-level permissions on providers and agents endpoints."""

from fastapi.testclient import TestClient
from tests.conftest import register_and_login


def _create_project(client: TestClient, headers: dict) -> dict:
    resp = client.post("/projects", json={"name": "Perm Test Project", "language": "fr"}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _get_user_id(client: TestClient, headers: dict) -> str:
    resp = client.get("/auth/me", headers=headers)
    return resp.json()["id"]


def test_providers_accessible_by_project_owner(client: TestClient):
    """Project owner can list providers for their project."""
    headers = register_and_login(client, email="owner@test.com")
    project = _create_project(client, headers)
    resp = client.get(f"/settings/ai-providers?project_id={project['id']}", headers=headers)
    assert resp.status_code == 200


def test_providers_accessible_by_project_admin(client: TestClient):
    """Project admin can list providers for their project."""
    owner_headers = register_and_login(client, email="owner2@test.com")
    project = _create_project(client, owner_headers)

    admin_headers = register_and_login(client, email="admin@test.com")
    admin_id = _get_user_id(client, admin_headers)

    resp = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": admin_id, "role": "admin"},
        headers=owner_headers,
    )
    assert resp.status_code == 201, f"Failed to add admin member: {resp.text}"

    resp2 = client.get(f"/settings/ai-providers?project_id={project['id']}", headers=admin_headers)
    assert resp2.status_code == 200


def test_providers_blocked_for_project_editor(client: TestClient):
    """Editor role gets 403 on provider endpoints."""
    owner_headers = register_and_login(client, email="owner3@test.com")
    project = _create_project(client, owner_headers)

    editor_headers = register_and_login(client, email="editor@test.com")
    editor_id = _get_user_id(client, editor_headers)

    resp = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": editor_id, "role": "editor"},
        headers=owner_headers,
    )
    assert resp.status_code == 201, f"Failed to add editor: {resp.text}"

    resp2 = client.get(f"/settings/ai-providers?project_id={project['id']}", headers=editor_headers)
    assert resp2.status_code == 403
    assert "admin" in resp2.json()["detail"].lower()


def test_providers_blocked_for_project_writer(client: TestClient):
    """Writer role gets 403 on provider endpoints."""
    owner_headers = register_and_login(client, email="owner4@test.com")
    project = _create_project(client, owner_headers)

    writer_headers = register_and_login(client, email="writer@test.com")
    writer_id = _get_user_id(client, writer_headers)

    resp = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": writer_id, "role": "writer"},
        headers=owner_headers,
    )
    assert resp.status_code == 201, f"Failed to add writer: {resp.text}"

    resp = client.get(f"/settings/ai-providers?project_id={project['id']}", headers=writer_headers)
    assert resp.status_code == 403


def test_agents_accessible_by_project_owner(client: TestClient):
    """Project owner can list agents for their project."""
    headers = register_and_login(client, email="owner5@test.com")
    project = _create_project(client, headers)
    resp = client.get(f"/settings/ai-agents?project_id={project['id']}", headers=headers)
    assert resp.status_code == 200


def test_agents_accessible_by_project_admin(client: TestClient):
    """Project admin can list agents for their project."""
    owner_headers = register_and_login(client, email="owner6@test.com")
    project = _create_project(client, owner_headers)

    admin_headers = register_and_login(client, email="admin2@test.com")
    admin_id = _get_user_id(client, admin_headers)

    resp = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": admin_id, "role": "admin"},
        headers=owner_headers,
    )
    assert resp.status_code == 201, f"Failed to add admin: {resp.text}"

    resp2 = client.get(f"/settings/ai-agents?project_id={project['id']}", headers=admin_headers)
    assert resp2.status_code == 200


def test_agents_blocked_for_project_editor(client: TestClient):
    """Editor role gets 403 on agent endpoints."""
    owner_headers = register_and_login(client, email="owner7@test.com")
    project = _create_project(client, owner_headers)

    editor_headers = register_and_login(client, email="editor2@test.com")
    editor_id = _get_user_id(client, editor_headers)

    resp = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": editor_id, "role": "editor"},
        headers=owner_headers,
    )
    assert resp.status_code == 201, f"Failed to add editor: {resp.text}"

    resp = client.get(f"/settings/ai-agents?project_id={project['id']}", headers=editor_headers)
    assert resp.status_code == 403


def test_assignments_accessible_by_project_admin(client: TestClient):
    """Project admin can list and manage agent assignments."""
    owner_headers = register_and_login(client, email="owner8@test.com")
    project = _create_project(client, owner_headers)

    # Create a provider first
    provider_resp = client.post("/settings/ai-providers", json={
        "provider": "ollama",
        "label": "Test Ollama",
        "api_key": "",
        "project_id": project["id"],
        "is_default": True,
        "enabled": True,
    }, headers=owner_headers)
    assert provider_resp.status_code == 201
    provider_id = provider_resp.json()["id"]

    # Create assignment as owner
    assign_resp = client.put("/settings/ai-agents/assignments", json={
        "agent_id": "fact_checker",
        "provider_id": provider_id,
        "project_id": project["id"],
        "enabled": True,
        "priority": 0,
    }, headers=owner_headers)
    assert assign_resp.status_code == 201

    # Verify admin can read assignments
    admin_headers = register_and_login(client, email="admin3@test.com")
    admin_id = _get_user_id(client, admin_headers)

    resp = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": admin_id, "role": "admin"},
        headers=owner_headers,
    )
    assert resp.status_code == 201, f"Failed to add admin: {resp.text}"

    resp = client.get(f"/settings/ai-agents/assignments?project_id={project['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_provider_test_blocked_for_editor(client: TestClient):
    """Editor cannot test a provider connection."""
    owner_headers = register_and_login(client, email="owner9@test.com")
    project = _create_project(client, owner_headers)

    provider_resp = client.post("/settings/ai-providers", json={
        "provider": "gemini",
        "label": "Test Gemini",
        "api_key": "test-key-123",
        "project_id": project["id"],
        "is_default": True,
        "enabled": True,
    }, headers=owner_headers)
    assert provider_resp.status_code == 201
    provider_id = provider_resp.json()["id"]

    editor_headers = register_and_login(client, email="editor3@test.com")
    editor_id = _get_user_id(client, editor_headers)

    resp = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": editor_id, "role": "editor"},
        headers=owner_headers,
    )
    assert resp.status_code == 201, f"Failed to add editor: {resp.text}"

    resp = client.post(f"/settings/ai-providers/{provider_id}/test", headers=editor_headers)
    assert resp.status_code == 403
