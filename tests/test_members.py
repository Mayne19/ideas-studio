"""Tests for project member management routes (BLOCAGE 1 fix)."""
from fastapi.testclient import TestClient
from tests.conftest import register_and_login


def _setup(client: TestClient, email: str = "owner@test.com") -> tuple[dict, dict]:
    headers = register_and_login(client, email=email)
    resp = client.post(
        "/projects",
        json={"name": "Blog", "domain": "blog.com", "language": "fr"},
        headers=headers,
    )
    assert resp.status_code == 201
    return headers, resp.json()


def _new_user(client: TestClient, email: str, name: str = "Member") -> dict:
    resp = client.post("/auth/register", json={"name": name, "email": email, "password": "pass1234"})
    assert resp.status_code == 201
    return resp.json()


# ── 1. GET list members ───────────────────────────────────────────────────────

def test_list_members_owner(client: TestClient):
    headers, project = _setup(client, email="lm_owner@test.com")
    resp = client.get(f"/projects/{project['id']}/members", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["role"] == "owner"
    assert data[0]["user_email"] == "lm_owner@test.com"
    assert data[0]["user_id"] == project["owner_id"]


# ── 2. POST add member ────────────────────────────────────────────────────────

def test_add_member_success(client: TestClient):
    headers, project = _setup(client, email="am_owner@test.com")
    new_user = _new_user(client, "am_member@test.com")

    resp = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": new_user["id"], "role": "editor"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == new_user["id"]
    assert data["role"] == "editor"
    assert data["status"] == "active"
    assert data["user_email"] == "am_member@test.com"

    list_resp = client.get(f"/projects/{project['id']}/members", headers=headers)
    assert len(list_resp.json()) == 2


# ── 3. POST duplicate blocked ─────────────────────────────────────────────────

def test_add_member_duplicate_blocked(client: TestClient):
    headers, project = _setup(client, email="dup_owner@test.com")
    new_user = _new_user(client, "dup_member@test.com")

    client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": new_user["id"], "role": "editor"},
        headers=headers,
    )
    resp = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": new_user["id"], "role": "writer"},
        headers=headers,
    )
    assert resp.status_code == 409


# ── 4. POST role owner blocked ────────────────────────────────────────────────

def test_add_member_role_owner_blocked(client: TestClient):
    headers, project = _setup(client, email="ro_owner@test.com")
    new_user = _new_user(client, "ro_member@test.com")

    resp = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": new_user["id"], "role": "owner"},
        headers=headers,
    )
    assert resp.status_code == 422


# ── 5. PATCH change role ──────────────────────────────────────────────────────

def test_patch_member_role(client: TestClient):
    headers, project = _setup(client, email="pm_owner@test.com")
    new_user = _new_user(client, "pm_member@test.com")

    client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": new_user["id"], "role": "editor"},
        headers=headers,
    )
    resp = client.patch(
        f"/projects/{project['id']}/members/{new_user['id']}",
        json={"role": "writer"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "writer"


# ── 6. DELETE member ──────────────────────────────────────────────────────────

def test_delete_member_success(client: TestClient):
    headers, project = _setup(client, email="dm_owner@test.com")
    new_user = _new_user(client, "dm_member@test.com")

    client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": new_user["id"], "role": "editor"},
        headers=headers,
    )
    resp = client.delete(
        f"/projects/{project['id']}/members/{new_user['id']}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert "removed" in resp.json()["message"].lower()

    list_resp = client.get(f"/projects/{project['id']}/members", headers=headers)
    assert len(list_resp.json()) == 1


# ── 7. DELETE owner blocked ───────────────────────────────────────────────────

def test_delete_owner_blocked(client: TestClient):
    headers, project = _setup(client, email="do_owner@test.com")
    owner_id = project["owner_id"]

    resp = client.delete(
        f"/projects/{project['id']}/members/{owner_id}",
        headers=headers,
    )
    assert resp.status_code == 403


# ── 8. Viewer cannot manage members ──────────────────────────────────────────

def test_viewer_cannot_add_member(client: TestClient):
    headers_owner, project = _setup(client, email="vm_owner@test.com")
    viewer = _new_user(client, "vm_viewer@test.com", name="Viewer")

    client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": viewer["id"], "role": "viewer"},
        headers=headers_owner,
    )
    headers_viewer = register_and_login(client, email="vm_viewer@test.com")

    target = _new_user(client, "vm_target@test.com", name="Target")
    resp = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": target["id"], "role": "editor"},
        headers=headers_viewer,
    )
    assert resp.status_code == 403


# ── 9. Non-member cannot access members ──────────────────────────────────────

def test_nonmember_cannot_list_members(client: TestClient):
    headers_owner, project = _setup(client, email="nm_owner@test.com")
    headers_other = register_and_login(client, email="nm_other@test.com", name="Other")

    resp = client.get(f"/projects/{project['id']}/members", headers=headers_other)
    assert resp.status_code == 403


def test_nonmember_cannot_add_member(client: TestClient):
    headers_owner, project = _setup(client, email="nma_owner@test.com")
    headers_other = register_and_login(client, email="nma_other@test.com", name="Other")
    target = _new_user(client, "nma_target@test.com", name="Target")

    resp = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": target["id"], "role": "editor"},
        headers=headers_other,
    )
    assert resp.status_code == 403
