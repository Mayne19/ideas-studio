from unittest.mock import patch, MagicMock
from tests.conftest import register_and_login


def _create_project(client, headers, name="Test Blog"):
    resp = client.post("/projects", json={"name": name}, headers=headers)
    return resp.json()


def test_create_category(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    resp = client.post(
        f"/projects/{project['id']}/categories",
        json={"name": "SEO Tips"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "SEO Tips"
    assert data["slug"] == "seo-tips"
    assert data["project_id"] == project["id"]


def test_create_category_auto_slug(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    client.post(f"/projects/{project['id']}/categories", json={"name": "Tech"}, headers=headers)
    # Second with same name → slug-2
    resp = client.post(f"/projects/{project['id']}/categories", json={"name": "Tech"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["slug"] == "tech-2"


def test_list_categories(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    client.post(f"/projects/{project['id']}/categories", json={"name": "A"}, headers=headers)
    client.post(f"/projects/{project['id']}/categories", json={"name": "B"}, headers=headers)
    resp = client.get(f"/projects/{project['id']}/categories", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_access_category_other_project_forbidden(client):
    headers1 = register_and_login(client, "owner@test.com", "pass1234", "Owner")
    headers2 = register_and_login(client, "other@test.com", "pass1234", "Other")
    project = _create_project(client, headers1)
    cat = client.post(
        f"/projects/{project['id']}/categories",
        json={"name": "Private Cat"},
        headers=headers1,
    ).json()
    resp = client.get(f"/categories/{cat['id']}", headers=headers2)
    assert resp.status_code == 403


def test_delete_category_with_article_fails(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    cat = client.post(
        f"/projects/{project['id']}/categories",
        json={"name": "Used Category"},
        headers=headers,
    ).json()
    client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "My Article", "category_id": cat["id"]},
        headers=headers,
    )
    resp = client.delete(f"/categories/{cat['id']}", headers=headers)
    assert resp.status_code == 409


def test_delete_empty_category(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    cat = client.post(
        f"/projects/{project['id']}/categories",
        json={"name": "Empty Cat"},
        headers=headers,
    ).json()
    resp = client.delete(f"/categories/{cat['id']}", headers=headers)
    assert resp.status_code == 204


def _mock_httpx_get(data: list[dict], status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = str(data)
    mock.json.return_value = data
    return mock


def test_sync_categories_imports_colors(client):
    """Blog returns a direct array with slug/name/color → all imported."""
    headers = register_and_login(client)
    project = _create_project(client, headers)
    pid = project["id"]
    # Set a domain so sync can build an API URL
    client.patch(f"/projects/{pid}", json={"domain": "www.theslash.fr"}, headers=headers)

    blog_data = [
        {"slug": "seo", "name": "SEO", "color": "#2563eb"},
        {"slug": "web-design", "name": "Web Design", "color": "#9333ea"},
    ]
    with patch("app.routers.categories.httpx.get", return_value=_mock_httpx_get(blog_data)):
        resp = client.post(f"/projects/{pid}/categories/sync", headers=headers)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    slugs = {c["slug"]: c for c in data}
    assert slugs["seo"]["color"] == "#2563eb"
    assert slugs["web-design"]["color"] == "#9333ea"
    assert resp.headers.get("X-Sync-Message") == "2 categorie(s) synchronisee(s)."


def test_sync_categories_empty_blog(client):
    """Blog returns an empty array but existing categories exist → 200 with message."""
    headers = register_and_login(client)
    project = _create_project(client, headers)
    pid = project["id"]
    client.patch(f"/projects/{pid}", json={"domain": "www.theslash.fr"}, headers=headers)
    # Have at least one existing category so we don't hit 502
    client.post(f"/projects/{pid}/categories", json={"name": "SEO", "slug": "seo"}, headers=headers)

    with patch("app.routers.categories.httpx.get", return_value=_mock_httpx_get([])):
        resp = client.post(f"/projects/{pid}/categories/sync", headers=headers)

    assert resp.status_code == 200
    assert resp.headers.get("X-Sync-Message") == "Aucune categorie detectee sur le site connecte."


def test_sync_categories_preserves_manual_color(client):
    """Existing category with a valid manual color is NOT overwritten by blog sync."""
    headers = register_and_login(client)
    project = _create_project(client, headers)
    pid = project["id"]
    client.patch(f"/projects/{pid}", json={"domain": "www.theslash.fr"}, headers=headers)

    # Create a category manually with a specific color
    client.post(
        f"/projects/{pid}/categories",
        json={"name": "SEO", "slug": "seo", "color": "#ff0000"},
        headers=headers,
    )

    blog_data = [{"slug": "seo", "name": "SEO", "color": "#2563eb"}]
    with patch("app.routers.categories.httpx.get", return_value=_mock_httpx_get(blog_data)):
        resp = client.post(f"/projects/{pid}/categories/sync", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    cat = next(c for c in data if c["slug"] == "seo")
    assert cat["color"] == "#ff0000", "Manual color should be preserved"


def test_sync_categories_all_exist(client):
    """All blog categories already present → no new categories message."""
    headers = register_and_login(client)
    project = _create_project(client, headers)
    pid = project["id"]
    client.patch(f"/projects/{pid}", json={"domain": "www.theslash.fr"}, headers=headers)

    blog_data = [{"slug": "seo", "name": "SEO", "color": "#2563eb"}]
    with patch("app.routers.categories.httpx.get", return_value=_mock_httpx_get(blog_data)):
        resp1 = client.post(f"/projects/{pid}/categories/sync", headers=headers)
    assert resp1.headers.get("X-Sync-Message") == "1 categorie(s) synchronisee(s)."

    # Second sync with same data
    with patch("app.routers.categories.httpx.get", return_value=_mock_httpx_get(blog_data)):
        resp2 = client.post(f"/projects/{pid}/categories/sync", headers=headers)

    assert resp2.status_code == 200
    assert resp2.headers.get("X-Sync-Message") == "Aucune nouvelle categorie detectee."


def test_sync_categories_follows_redirects(client):
    """Domain without www produces a 307 redirect → httpx with follow_redirects=True handles it."""
    headers = register_and_login(client)
    project = _create_project(client, headers)
    pid = project["id"]
    # Store domain WITHOUT www, exactly like theslash.fr
    client.patch(f"/projects/{pid}", json={"domain": "theslash.fr"}, headers=headers)

    blog_data = [{"slug": "seo", "name": "SEO", "color": "#2563eb"}]
    with patch("app.routers.categories.httpx.get", return_value=_mock_httpx_get(blog_data)):
        resp = client.post(f"/projects/{pid}/categories/sync", headers=headers)

    assert resp.status_code == 200
    assert resp.headers.get("X-Sync-Message") == "1 categorie(s) synchronisee(s)."
    data = resp.json()
    assert data[0]["slug"] == "seo"
