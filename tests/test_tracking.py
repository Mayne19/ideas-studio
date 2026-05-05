from tests.conftest import register_and_login


def _setup(client):
    headers = register_and_login(client)
    project = client.post("/projects", json={"name": "Blog", "domain": "myblog.com"}, headers=headers).json()
    return headers, project


def test_traffic_collect_valid_key(client):
    headers, project = _setup(client)
    resp = client.post("/api/traffic/collect", json={
        "project_id": project["id"],
        "tracking_key": project["public_tracking_key"],
        "url": "https://myblog.com/post/1",
        "path": "/post/1",
        "referrer": "https://google.com",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/120",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_traffic_collect_invalid_key(client):
    headers, project = _setup(client)
    resp = client.post("/api/traffic/collect", json={
        "project_id": project["id"],
        "tracking_key": "wrong-key-12345",
        "url": "https://myblog.com/post/1",
        "path": "/post/1",
    })
    assert resp.status_code == 403


def test_traffic_collect_unknown_project(client):
    resp = client.post("/api/traffic/collect", json={
        "project_id": "does-not-exist",
        "tracking_key": "some-key",
        "url": "https://example.com",
    })
    assert resp.status_code == 404


def test_project_last_seen_at_updated(client):
    headers, project = _setup(client)
    assert project["last_seen_at"] is None

    client.post("/api/traffic/collect", json={
        "project_id": project["id"],
        "tracking_key": project["public_tracking_key"],
        "url": "https://myblog.com/",
        "path": "/",
    })

    updated = client.get(f"/projects/{project['id']}", headers=headers).json()
    assert updated["last_seen_at"] is not None


def test_project_status_becomes_connected(client):
    headers, project = _setup(client)
    assert project["status"] == "not_connected"

    client.post("/api/traffic/collect", json={
        "project_id": project["id"],
        "tracking_key": project["public_tracking_key"],
        "url": "https://myblog.com/",
    })

    updated = client.get(f"/projects/{project['id']}", headers=headers).json()
    assert updated["status"] == "connected"


def test_traffic_js_served(client):
    resp = client.get("/traffic.js")
    assert resp.status_code == 200
    assert "application/javascript" in resp.headers["content-type"]
    assert "data-project-id" in resp.text
    assert "data-tracking-key" in resp.text
    assert "/api/traffic/collect" in resp.text
