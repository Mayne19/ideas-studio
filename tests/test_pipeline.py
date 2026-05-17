"""Tests for the automatic article creation pipeline."""
from fastapi.testclient import TestClient
from tests.conftest import register_and_login, TestingSessionLocal


def _setup(client: TestClient, email: str = "pipe_owner@test.com") -> tuple[dict, dict]:
    headers = register_and_login(client, email=email)
    resp = client.post("/projects", json={"name": "Pipeline Proj", "domain": "pipe.com", "language": "fr"}, headers=headers)
    assert resp.status_code == 201
    return headers, resp.json()


def test_get_default_pipeline_settings(client: TestClient):
    """GET pipeline returns sensible defaults before any PATCH."""
    headers, project = _setup(client, "pipe_default@test.com")
    resp = client.get(f"/projects/{project['id']}/pipeline", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["active_days"] == []
    assert data["launch_hour"] == 8
    assert data["articles_per_week"] == 5
    assert data["category_priorities"] == {}


def test_patch_pipeline_settings(client: TestClient):
    """PATCH updates pipeline settings correctly."""
    headers, project = _setup(client, "pipe_patch@test.com")
    resp = client.patch(f"/projects/{project['id']}/pipeline", json={
        "enabled": True,
        "active_days": ["monday", "friday"],
        "launch_hour": 10,
        "articles_per_week": 7,
        "category_priorities": {"cat-a": 8, "cat-b": 3},
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["active_days"] == ["monday", "friday"]
    assert data["launch_hour"] == 10
    assert data["articles_per_week"] == 7
    assert data["category_priorities"] == {"cat-a": 8, "cat-b": 3}


def test_patch_partial_pipeline(client: TestClient):
    """PATCH with partial fields only updates those fields."""
    headers, project = _setup(client, "pipe_partial@test.com")
    client.patch(f"/projects/{project['id']}/pipeline", json={
        "enabled": True,
        "launch_hour": 14,
    }, headers=headers)
    resp = client.get(f"/projects/{project['id']}/pipeline", headers=headers)
    data = resp.json()
    assert data["enabled"] is True
    assert data["launch_hour"] == 14
    assert data["articles_per_week"] == 5

    resp2 = client.patch(f"/projects/{project['id']}/pipeline", json={
        "enabled": False,
    }, headers=headers)
    assert resp2.json()["enabled"] is False
    assert resp2.json()["launch_hour"] == 14


def test_pipeline_run_creates_log(client: TestClient):
    """Triggering a pipeline run creates a log entry."""
    headers, project = _setup(client, "pipe_run@test.com")
    run = client.post(f"/projects/{project['id']}/pipeline/run", headers=headers)
    assert run.status_code == 200
    data = run.json()
    assert "status" in data
    assert "ideas_generated" in data
    assert "articles_created" in data

    logs = client.get(f"/projects/{project['id']}/pipeline/logs", headers=headers)
    assert logs.status_code == 200
    entries = logs.json()
    assert len(entries) >= 1
    assert entries[0]["status"] == "completed"


def test_pipeline_logs_empty_when_no_runs(client: TestClient):
    """Project with no pipeline runs returns empty log list."""
    headers, project = _setup(client, "pipe_nolog@test.com")
    resp = client.get(f"/projects/{project['id']}/pipeline/logs", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_pipeline_requires_manager_role(client: TestClient):
    """Non-members should not be able to update pipeline settings."""
    headers, project = _setup(client, "pipe_mgr@test.com")
    other_h = register_and_login(client, email="pipe_other@test.com")
    resp = client.patch(f"/projects/{project['id']}/pipeline", json={"enabled": True}, headers=other_h)
    assert resp.status_code == 403
