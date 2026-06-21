from tests.conftest import TestingSessionLocal, register_and_login
from app.models.password_reset_token import PasswordResetToken
from app.services.password_reset_service import _hash_token


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


def test_forgot_password_does_not_enumerate_unknown_email(client):
    resp = client.post("/auth/forgot-password", json={"email": "missing@test.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Si un compte existe" in data["message"]
    assert data["dev_reset_url"] is None


def test_password_reset_updates_password_once(client):
    client.post("/auth/register", json={"name": "Reset", "email": "reset@test.com", "password": "oldpass123"})

    forgot = client.post("/auth/forgot-password", json={"email": "reset@test.com"})
    assert forgot.status_code == 200
    reset_url = forgot.json()["dev_reset_url"]
    assert reset_url
    token = reset_url.split("token=", 1)[1]
    db = TestingSessionLocal()
    try:
        stored = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == _hash_token(token)).first()
        assert stored is not None
        assert stored.used_at is None
    finally:
        db.close()

    reset = client.post("/auth/reset-password", json={
        "token": token,
        "password": "newpass123",
        "password_confirm": "newpass123",
    })
    assert reset.status_code == 200
    assert client.post("/auth/login", json={"email": "reset@test.com", "password": "oldpass123"}).status_code == 401
    assert client.post("/auth/login", json={"email": "reset@test.com", "password": "newpass123"}).status_code == 200

    reuse = client.post("/auth/reset-password", json={
        "token": token,
        "password": "another123",
        "password_confirm": "another123",
    })
    assert reuse.status_code == 400
