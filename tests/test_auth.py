from tests.conftest import register_and_login


def test_register_user(client):
    resp = client.post("/auth/register", json={
        "name": "Alice",
        "email": "alice@test.com",
        "password": "secret123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@test.com"
    assert data["name"] == "Alice"
    assert "password_hash" not in data
    assert data["is_active"] is True


def test_register_duplicate_email(client):
    payload = {"name": "Bob", "email": "bob@test.com", "password": "secret"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 400


def test_login_user(client):
    client.post("/auth/register", json={"name": "Alice", "email": "alice@test.com", "password": "pass1234"})
    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "pass1234"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post("/auth/register", json={"name": "Alice", "email": "alice@test.com", "password": "pass1234"})
    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "wrong"})
    assert resp.status_code == 401


def test_me(client):
    headers = register_and_login(client, "me@test.com", "pass1234", "Me User")
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.com"


def test_me_no_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
