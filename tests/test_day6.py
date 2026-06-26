"""Day 6 — Editor Backend Hardening tests."""
from fastapi.testclient import TestClient
from tests.conftest import force_publish_article, mark_article_ready_for_publication, register_and_login, TestingSessionLocal


# ── Helpers ───────────────────────────────────────────────────────────────────

def _setup(client: TestClient, email: str = "d6owner@test.com") -> tuple[dict, dict]:
    headers = register_and_login(client, email=email)
    resp = client.post("/projects", json={"name": "Blog", "domain": "blog.com", "language": "fr"}, headers=headers)
    assert resp.status_code == 201
    return headers, resp.json()


def _article(client, headers, project_id, title="My Article", content=None) -> dict:
    payload = {"title": title}
    if content:
        payload["content"] = content
    resp = client.post(f"/projects/{project_id}/articles", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _add_member(client, headers, project_id, email, role) -> str:
    user_resp = client.post("/auth/register", json={"name": role.title(), "email": email, "password": "pass1234"})
    assert user_resp.status_code == 201
    user_id = user_resp.json()["id"]
    client.post(f"/projects/{project_id}/members", json={"user_id": user_id, "role": role}, headers=headers)
    return user_id


# ── 1. GET /editor ────────────────────────────────────────────────────────────

def test_get_editor_data(client: TestClient):
    headers, project = _setup(client, "e_get@test.com")
    article = _article(client, headers, project["id"], content="Hello world content")

    resp = client.get(f"/articles/{article['id']}/editor", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == article["id"]
    assert data["title"] == "My Article"
    assert data["content"] == "Hello world content"
    assert "word_count" in data
    assert "seo_score" in data
    assert "latest_analysis" in data
    assert "content_blocks_json" in data


# ── 2–3. PATCH /editor ────────────────────────────────────────────────────────

def test_editor_saves_content_blocks_json(client: TestClient):
    headers, project = _setup(client, "e_cb@test.com")
    article = _article(client, headers, project["id"])

    blocks = '[{"type":"paragraph","content":"hello"}]'
    resp = client.patch(
        f"/articles/{article['id']}/editor",
        json={"content_blocks_json": blocks},
        headers=headers,
    )
    assert resp.status_code == 200

    resp2 = client.get(f"/articles/{article['id']}/editor", headers=headers)
    assert resp2.json()["content_blocks_json"] == blocks


def test_editor_patch_creates_version(client: TestClient):
    headers, project = _setup(client, "e_ver@test.com")
    article = _article(client, headers, project["id"], content="Original content")

    client.patch(
        f"/articles/{article['id']}/editor",
        json={"content": "Updated content"},
        headers=headers,
    )

    resp = client.get(f"/articles/{article['id']}/versions", headers=headers)
    assert resp.status_code == 200
    versions = resp.json()
    assert len(versions) >= 1
    assert versions[0]["version_type"] == "manual"


# ── 4–6. POST /autosave ───────────────────────────────────────────────────────

def test_autosave_no_publish(client: TestClient):
    headers, project = _setup(client, "e_as@test.com")
    article = _article(client, headers, project["id"])

    resp = client.post(
        f"/articles/{article['id']}/autosave",
        json={"content": "Draft content saved"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["updated"] is True

    # status must NOT be published
    article_resp = client.get(f"/articles/{article['id']}", headers=headers)
    assert article_resp.json()["status"] != "published"


def test_autosave_viewer_blocked(client: TestClient):
    headers, project = _setup(client, "e_asv@test.com")
    article = _article(client, headers, project["id"])
    _add_member(client, headers, project["id"], "e_asv_viewer@test.com", "viewer")
    viewer_headers = register_and_login(client, email="e_asv_viewer@test.com")

    resp = client.post(
        f"/articles/{article['id']}/autosave",
        json={"content": "attempt"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


def test_autosave_nonmember_blocked(client: TestClient):
    headers, project = _setup(client, "e_asnm@test.com")
    article = _article(client, headers, project["id"])
    other_headers = register_and_login(client, email="e_asnm_other@test.com", name="Other")

    resp = client.post(
        f"/articles/{article['id']}/autosave",
        json={"content": "attempt"},
        headers=other_headers,
    )
    assert resp.status_code == 403


# ── 7–11. Versions ────────────────────────────────────────────────────────────

def test_list_versions(client: TestClient):
    headers, project = _setup(client, "v_list@test.com")
    article = _article(client, headers, project["id"], content="v1 content")

    client.patch(f"/articles/{article['id']}/editor", json={"content": "v2 content"}, headers=headers)
    client.patch(f"/articles/{article['id']}/editor", json={"content": "v3 content"}, headers=headers)

    resp = client.get(f"/articles/{article['id']}/versions", headers=headers)
    assert resp.status_code == 200
    versions = resp.json()
    assert len(versions) == 2
    assert versions[0]["version_number"] > versions[1]["version_number"]


def test_restore_version(client: TestClient):
    headers, project = _setup(client, "v_rest@test.com")
    # Article starts with "original"; PATCH to "changed" → version v1 captures "original"
    article = _article(client, headers, project["id"], content="original")

    client.patch(f"/articles/{article['id']}/editor", json={"content": "changed"}, headers=headers)
    versions_resp = client.get(f"/articles/{article['id']}/versions", headers=headers)
    version_id = versions_resp.json()[0]["id"]  # v1, content="original"

    restore_resp = client.post(
        f"/articles/{article['id']}/versions/{version_id}/restore",
        headers=headers,
    )
    assert restore_resp.status_code == 200
    # Restoring v1 (content="original") brings article back to "original"
    assert restore_resp.json()["content"] == "original"


def test_restore_creates_restore_version(client: TestClient):
    headers, project = _setup(client, "v_rv@test.com")
    article = _article(client, headers, project["id"], content="initial")

    client.patch(f"/articles/{article['id']}/editor", json={"content": "edited"}, headers=headers)
    versions_before = client.get(f"/articles/{article['id']}/versions", headers=headers).json()
    version_id = versions_before[0]["id"]

    client.post(f"/articles/{article['id']}/versions/{version_id}/restore", headers=headers)

    versions_after = client.get(f"/articles/{article['id']}/versions", headers=headers).json()
    assert len(versions_after) > len(versions_before)
    types = [v["version_type"] for v in versions_after]
    assert "restore" in types


def test_restore_viewer_blocked(client: TestClient):
    headers, project = _setup(client, "v_vb@test.com")
    article = _article(client, headers, project["id"], content="c")
    _add_member(client, headers, project["id"], "v_vb_viewer@test.com", "viewer")

    client.patch(f"/articles/{article['id']}/editor", json={"content": "edited"}, headers=headers)
    version_id = client.get(f"/articles/{article['id']}/versions", headers=headers).json()[0]["id"]

    viewer_headers = register_and_login(client, email="v_vb_viewer@test.com")
    resp = client.post(f"/articles/{article['id']}/versions/{version_id}/restore", headers=viewer_headers)
    assert resp.status_code == 403


def test_restore_nonmember_blocked(client: TestClient):
    headers, project = _setup(client, "v_nb@test.com")
    article = _article(client, headers, project["id"], content="c")

    client.patch(f"/articles/{article['id']}/editor", json={"content": "edited"}, headers=headers)
    version_id = client.get(f"/articles/{article['id']}/versions", headers=headers).json()[0]["id"]

    other_headers = register_and_login(client, email="v_nb_other@test.com", name="Other")
    resp = client.post(f"/articles/{article['id']}/versions/{version_id}/restore", headers=other_headers)
    assert resp.status_code == 403


# ── 12–14. Preview ────────────────────────────────────────────────────────────

def test_preview_draft_with_auth(client: TestClient):
    headers, project = _setup(client, "p_auth@test.com")
    article = _article(client, headers, project["id"], content="Draft preview content")

    resp = client.get(f"/articles/{article['id']}/preview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "Draft preview content"
    assert data["status"] == "draft"


def test_preview_without_auth(client: TestClient):
    headers, project = _setup(client, "p_noauth@test.com")
    article = _article(client, headers, project["id"])

    resp = client.get(f"/articles/{article['id']}/preview")
    assert resp.status_code in (401, 403)


def test_preview_nonmember_blocked(client: TestClient):
    headers, project = _setup(client, "p_nm@test.com")
    article = _article(client, headers, project["id"])
    other_headers = register_and_login(client, email="p_nm_other@test.com", name="Other")

    resp = client.get(f"/articles/{article['id']}/preview", headers=other_headers)
    assert resp.status_code == 403


# ── 15–20. Media ──────────────────────────────────────────────────────────────

def test_create_media_url(client: TestClient):
    headers, project = _setup(client, "m_cr@test.com")

    resp = client.post(
        f"/projects/{project['id']}/media/upload-json",
        json={
            "url": "https://example.com/image.jpg",
            "filename": "image.jpg",
            "mime_type": "image/jpeg",
            "size": 12345,
            "alt_text": "A test image",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://example.com/image.jpg"
    assert data["alt_text"] == "A test image"
    assert data["project_id"] == project["id"]


def test_upload_media_file(client: TestClient):
    headers, project = _setup(client, "m_up@test.com")
    import io
    file_content = b"fake-image-content"
    resp = client.post(
        f"/projects/{project['id']}/media/upload",
        files={"file": ("test.png", io.BytesIO(file_content), "image/png")},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"].startswith("/uploads/"), "url should be a relative path"
    assert data["url"].endswith(".png"), "url should preserve extension"
    assert data["public_url"] is not None
    assert data["public_url"].startswith("http"), "public_url should be absolute"
    assert data["url"] in data["public_url"], "public_url should contain the relative url"
    assert data["filename"] == "test.png"
    assert data["mime_type"] == "image/png"
    assert data["size"] == len(file_content)


def test_list_media(client: TestClient):
    headers, project = _setup(client, "m_list@test.com")

    client.post(f"/projects/{project['id']}/media/upload-json",
                json={"url": "https://cdn.com/a.jpg", "filename": "a.jpg"}, headers=headers)
    client.post(f"/projects/{project['id']}/media/upload-json",
                json={"url": "https://cdn.com/b.jpg", "filename": "b.jpg"}, headers=headers)

    resp = client.get(f"/projects/{project['id']}/media", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_patch_media_alt_text(client: TestClient):
    headers, project = _setup(client, "m_patch@test.com")

    create_resp = client.post(
        f"/projects/{project['id']}/media/upload-json",
        json={"url": "https://cdn.com/img.jpg", "filename": "img.jpg"},
        headers=headers,
    )
    media_id = create_resp.json()["id"]

    resp = client.patch(f"/media/{media_id}", json={"alt_text": "Updated alt"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["alt_text"] == "Updated alt"


def test_delete_media(client: TestClient):
    headers, project = _setup(client, "m_del@test.com")

    create_resp = client.post(
        f"/projects/{project['id']}/media/upload-json",
        json={"url": "https://cdn.com/del.jpg", "filename": "del.jpg"},
        headers=headers,
    )
    media_id = create_resp.json()["id"]

    resp = client.delete(f"/media/{media_id}", headers=headers)
    assert resp.status_code == 200

    list_resp = client.get(f"/projects/{project['id']}/media", headers=headers)
    assert len(list_resp.json()) == 0


def test_media_viewer_blocked(client: TestClient):
    headers, project = _setup(client, "m_vb@test.com")
    _add_member(client, headers, project["id"], "m_vb_viewer@test.com", "viewer")
    viewer_headers = register_and_login(client, email="m_vb_viewer@test.com")

    resp = client.post(
        f"/projects/{project['id']}/media/upload-json",
        json={"url": "https://cdn.com/x.jpg", "filename": "x.jpg"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


def test_media_nonmember_blocked(client: TestClient):
    headers, project = _setup(client, "m_nm@test.com")
    other_headers = register_and_login(client, email="m_nm_other@test.com", name="Other")

    resp = client.post(
        f"/projects/{project['id']}/media/upload-json",
        json={"url": "https://cdn.com/y.jpg", "filename": "y.jpg"},
        headers=other_headers,
    )
    assert resp.status_code == 403


# ── 21–24. Publishing workflow ────────────────────────────────────────────────

def test_mark_ready(client: TestClient):
    headers, project = _setup(client, "pub_mr@test.com")
    article = _article(client, headers, project["id"])

    resp = client.post(f"/articles/{article['id']}/mark-ready", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready_to_publish"


def test_archive(client: TestClient):
    headers, project = _setup(client, "pub_arch@test.com")
    article = _article(client, headers, project["id"])

    resp = client.post(f"/articles/{article['id']}/archive", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


def test_archived_not_in_public_api(client: TestClient):
    headers, project = _setup(client, "pub_arc_pub@test.com")
    article = _article(client, headers, project["id"], title="To Archive")
    force_publish_article(article["id"])
    client.post(f"/articles/{article['id']}/archive", headers=headers)

    resp = client.get(f"/api/public/projects/{project['id']}/articles")
    assert resp.status_code == 200
    assert all(a["title"] != "To Archive" for a in resp.json())


def test_unpublished_not_in_public_api(client: TestClient):
    headers, project = _setup(client, "pub_unp@test.com")
    article = _article(client, headers, project["id"], title="Will Unpublish")
    force_publish_article(article["id"])

    visible = client.get(f"/api/public/projects/{project['id']}/articles").json()
    assert len(visible) == 1

    client.post(f"/articles/{article['id']}/unpublish", headers=headers)

    invisible = client.get(f"/api/public/projects/{project['id']}/articles").json()
    assert len(invisible) == 0


# ── 25–28. Published article draft/publish separation ─────────────────────────

def test_publish_snapshots_content_to_published_fields(client: TestClient):
    headers, project = _setup(client, "pub_snap@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Snapshot Test", "content": "<p>Draft content</p>"},
        headers=headers,
    ).json()

    force_publish_article(article["id"])

    editor = client.get(f"/articles/{article['id']}/editor", headers=headers).json()
    public = client.get(f"/api/public/projects/{project['id']}/articles/snapshot-test").json()
    assert public["content"] == "<p>Draft content</p>"

    autosave = client.post(
        f"/articles/{article['id']}/autosave",
        json={"content": "<p>Updated draft content</p>"},
        headers=headers,
    )
    assert autosave.status_code == 200

    editor_after = client.get(f"/articles/{article['id']}/editor", headers=headers).json()
    assert editor_after["content"] == "<p>Updated draft content</p>"

    public_after = client.get(f"/api/public/projects/{project['id']}/articles/snapshot-test").json()
    assert public_after["content"] == "<p>Draft content</p>", "Public API should still show published snapshot"

    promote = client.post(f"/articles/{article['id']}/promote", headers=headers)
    assert promote.status_code == 200

    public_promoted = client.get(f"/api/public/projects/{project['id']}/articles/snapshot-test").json()
    assert public_promoted["content"] == "<p>Updated draft content</p>"


def test_promote_requires_published_article(client: TestClient):
    headers, project = _setup(client, "pub_prq@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Draft Only"},
        headers=headers,
    ).json()

    resp = client.post(f"/articles/{article['id']}/promote", headers=headers)
    assert resp.status_code == 400


def test_promote_requires_manage_role(client: TestClient):
    headers, project = _setup(client, "pub_prm@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Promote Role Test"},
        headers=headers,
    ).json()
    force_publish_article(article["id"])

    _add_member(client, headers, project["id"], "pub_prm_viewer@test.com", "viewer")
    viewer_headers = register_and_login(client, email="pub_prm_viewer@test.com")

    resp = client.post(f"/articles/{article['id']}/promote", headers=viewer_headers)
    assert resp.status_code == 403


def test_autosave_does_not_modify_published_content(client: TestClient):
    headers, project = _setup(client, "pub_aut@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Autosave Published", "content": "<p>Original public content</p>"},
        headers=headers,
    ).json()
    force_publish_article(article["id"])

    for i in range(3):
        client.post(
            f"/articles/{article['id']}/autosave",
            json={"content": f"<p>Draft change {i}</p>"},
            headers=headers,
        )

    public = client.get(f"/api/public/projects/{project['id']}/articles/autosave-published").json()
    assert public["content"] == "<p>Original public content</p>"


# ── 29–33. Callout colors (data-callout-color-*) ─────────────────────────────

def test_callout_manual_colors_in_callouts_json(client: TestClient):
    headers, project = _setup(client, "ccol@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Callout Colors"},
        headers=headers,
    ).json()

    content = (
        '<div data-block-type="callout" data-callout-style="info" data-callout-source="manual" '
        'data-callout-color-background="#f0fdf4" data-callout-color-border="#10b981" '
        'data-callout-color-text="#065f46">'
        '<div class="callout-body"><p>Green callout</p></div></div>'
    )
    client.post(
        f"/articles/{article['id']}/autosave",
        json={"content": content},
        headers=headers,
    )

    editor = client.get(f"/articles/{article['id']}/editor", headers=headers).json()
    callouts = __import__("json").loads(editor["callouts_json"])
    assert len(callouts) == 1
    colors = callouts[0]["colors"]
    assert colors["background"] == "#f0fdf4"
    assert colors["border"] == "#10b981"
    assert colors["text"] == "#065f46"
    assert callouts[0]["source"] == "manual"


def test_callout_legacy_color_attrs_still_parsed(client: TestClient):
    headers, project = _setup(client, "ccol_leg@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Legacy Callout Colors"},
        headers=headers,
    ).json()

    content = (
        '<div data-block-type="callout" data-callout-style="info" data-callout-source="manual" '
        'data-color-background="#fef2f2" data-color-border="#ef4444" data-color-text="#991b1b">'
        '<div class="callout-body"><p>Red callout</p></div></div>'
    )
    client.post(
        f"/articles/{article['id']}/autosave",
        json={"content": content},
        headers=headers,
    )

    editor = client.get(f"/articles/{article['id']}/editor", headers=headers).json()
    callouts = __import__("json").loads(editor["callouts_json"])
    assert len(callouts) == 1
    colors = callouts[0]["colors"]
    assert colors["background"] == "#fef2f2"
    assert colors["border"] == "#ef4444"
    assert colors["text"] == "#991b1b"
    assert callouts[0]["source"] == "manual"


# ── 34–37. Editor API has_draft_changes ─────────────────────────────────────

def test_editor_returns_has_draft_changes_for_published(client: TestClient):
    headers, project = _setup(client, "hdc1@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "HDC Test", "content": "<p>Original</p>"},
        headers=headers,
    ).json()

    force_publish_article(article["id"])
    editor = client.get(f"/articles/{article['id']}/editor", headers=headers).json()
    assert "has_draft_changes" in editor
    assert editor["has_draft_changes"] is False


def test_autosave_sets_has_draft_changes_true(client: TestClient):
    headers, project = _setup(client, "hdc2@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "HDC Autosave", "content": "<p>Original</p>"},
        headers=headers,
    ).json()

    force_publish_article(article["id"])

    client.post(
        f"/articles/{article['id']}/autosave",
        json={"content": "<p>Updated draft</p>"},
        headers=headers,
    )

    editor = client.get(f"/articles/{article['id']}/editor", headers=headers).json()
    assert editor["has_draft_changes"] is True


def test_promote_resets_has_draft_changes(client: TestClient):
    headers, project = _setup(client, "hdc3@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "HDC Promote", "content": "<p>Original</p>"},
        headers=headers,
    ).json()

    force_publish_article(article["id"])

    client.post(
        f"/articles/{article['id']}/autosave",
        json={"content": "<p>Updated draft</p>"},
        headers=headers,
    )

    client.post(f"/articles/{article['id']}/promote", headers=headers)

    editor = client.get(f"/articles/{article['id']}/editor", headers=headers).json()
    assert editor["has_draft_changes"] is False


def test_editor_has_draft_changes_fields(client: TestClient):
    headers, project = _setup(client, "hdc4@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "HDC Fields", "content": "<p>Original</p>"},
        headers=headers,
    ).json()

    force_publish_article(article["id"])
    editor = client.get(f"/articles/{article['id']}/editor", headers=headers).json()

    assert "published_content" in editor
    assert "published_title" in editor
    assert "published_excerpt" in editor
    assert "published_meta_description" in editor
    assert "published_cover_image_url" in editor
    assert "published_faq_json" in editor
    assert "published_callouts_json" in editor
    assert editor["published_content"] == "<p>Original</p>"


# ── 38–42. Media library + promote verification ────────────────────────────

def test_upload_adds_to_media_library(client: TestClient):
    headers, project = _setup(client, "mlib_up@test.com")
    import io
    file_content = b"media-lib-image"
    upload_resp = client.post(
        f"/projects/{project['id']}/media/upload",
        files={"file": ("lib.png", io.BytesIO(file_content), "image/png")},
        headers=headers,
    )
    assert upload_resp.status_code == 201

    list_resp = client.get(f"/projects/{project['id']}/media", headers=headers)
    assert list_resp.status_code == 200
    assets = list_resp.json()
    assert len(assets) == 1
    assert assets[0]["filename"] == "lib.png"


def test_promote_updates_published_content_public_api(client: TestClient):
    headers, project = _setup(client, "mpro_pub@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Promote Public", "content": "<p>Original public</p>"},
        headers=headers,
    ).json()

    force_publish_article(article["id"])

    public_before = client.get(f"/api/public/projects/{project['id']}/articles/promote-public").json()
    assert public_before["content"] == "<p>Original public</p>"

    autosave_resp = client.post(
        f"/articles/{article['id']}/autosave",
        json={"content": "<p>Updated via promote</p>"},
        headers=headers,
    )
    assert autosave_resp.status_code == 200

    promote_resp = client.post(f"/articles/{article['id']}/promote", headers=headers)
    assert promote_resp.status_code == 200

    public_after = client.get(f"/api/public/projects/{project['id']}/articles/promote-public").json()
    assert public_after["content"] == "<p>Updated via promote</p>", \
        "Public API must reflect promoted content"


def test_promote_updates_published_fields_directly(client: TestClient):
    headers, project = _setup(client, "mpro_dir@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Promote Direct", "content": "<p>Before promote</p>"},
        headers=headers,
    ).json()

    force_publish_article(article["id"])

    client.post(
        f"/articles/{article['id']}/autosave",
        json={"content": "<p>After promote</p>"},
        headers=headers,
    )
    promote_resp = client.post(f"/articles/{article['id']}/promote", headers=headers)
    assert promote_resp.status_code == 200

    editor = client.get(f"/articles/{article['id']}/editor", headers=headers).json()
    assert editor["published_content"] == "<p>After promote</p>"
    assert editor["has_draft_changes"] is False


def test_autosave_alone_does_not_change_public_callouts(client: TestClient):
    headers, project = _setup(client, "mpro_cl@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Callout Promote", "content": "<p>Initial</p>"},
        headers=headers,
    ).json()

    content_with_callout = (
        '<div data-block-type="callout" data-callout-style="info" data-callout-source="manual" '
        'data-callout-color-background="#f0fdf4">'
        '<div class="callout-body"><p>Test</p></div></div>'
    )

    force_publish_article(article["id"])
    client.post(
        f"/articles/{article['id']}/autosave",
        json={"content": content_with_callout},
        headers=headers,
    )

    public_before = client.get(f"/api/public/projects/{project['id']}/articles/callout-promote").json()
    assert public_before["content"] == "<p>Initial</p>", "Content must remain published version after autosave"

    promote_resp = client.post(f"/articles/{article['id']}/promote", headers=headers)
    assert promote_resp.status_code == 200

    public_after = client.get(f"/api/public/projects/{project['id']}/articles/callout-promote").json()
    assert "callout" in public_after["content"], "Content must update after promote"
    import json as _json
    callouts_after = _json.loads(public_after["callouts_json"]) if public_after["callouts_json"] else []
    assert len(callouts_after) > 0, "callouts_json must be present after promote"


def _create_project_and_article(client, headers, title, slug):
    project_resp = client.post("/projects", json={
        "name": "Test Project",
        "domain": "blog.com",
        "language": "fr",
    }, headers=headers)
    assert project_resp.status_code == 201, f"Project creation failed: {project_resp.text}"
    project = project_resp.json()
    art_resp = client.post(f"/projects/{project['id']}/articles", json={
        "title": title, "slug": slug, "content": "<p>Test</p>", "keyword": "test",
    }, headers=headers)
    assert art_resp.status_code == 201, f"Article creation failed: {art_resp.text}"
    return project, art_resp.json()


def test_promote_revalidated_false_when_no_webhook(client: TestClient):
    """When BLOG_REVALIDATE_URL is empty, revalidated=false is returned."""
    from app.core.config import settings

    old_url = settings.BLOG_REVALIDATE_URL
    old_secret = settings.BLOG_REVALIDATE_SECRET
    settings.BLOG_REVALIDATE_URL = ""
    settings.BLOG_REVALIDATE_SECRET = ""
    headers = register_and_login(client, email="rw_empty@test.com")
    try:
        _, article = _create_project_and_article(client, headers, "Revalidate Test", "revalidate-test")
        force_publish_article(article["id"])
        promote_resp = client.post(f"/articles/{article['id']}/promote", headers=headers)
        assert promote_resp.status_code == 200
        data = promote_resp.json()
        assert data["revalidated"] is False
    finally:
        settings.BLOG_REVALIDATE_URL = old_url
        settings.BLOG_REVALIDATE_SECRET = old_secret


def test_promote_revalidated_false_on_bad_url(client: TestClient):
    """When webhook URL is unreachable, promote succeeds but revalidated=false."""
    from app.core.config import settings

    old_url = settings.BLOG_REVALIDATE_URL
    old_secret = settings.BLOG_REVALIDATE_SECRET
    settings.BLOG_REVALIDATE_URL = "http://localhost:1/nonexistent"
    settings.BLOG_REVALIDATE_SECRET = "test-secret"
    headers = register_and_login(client, email="rw_badurl@test.com")
    try:
        _, article = _create_project_and_article(client, headers, "Bad Webhook Test", "bad-webhook")
        force_publish_article(article["id"])
        promote_resp = client.post(f"/articles/{article['id']}/promote", headers=headers)
        assert promote_resp.status_code == 200
        data = promote_resp.json()
        assert data["revalidated"] is False
    finally:
        settings.BLOG_REVALIDATE_URL = old_url
        settings.BLOG_REVALIDATE_SECRET = old_secret


def test_publish_returns_revalidated_false_when_no_webhook(client: TestClient):
    """Publish route returns revalidated:false when BLOG_REVALIDATE_URL is empty."""
    from app.core.config import settings

    old_url = settings.BLOG_REVALIDATE_URL
    old_secret = settings.BLOG_REVALIDATE_SECRET
    settings.BLOG_REVALIDATE_URL = ""
    settings.BLOG_REVALIDATE_SECRET = ""
    headers = register_and_login(client, email="pub_rev@test.com")
    try:
        _, article = _create_project_and_article(client, headers, "Pub Reval Test", "pub-reval")
        mark_article_ready_for_publication(article["id"])
        resp = client.post(f"/articles/{article['id']}/publish", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["revalidated"] is False
    finally:
        settings.BLOG_REVALIDATE_URL = old_url
        settings.BLOG_REVALIDATE_SECRET = old_secret


def test_revalidation_sends_secret_in_headers_and_query(monkeypatch):
    from app.models.project import Project
    from app.services.publication_revalidation_service import trigger_project_revalidation

    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

    class DummyClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, params, json, headers):
            captured.update({
                "url": url,
                "params": params,
                "json": json,
                "headers": headers,
            })
            return DummyResponse()

    class DummyDB:
        def commit(self):
            return None

    monkeypatch.setattr("app.services.publication_revalidation_service.httpx.Client", DummyClient)
    project = Project(id="project-1", revalidate_url="https://example.test/api/revalidate")
    project.revalidate_secret_encrypted = "shared-secret"

    result = trigger_project_revalidation(DummyDB(), project, event_type="manual")

    assert result["revalidated"] is True
    assert captured["params"]["secret"] == "shared-secret"
    assert captured["json"]["secret"] == "shared-secret"
    assert captured["headers"]["Authorization"] == "Bearer shared-secret"
    assert captured["headers"]["X-Ideas-Studio-Secret"] == "shared-secret"
    assert captured["headers"]["X-Revalidate-Secret"] == "shared-secret"


def test_autosave_version_has_updated_title(client: TestClient):
    """After autosave changes the title, the created version should have the new title."""
    headers, project = _setup(client, "ver_title@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Old Title", "content": "<p>Content</p>"},
        headers=headers,
    ).json()

    autosave = client.post(
        f"/articles/{article['id']}/autosave",
        json={"title": "New Title"},
        headers=headers,
    )
    assert autosave.status_code == 200
    assert autosave.json()["version_created"] is True

    versions_resp = client.get(f"/articles/{article['id']}/versions", headers=headers)
    assert versions_resp.status_code == 200
    versions = versions_resp.json()
    latest = versions[0]
    assert latest["title"] == "New Title", "Version should capture the updated title"


def test_slug_not_auto_regenerated_by_backend_on_title_change(client: TestClient):
    """The backend should NOT auto-regenerate slug when title changes (frontend handles it)."""
    headers, project = _setup(client, "slug_bk@test.com")
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "First Title", "content": "<p>Content</p>"},
        headers=headers,
    ).json()
    original_slug = article["slug"]
    assert "first-title" in original_slug

    resp = client.patch(
        f"/articles/{article['id']}",
        json={"title": "Second Title"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["slug"] == original_slug, "Backend should not auto-regenerate slug"
