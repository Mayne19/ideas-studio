from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.conftest import register_and_login, TEST_DATABASE_URL
from app.models.project_member import ProjectMember

engine_test = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def _db() -> Session:
    return TestingSessionLocal()


def test_create_project(client):
    headers = register_and_login(client)
    resp = client.post("/projects", json={"name": "My Blog"}, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Blog"
    assert data["status"] == "not_connected"
    assert "public_tracking_key" in data
    assert "secret_api_key" not in data  # secret must not appear in ProjectPublic schema


def test_list_projects(client):
    headers = register_and_login(client)
    client.post("/projects", json={"name": "Blog A"}, headers=headers)
    client.post("/projects", json={"name": "Blog B"}, headers=headers)
    resp = client.get("/projects", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_projects_only_own(client):
    headers1 = register_and_login(client, "user1@test.com", "pass1234", "User 1")
    headers2 = register_and_login(client, "user2@test.com", "pass1234", "User 2")
    client.post("/projects", json={"name": "Blog of User 2"}, headers=headers2)
    resp = client.get("/projects", headers=headers1)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_access_own_project(client):
    headers = register_and_login(client)
    create = client.post("/projects", json={"name": "My Blog"}, headers=headers)
    project_id = create.json()["id"]
    resp = client.get(f"/projects/{project_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == project_id


def test_access_other_user_project_forbidden(client):
    headers1 = register_and_login(client, "owner@test.com", "pass1234", "Owner")
    headers2 = register_and_login(client, "intruder@test.com", "pass1234", "Intruder")
    create = client.post("/projects", json={"name": "Private Blog"}, headers=headers1)
    project_id = create.json()["id"]
    resp = client.get(f"/projects/{project_id}", headers=headers2)
    assert resp.status_code == 403


def test_project_member_created_as_owner(client):
    headers = register_and_login(client)
    create = client.post("/projects", json={"name": "My Blog"}, headers=headers)
    project_id = create.json()["id"]
    db = _db()
    try:
        member = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).first()
        assert member is not None
        assert member.role == "owner"
        assert member.status == "active"
    finally:
        db.close()


def test_patch_project_as_owner(client):
    headers = register_and_login(client)
    create = client.post("/projects", json={"name": "Old Name"}, headers=headers)
    project_id = create.json()["id"]
    resp = client.patch(f"/projects/{project_id}", json={"name": "New Name"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


def test_connect_info(client):
    headers = register_and_login(client)
    create = client.post("/projects", json={"name": "My Blog"}, headers=headers)
    project_id = create.json()["id"]
    resp = client.get(f"/projects/{project_id}/connect", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "snippet" in data
    assert "traffic.js" in data["snippet"]
    assert "secret_api_key" not in data  # full key must never appear
    assert "..." in data["secret_api_key_masked"]
