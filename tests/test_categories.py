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
