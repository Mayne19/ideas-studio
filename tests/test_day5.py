"""Day 5 tests: Performance, Recommendations, Notifications, Scheduler, Public API."""
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from tests.conftest import force_publish_article, register_and_login, TestingSessionLocal


# ── Helpers ───────────────────────────────────────────────────────────────────

def _setup_project(client: TestClient, email: str = "user@test.com") -> tuple[dict, dict]:
    headers = register_and_login(client, email=email)
    resp = client.post("/projects", json={"name": "Blog", "domain": "blog.com", "language": "fr"}, headers=headers)
    assert resp.status_code == 201
    return headers, resp.json()


def _create_article(client, headers, project_id, title="Test Article", status="draft", content=None) -> dict:
    payload = {"title": title}
    if content:
        payload["content"] = content
    resp = client.post(f"/projects/{project_id}/articles", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _publish_article(client, headers, article_id) -> dict:
    force_publish_article(article_id)
    resp = client.get(f"/articles/{article_id}", headers=headers)
    assert resp.status_code == 200
    return resp.json()


# ── Performance ───────────────────────────────────────────────────────────────

def test_performance_summary_empty(client: TestClient):
    headers, project = _setup_project(client)
    resp = client.get(f"/projects/{project['id']}/performance/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_views"] == 0
    assert data["unique_pages"] == 0
    assert data["top_pages"] == []
    assert data["trend_by_day"] == []


def test_performance_summary_with_data(client: TestClient):
    headers, project = _setup_project(client, email="perf@test.com")
    tracking_key = project["public_tracking_key"]

    client.post("/api/traffic/collect", json={
        "project_id": project["id"],
        "tracking_key": tracking_key,
        "url": "https://blog.com/article-1",
        "path": "/article-1",
    })
    client.post("/api/traffic/collect", json={
        "project_id": project["id"],
        "tracking_key": tracking_key,
        "url": "https://blog.com/article-2",
        "path": "/article-2",
    })

    resp = client.get(f"/projects/{project['id']}/performance/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_views"] == 2
    assert data["unique_pages"] == 2


def test_article_performance(client: TestClient):
    headers, project = _setup_project(client, email="art_perf@test.com")
    article = _create_article(client, headers, project["id"])
    article_id = article["id"]

    resp = client.get(f"/articles/{article_id}/performance", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["article_id"] == article_id
    assert data["views"] == 0
    assert data["referrers"] == []
    assert data["daily_views"] == []


def test_performance_articles_list(client: TestClient):
    headers, project = _setup_project(client, email="artlist@test.com")
    article = _create_article(client, headers, project["id"])
    _publish_article(client, headers, article["id"])

    resp = client.get(f"/projects/{project['id']}/performance/articles", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 1


def test_performance_requires_auth(client: TestClient):
    headers, project = _setup_project(client, email="auth_perf@test.com")
    resp = client.get(f"/projects/{project['id']}/performance/summary")
    assert resp.status_code in (401, 403)


def test_performance_nonmember_blocked(client: TestClient):
    headers_owner, project = _setup_project(client, email="owner_perf@test.com")
    headers_other = register_and_login(client, email="other_perf@test.com", name="Other")

    resp = client.get(f"/projects/{project['id']}/performance/summary", headers=headers_other)
    assert resp.status_code == 403


# ── Recommendations ───────────────────────────────────────────────────────────

def test_list_recommendations_empty(client: TestClient):
    headers, project = _setup_project(client, email="recs_empty@test.com")
    resp = client.get(f"/projects/{project['id']}/recommendations", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_review_creates_recommendations(client: TestClient):
    headers, project = _setup_project(client, email="recs_review@test.com")
    article = _create_article(client, headers, project["id"], title="SEO Article")
    _publish_article(client, headers, article["id"])

    # Backdate published_at so it's J+30 by modifying via DB
    db = TestingSessionLocal()
    try:
        from app.models.article import Article
        art = db.query(Article).filter(Article.id == article["id"]).first()
        art.published_at = datetime.now(timezone.utc) - timedelta(days=35)
        db.commit()
    finally:
        db.close()

    resp = client.post(f"/projects/{project['id']}/recommendations/review", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommendations_created"] >= 1

    recs_resp = client.get(f"/projects/{project['id']}/recommendations", headers=headers)
    assert len(recs_resp.json()) >= 1


def test_no_duplicate_recommendations(client: TestClient):
    headers, project = _setup_project(client, email="recs_dup@test.com")
    article = _create_article(client, headers, project["id"], title="Dup Test")
    _publish_article(client, headers, article["id"])

    db = TestingSessionLocal()
    try:
        from app.models.article import Article
        art = db.query(Article).filter(Article.id == article["id"]).first()
        art.published_at = datetime.now(timezone.utc) - timedelta(days=40)
        db.commit()
    finally:
        db.close()

    client.post(f"/projects/{project['id']}/recommendations/review", headers=headers)
    first_count_resp = client.get(f"/projects/{project['id']}/recommendations", headers=headers)
    first_count = len(first_count_resp.json())

    # Run again — no new pending duplicates
    client.post(f"/projects/{project['id']}/recommendations/review", headers=headers)
    second_count_resp = client.get(f"/projects/{project['id']}/recommendations", headers=headers)
    second_count = len(second_count_resp.json())

    assert second_count == first_count


def test_accept_recommendation(client: TestClient):
    headers, project = _setup_project(client, email="recs_accept@test.com")
    article = _create_article(client, headers, project["id"])
    _publish_article(client, headers, article["id"])

    # Create a recommendation directly via DB
    db = TestingSessionLocal()
    try:
        from app.models.optimization_recommendation import OptimizationRecommendation
        rec = OptimizationRecommendation(
            project_id=project["id"],
            article_id=article["id"],
            type="add_faq",
            reason="No FAQ",
            suggestion="Add FAQ",
        )
        db.add(rec)
        db.commit()
        rec_id = rec.id
    finally:
        db.close()

    resp = client.post(f"/recommendations/{rec_id}/accept", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


def test_reject_recommendation(client: TestClient):
    headers, project = _setup_project(client, email="recs_reject@test.com")
    article = _create_article(client, headers, project["id"])
    _publish_article(client, headers, article["id"])

    db = TestingSessionLocal()
    try:
        from app.models.optimization_recommendation import OptimizationRecommendation
        rec = OptimizationRecommendation(
            project_id=project["id"],
            article_id=article["id"],
            type="add_faq",
            reason="No FAQ",
            suggestion="Add FAQ",
        )
        db.add(rec)
        db.commit()
        rec_id = rec.id
    finally:
        db.close()

    resp = client.post(f"/recommendations/{rec_id}/reject", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


# ── Notifications ─────────────────────────────────────────────────────────────

def test_notifications_list_empty(client: TestClient):
    headers, project = _setup_project(client, email="notif_empty@test.com")
    resp = client.get(f"/projects/{project['id']}/notifications", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_and_list_notification(client: TestClient):
    headers, project = _setup_project(client, email="notif_list@test.com")

    db = TestingSessionLocal()
    try:
        from app.services.notification_service import create_notification
        create_notification(db, project["id"], "Test", "A test notification", level="info")
        db.commit()
    finally:
        db.close()

    resp = client.get(f"/projects/{project['id']}/notifications", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test"
    assert data[0]["read_at"] is None


def test_mark_notification_read(client: TestClient):
    headers, project = _setup_project(client, email="notif_read@test.com")

    db = TestingSessionLocal()
    try:
        from app.services.notification_service import create_notification
        n = create_notification(db, project["id"], "Test", "msg")
        db.commit()
        notif_id = n.id
    finally:
        db.close()

    resp = client.post(f"/notifications/{notif_id}/read", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["read_at"] is not None


def test_mark_all_notifications_read(client: TestClient):
    headers, project = _setup_project(client, email="notif_readall@test.com")

    db = TestingSessionLocal()
    try:
        from app.services.notification_service import create_notification
        create_notification(db, project["id"], "N1", "msg1")
        create_notification(db, project["id"], "N2", "msg2")
        db.commit()
    finally:
        db.close()

    resp = client.post(f"/projects/{project['id']}/notifications/read-all", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["marked_read"] == 2

    list_resp = client.get(f"/projects/{project['id']}/notifications", headers=headers)
    for n in list_resp.json():
        assert n["read_at"] is not None


# ── Scheduler ─────────────────────────────────────────────────────────────────

def test_daily_task_calls_ideas_and_review(client: TestClient):
    headers, project = _setup_project(client, email="sched@test.com")
    article = _create_article(client, headers, project["id"])
    _publish_article(client, headers, article["id"])

    db = TestingSessionLocal()
    try:
        from app.models.article import Article
        art = db.query(Article).filter(Article.id == article["id"]).first()
        art.published_at = datetime.now(timezone.utc) - timedelta(days=40)
        db.commit()
    finally:
        db.close()

    db = TestingSessionLocal()
    try:
        from app.services.scheduler_service import run_daily_project_tasks
        result = run_daily_project_tasks(db, project["id"])
        assert "ideas" in result
        assert "review" in result
        assert result["project_id"] == project["id"]
    finally:
        db.close()


# ── Public API stabilisation ──────────────────────────────────────────────────

def test_public_api_does_not_expose_drafts(client: TestClient):
    headers, project = _setup_project(client, email="pub_draft@test.com")
    _create_article(client, headers, project["id"], title="Draft Post")
    resp = client.get(f"/api/public/projects/{project['id']}/articles")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_public_api_does_not_expose_scheduled(client: TestClient):
    headers, project = _setup_project(client, email="pub_sched@test.com")
    article = _create_article(client, headers, project["id"], title="Scheduled Post")

    from datetime import datetime, timedelta, timezone
    future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    client.post(f"/articles/{article['id']}/schedule", json={"scheduled_at": future}, headers=headers)

    resp = client.get(f"/api/public/projects/{project['id']}/articles")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_public_api_exposes_published_only(client: TestClient):
    headers, project = _setup_project(client, email="pub_pub@test.com")
    article = _create_article(client, headers, project["id"], title="Published Post")
    _publish_article(client, headers, article["id"])
    _create_article(client, headers, project["id"], title="Draft Post 2")

    resp = client.get(f"/api/public/projects/{project['id']}/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Published Post"


def test_public_api_no_secret_key_exposed(client: TestClient):
    headers, project = _setup_project(client, email="pub_secret@test.com")
    article = _create_article(client, headers, project["id"], title="Article")
    _publish_article(client, headers, article["id"])

    resp = client.get(f"/api/public/projects/{project['id']}/articles")
    body = resp.text
    assert "secret_api_key" not in body
    assert "password" not in body.lower()
