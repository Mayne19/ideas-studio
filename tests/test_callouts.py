from unittest.mock import MagicMock, patch

from tests.conftest import register_and_login


def _create_project(client, headers, name="Callout Blog"):
    resp = client.post("/projects", json={"name": name}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _mock_httpx_response(payload: dict, status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = str(payload)
    mock.json.return_value = payload
    return mock


def test_create_and_list_callout_templates(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    created = client.post(
        f"/projects/{project['id']}/callouts",
        json={
            "label": "Information",
            "style": "info",
            "default_title": "A retenir",
            "color_background": "#eff6ff",
            "color_border": "#3b82f6",
            "color_text": "#1e3a8a",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    data = created.json()
    assert data["label"] == "Information"
    assert data["slug"] == "information"
    assert data["source"] == "manual"

    listed = client.get(f"/projects/{project['id']}/callouts", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_sync_callouts_returns_clear_error_when_site_endpoint_missing(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    client.patch(f"/projects/{project['id']}", json={"domain": "theslash.fr"}, headers=headers)

    response_404 = _mock_httpx_response({}, status_code=404)
    response_404.raise_for_status.side_effect = __import__("httpx").HTTPStatusError(
        "Not Found",
        request=MagicMock(),
        response=response_404,
    )

    with patch("app.routers.callouts.httpx.get", return_value=response_404):
        resp = client.post(f"/projects/{project['id']}/callouts/sync", headers=headers)

    assert resp.status_code == 502
    assert "/api/ideas-studio/config" in resp.json()["detail"]


def test_sync_callouts_imports_templates(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)
    client.patch(f"/projects/{project['id']}", json={"domain": "theslash.fr"}, headers=headers)

    payload = {
        "callouts": [
            {
                "id": "info",
                "label": "Information",
                "defaultTitle": "A retenir",
                "className": "callout-info",
                "colors": {
                    "background": "#eff6ff",
                    "border": "#3b82f6",
                    "text": "#1e3a8a",
                },
            }
        ],
        "faq": {"enabled": True, "renderMode": "after_article"},
    }

    with patch("app.routers.callouts.httpx.get", return_value=_mock_httpx_response(payload)):
        resp = client.post(f"/projects/{project['id']}/callouts/sync", headers=headers)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["label"] == "Information"
    assert data[0]["source"] == "imported"
    assert data[0]["class_name"] == "callout-info"


def test_public_article_exposes_callouts_json(client):
    headers = register_and_login(client)
    project = _create_project(client, headers)

    template = client.post(
        f"/projects/{project['id']}/callouts",
        json={
            "label": "Information",
            "style": "info",
            "default_title": "A retenir",
            "color_background": "#eff6ff",
            "color_border": "#3b82f6",
            "color_text": "#1e3a8a",
        },
        headers=headers,
    ).json()

    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Article avec callout", "slug": "article-avec-callout"},
        headers=headers,
    ).json()

    content = f"""
    <div data-block-type="callout" data-template-id="{template['id']}" data-template-key="{template['slug']}" data-callout-label="{template['label']}" data-callout-title="A retenir" data-callout-style="info" data-color-background="#eff6ff" data-color-border="#3b82f6" data-color-text="#1e3a8a">
      <div class="callout-title" contenteditable="false">A retenir</div>
      <div class="callout-body"><p>Contenu du callout</p></div>
    </div>
    """
    autosave = client.post(
        f"/articles/{article['id']}/autosave",
        json={"content": content},
        headers=headers,
    )
    assert autosave.status_code == 200, autosave.text

    published = client.post(f"/articles/{article['id']}/publish", headers=headers)
    assert published.status_code == 200

    public = client.get(f"/api/public/projects/{project['id']}/articles/article-avec-callout")
    assert public.status_code == 200, public.text
    data = public.json()
    assert data["callouts_json"] is not None
    assert template["id"] in data["callouts_json"]
    assert "Contenu du callout" in data["callouts_json"]
