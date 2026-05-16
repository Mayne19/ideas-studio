from tests.conftest import register_and_login


def _setup(client):
    headers = register_and_login(client)
    project = client.post("/projects", json={"name": "Blog"}, headers=headers).json()
    return headers, project


def test_create_article(client):
    headers, project = _setup(client)
    resp = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "My First Post"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My First Post"
    assert data["slug"] == "my-first-post"
    assert data["status"] == "draft"
    assert data["project_id"] == project["id"]


def test_create_article_auto_slug_unique(client):
    headers, project = _setup(client)
    client.post(f"/projects/{project['id']}/articles", json={"title": "Hello"}, headers=headers)
    resp = client.post(f"/projects/{project['id']}/articles", json={"title": "Hello"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["slug"] == "hello-2"


def test_word_count_calculated(client):
    headers, project = _setup(client)
    resp = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Post", "content": "one two three four five"},
        headers=headers,
    )
    assert resp.json()["word_count"] == 5


def test_publish_article(client):
    headers, project = _setup(client)
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "To Publish"},
        headers=headers,
    ).json()
    resp = client.post(f"/articles/{article['id']}/publish", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "published"
    assert data["published_at"] is not None


def test_unpublish_article(client):
    headers, project = _setup(client)
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Unpublish Me"},
        headers=headers,
    ).json()
    client.post(f"/articles/{article['id']}/publish", headers=headers)
    resp = client.post(f"/articles/{article['id']}/unpublish", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


def test_public_api_returns_published_only(client):
    headers, project = _setup(client)
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Public Post", "content": "Hello world"},
        headers=headers,
    ).json()
    client.post(f"/articles/{article['id']}/publish", headers=headers)
    # Also create a draft
    client.post(f"/projects/{project['id']}/articles", json={"title": "Draft"}, headers=headers)

    resp = client.get(f"/api/public/projects/{project['id']}/articles")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["title"] == "Public Post"


def test_public_api_does_not_return_draft(client):
    headers, project = _setup(client)
    client.post(f"/projects/{project['id']}/articles", json={"title": "Secret Draft"}, headers=headers)
    resp = client.get(f"/api/public/projects/{project['id']}/articles")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_public_api_get_by_slug(client):
    headers, project = _setup(client)
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Slug Post"},
        headers=headers,
    ).json()
    client.post(f"/articles/{article['id']}/publish", headers=headers)
    resp = client.get(f"/api/public/projects/{project['id']}/articles/slug-post")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "slug-post"


def test_publish_preserves_published_at_on_republish(client):
    headers, project = _setup(client)
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Stable Publish Date"},
        headers=headers,
    ).json()

    first = client.post(f"/articles/{article['id']}/publish", headers=headers)
    assert first.status_code == 200
    first_published_at = first.json()["published_at"]

    second = client.post(f"/articles/{article['id']}/publish", headers=headers)
    assert second.status_code == 200
    assert second.json()["published_at"] == first_published_at


def test_autosave_persists_manual_reading_time_and_keyword(client):
    headers, project = _setup(client)
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Manual Reading Time", "content": "hello world"},
        headers=headers,
    ).json()

    autosave = client.post(
        f"/articles/{article['id']}/autosave",
        json={"reading_time_minutes": 9, "author_name": "Marie", "keyword": "landing page"},
        headers=headers,
    )
    assert autosave.status_code == 200

    editor = client.get(f"/articles/{article['id']}/editor", headers=headers)
    assert editor.status_code == 200
    data = editor.json()
    assert data["reading_time_minutes"] == 9
    assert data["author_name"] == "Marie"
    assert data["keyword"] == "landing page"


def test_public_api_draft_not_found_by_slug(client):
    headers, project = _setup(client)
    client.post(f"/projects/{project['id']}/articles", json={"title": "Draft Article"}, headers=headers)
    resp = client.get(f"/api/public/projects/{project['id']}/articles/draft-article")
    assert resp.status_code == 404


def test_viewer_cannot_edit_article(client):
    # owner creates project and article
    headers_owner = register_and_login(client, "owner@test.com", "pass1234", "Owner")
    project = client.post("/projects", json={"name": "Blog"}, headers=headers_owner).json()
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Post"},
        headers=headers_owner,
    ).json()
    # Register a second user
    register_and_login(client, "viewer@test.com", "pass1234", "Viewer")
    # viewer user has no membership — treated as 403
    headers_viewer = register_and_login(client, "viewer@test.com", "pass1234", "Viewer")
    resp = client.patch(f"/articles/{article['id']}", json={"title": "Hacked"}, headers=headers_viewer)
    assert resp.status_code == 403
