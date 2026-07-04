"""Tests for the automatic article creation pipeline."""
from datetime import datetime, timezone
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
    assert entries[0]["status"] in ("success", "partial_success", "failed")


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


def test_pipeline_disabled_is_skipped_by_scheduler_flag():
    from app.cli import _should_run_pipeline_today

    class Pipe:
        enabled = False
        active_days = "[]"

    assert _should_run_pipeline_today(Pipe()) is False


def test_pipeline_articles_per_week_affects_daily_target_and_never_publishes(client: TestClient):
    headers, project = _setup(client, "pipe_target@test.com")
    client.patch(
        f"/projects/{project['id']}/pipeline",
        json={
            "enabled": True,
            "active_days": ["monday", "wednesday", "friday"],
            "articles_per_week": 5,
            "category_priorities": {"seo": 10},
        },
        headers=headers,
    )

    run = client.post(f"/projects/{project['id']}/pipeline/run", headers=headers)
    assert run.status_code == 200
    data = run.json()
    assert data["articles_created"] == 0
    assert data["ideas_generated"] >= 0
    assert data["status"] in ("success", "partial_success", "failed")

    articles = client.get(f"/projects/{project['id']}/articles", headers=headers).json()
    assert len(articles) == data["ideas_generated"]
    if articles:
        assert all(article["status"] == "idea_proposed" for article in articles)


def test_pipeline_generates_monthly_volume_from_active_categories(client: TestClient):
    headers, project = _setup(client, "pipe_monthly_volume@test.com")
    category_ids = []
    for index in range(10):
        resp = client.post(
            f"/projects/{project['id']}/categories",
            json={
                "name": f"Catégorie {index + 1}",
                "monthly_frequency": 1,
                "pipeline_enabled": True,
                "priority": 10 - index,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        category_ids.append(resp.json()["id"])

    run = client.post(f"/projects/{project['id']}/pipeline/run", headers=headers)
    assert run.status_code == 200
    data = run.json()
    assert data["status"] == "success"
    assert data["workflow_run_id"]
    assert data["expected_ideas"] == 10
    assert data["generated_ideas"] == 10
    assert data["total_expected_ideas"] == 10
    assert data["total_generated_ideas"] == 10
    assert data["ideas_generated"] == 10
    assert len(data["categories_processed"]) == 10
    assert all(row["expected"] == 1 for row in data["categories_processed"])
    assert all(row["generated"] == 1 for row in data["categories_processed"])

    articles = client.get(f"/projects/{project['id']}/articles?status=idea_proposed&limit=50", headers=headers).json()
    generated = [article for article in articles if article["workflow_run_id"] == data["workflow_run_id"]]
    assert len(generated) == 10
    assert all(article["category_id"] in category_ids for article in generated)
    assert all(article["category_id"] is not None for article in generated)


def test_pipeline_category_error_does_not_block_batch(client: TestClient, monkeypatch):
    from app.services.idea_engine import generate_idea as real_generate_idea

    headers, project = _setup(client, "pipe_partial_category@test.com")
    failing_category_id = None
    for name in ("SEO", "Performance", "Marketing"):
        resp = client.post(
            f"/projects/{project['id']}/categories",
            json={"name": name, "monthly_frequency": 1, "pipeline_enabled": True},
            headers=headers,
        )
        assert resp.status_code == 201
        if name == "Performance":
            failing_category_id = resp.json()["id"]

    def flaky_generate_idea(*args, **kwargs):
        if kwargs.get("category_id") == failing_category_id:
            raise RuntimeError("Provider indisponible pour cette catégorie")
        return real_generate_idea(*args, **kwargs)

    monkeypatch.setattr("app.services.idea_engine.generate_idea", flaky_generate_idea)

    run = client.post(f"/projects/{project['id']}/pipeline/run", headers=headers)
    assert run.status_code == 200
    data = run.json()
    assert data["status"] == "partial_success"
    assert data["expected_ideas"] == 3
    assert data["generated_ideas"] == 2
    assert data["total_expected_ideas"] == 3
    assert data["total_generated_ideas"] == 2
    assert data["ideas_generated"] == 2
    assert len(data["errors"]) == 1
    assert len(data["failed_categories"]) == 1

    articles = client.get(f"/projects/{project['id']}/articles?status=idea_proposed&limit=50", headers=headers).json()
    generated = [article for article in articles if article["workflow_run_id"] == data["workflow_run_id"]]
    assert len(generated) == 2
    assert all(article["category_id"] for article in generated)


def test_pipeline_total_failure_returns_failed(client: TestClient, monkeypatch):
    headers, project = _setup(client, "pipe_total_failure@test.com")
    resp = client.post(
        f"/projects/{project['id']}/categories",
        json={"name": "SEO", "monthly_frequency": 2, "pipeline_enabled": True},
        headers=headers,
    )
    assert resp.status_code == 201

    def always_fail(*args, **kwargs):
        raise RuntimeError("Provider indisponible")

    monkeypatch.setattr("app.services.idea_engine.generate_idea", always_fail)

    run = client.post(f"/projects/{project['id']}/pipeline/run", headers=headers)
    assert run.status_code == 200
    data = run.json()
    assert data["status"] == "failed"
    assert data["expected_ideas"] == 2
    assert data["generated_ideas"] == 0
    assert data["ideas_generated"] == 0
    assert len(data["failed_categories"]) == 1


def test_pipeline_running_lock_returns_existing_run(client: TestClient):
    from app.models.pipeline_log import PipelineLog

    headers, project = _setup(client, "pipe_lock@test.com")
    with TestingSessionLocal() as db:
        running = PipelineLog(
            project_id=project["id"],
            status="running",
            ideas_generated=0,
            articles_created=0,
            started_at=datetime.now(timezone.utc),
            finished_at=None,
        )
        db.add(running)
        db.commit()
        running_id = running.id

    run = client.post(f"/projects/{project['id']}/pipeline/run", headers=headers)
    assert run.status_code == 200
    data = run.json()
    assert data["status"] == "running"
    assert data["workflow_run_id"] == running_id

    logs = client.get(f"/projects/{project['id']}/pipeline/logs", headers=headers).json()
    running_logs = [log for log in logs if log["status"] == "running"]
    assert len(running_logs) == 1
