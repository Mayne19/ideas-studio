import json
import pytest
from fastapi.testclient import TestClient
from tests.conftest import register_and_login, TestingSessionLocal


GOOD_CONTENT = """# Ultimate Guide to Python SEO

Python is a powerful language for building SEO tools. For example, you can automate keyword research and content analysis.

According to a 2024 study, websites using Python-based SEO tools see a 30% improvement in organic traffic.

## Getting Started

Start by installing the required packages. Use pip to install the dependencies quickly.

## Advanced Techniques

Apply these techniques to maximize your results. Here are the steps to follow:

1. Analyse your keywords
2. Optimize your meta tags
3. Build quality backlinks

## Tools and Resources

There are many useful tools available. For example, Screaming Frog and Ahrefs are industry standards.

Check out [Moz](https://moz.com) and [Ahrefs](https://ahrefs.com) for further reading.

## Conclusion

Python is an excellent choice for SEO automation. Start implementing these techniques today.
"""


def _setup(client: TestClient):
    headers = register_and_login(client)
    resp = client.post("/projects", json={"name": "SEO Blog", "domain": "seo.com", "language": "en"}, headers=headers)
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    resp = client.post(
        f"/projects/{project_id}/articles",
        json={
            "title": "Ultimate Guide to Python SEO",
            "keyword": "python seo",
            "meta_title": "Ultimate Guide to Python SEO Tools",
            "meta_description": "Discover how Python can supercharge your SEO workflow. Learn tools, techniques, and best practices for automating search optimization.",
            "slug": "ultimate-guide-python-seo",
            "content": GOOD_CONTENT,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    article_id = resp.json()["id"]
    return headers, project_id, article_id


# ── Analyzer unit tests ────────────────────────────────────────────────────────

def test_analyze_good_article(client: TestClient):
    headers, project_id, article_id = _setup(client)
    resp = client.post(f"/articles/{article_id}/analyze", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["article_id"] == article_id
    assert data["seo_score"] >= 50
    assert data["readiness_status"] in {"ready", "needs_improvement", "blocked"}
    assert isinstance(data["issues"], list)
    assert isinstance(data["suggestions"], list)


def test_analyze_missing_meta(client: TestClient):
    headers, _, project_id = register_and_login(client), None, None
    headers = register_and_login(client)
    resp = client.post("/projects", json={"name": "Blog", "domain": "x.com", "language": "en"}, headers=headers)
    project_id = resp.json()["id"]

    resp = client.post(
        f"/projects/{project_id}/articles",
        json={"title": "My Title", "keyword": "seo", "slug": "my-title", "content": "# My Title\n\nShort."},
        headers=headers,
    )
    article_id = resp.json()["id"]
    resp = client.post(f"/articles/{article_id}/analyze", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    issue_types = [i["type"] for i in data["issues"]]
    assert "missing_meta_title" in issue_types or "missing_meta_description" in issue_types
    assert data["readiness_status"] == "blocked"


def test_analyze_mock_content_blocked(client: TestClient):
    headers = register_and_login(client)
    resp = client.post("/projects", json={"name": "Blog", "domain": "x.com", "language": "en"}, headers=headers)
    project_id = resp.json()["id"]

    mock_content = "# [Mock] Title\n\n[Mock] This is placeholder content that should trigger a critical issue."
    resp = client.post(
        f"/projects/{project_id}/articles",
        json={"title": "[Mock] Title", "slug": "mock-title", "content": mock_content},
        headers=headers,
    )
    article_id = resp.json()["id"]
    resp = client.post(f"/articles/{article_id}/analyze", headers=headers)
    data = resp.json()
    issue_types = [i["type"] for i in data["issues"]]
    assert "mock_content" in issue_types
    assert data["readiness_status"] == "blocked"


def test_get_latest_analysis(client: TestClient):
    headers, project_id, article_id = _setup(client)
    client.post(f"/articles/{article_id}/analyze", headers=headers)
    resp = client.get(f"/articles/{article_id}/analysis/latest", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["article_id"] == article_id


def test_get_latest_analysis_not_found(client: TestClient):
    headers, project_id, article_id = _setup(client)
    resp = client.get(f"/articles/{article_id}/analysis/latest", headers=headers)
    assert resp.status_code == 404


def test_list_analyses(client: TestClient):
    headers, project_id, article_id = _setup(client)
    client.post(f"/articles/{article_id}/analyze", headers=headers)
    client.post(f"/articles/{article_id}/analyze", headers=headers)
    resp = client.get(f"/articles/{article_id}/analyses", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_editor_update(client: TestClient):
    headers, project_id, article_id = _setup(client)
    resp = client.patch(
        f"/articles/{article_id}/editor",
        json={"meta_title": "New Meta Title For Article", "meta_description": "New meta description that is long enough to pass validation checks for the editor update endpoint."},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] is True


def test_editor_update_viewer_blocked(client: TestClient):
    headers_owner = register_and_login(client, email="owner@test.com")
    resp = client.post("/projects", json={"name": "Blog", "domain": "x.com", "language": "en"}, headers=headers_owner)
    project_id = resp.json()["id"]

    resp = client.post(
        f"/projects/{project_id}/articles",
        json={"title": "Test", "slug": "test", "content": GOOD_CONTENT},
        headers=headers_owner,
    )
    article_id = resp.json()["id"]

    headers_viewer = register_and_login(client, email="viewer@test.com", name="Viewer")
    client.post(f"/projects/{project_id}/members", json={"email": "viewer@test.com", "role": "viewer"}, headers=headers_owner)

    resp = client.patch(f"/articles/{article_id}/editor", json={"meta_title": "X"}, headers=headers_viewer)
    assert resp.status_code == 403


def test_ready_check_can_publish(client: TestClient):
    headers, project_id, article_id = _setup(client)
    resp = client.post(f"/articles/{article_id}/ready-check", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "can_publish" in data
    assert "blocking_issues" in data
    assert isinstance(data["blocking_issues"], list)


def test_ready_check_blocked_article(client: TestClient):
    headers = register_and_login(client)
    resp = client.post("/projects", json={"name": "Blog", "domain": "x.com", "language": "en"}, headers=headers)
    project_id = resp.json()["id"]

    resp = client.post(
        f"/projects/{project_id}/articles",
        json={"title": "Short", "slug": "short"},
        headers=headers,
    )
    article_id = resp.json()["id"]
    resp = client.post(f"/articles/{article_id}/ready-check", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_publish"] is False
    assert len(data["blocking_issues"]) > 0


def test_analyze_nonmember_blocked(client: TestClient):
    headers_owner = register_and_login(client, email="owner2@test.com")
    resp = client.post("/projects", json={"name": "Blog", "domain": "x.com", "language": "en"}, headers=headers_owner)
    project_id = resp.json()["id"]
    resp = client.post(
        f"/projects/{project_id}/articles",
        json={"title": "Test", "slug": "test"},
        headers=headers_owner,
    )
    article_id = resp.json()["id"]

    headers_other = register_and_login(client, email="other@test.com", name="Other")
    resp = client.post(f"/articles/{article_id}/analyze", headers=headers_other)
    assert resp.status_code == 403


# ── Score calculation unit tests ───────────────────────────────────────────────

def test_score_formula():
    from app.services.seo_analyzer import _compute_score
    issues = [
        {"severity": "critical"},
        {"severity": "warning"},
        {"severity": "info"},
    ]
    score = _compute_score(issues)
    assert score == 100 - 20 - 10 - 3


def test_readiness_blocked_on_critical():
    from app.services.seo_analyzer import _compute_readiness
    issues = [{"severity": "critical"}, {"severity": "warning"}]
    assert _compute_readiness(issues) == "blocked"


def test_readiness_needs_improvement():
    from app.services.seo_analyzer import _compute_readiness
    issues = [{"severity": "warning"}, {"severity": "info"}]
    assert _compute_readiness(issues) == "needs_improvement"


def test_readiness_ready():
    from app.services.seo_analyzer import _compute_readiness
    issues = [{"severity": "info"}]
    assert _compute_readiness(issues) == "ready"


def test_readiness_all_clear():
    from app.services.seo_analyzer import _compute_readiness
    assert _compute_readiness([]) == "ready"
