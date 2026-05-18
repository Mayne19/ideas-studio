import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db
engine = None
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def reset_db(tmp_path):
    global engine
    db_path = tmp_path / "test_ideas_studio.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal.configure(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register_and_login(client: TestClient, email: str = "user@test.com", password: str = "pass1234", name: str = "Test User") -> dict:
    client.post("/auth/register", json={"name": name, "email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
