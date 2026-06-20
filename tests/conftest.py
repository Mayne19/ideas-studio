import os
os.environ["APP_ENV"] = "test"
os.environ["DEFAULT_LLM_PROVIDER"] = "mock"
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

import pytest
from datetime import datetime, timezone
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


def _publishable_content() -> str:
    filler = " ".join(["contenu"] * 320)
    return f"<h1>Article pret</h1><p>{filler}</p>"


def mark_article_ready_for_publication(article_id: str, *, content: str | None = None) -> None:
    from app.models.article import Article

    db = TestingSessionLocal()
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        assert article is not None
        if content is not None:
            article.content = content
        else:
            article.content = _publishable_content()
        article.status = "ready_to_publish"
        article.meta_title = article.meta_title or article.title
        article.meta_description = article.meta_description or "Description de test suffisamment complete pour publier."
        article.seo_score = 96
        article.quality_score = 96
        article.geo_optimization_json = {"geo_score": 96, "source": "test_fixture"}
        article.originality_report_json = {
            "heuristic_score": 96,
            "trust_level": "medium",
            "manual_review_needed": False,
            "source": "test_fixture",
        }
        article.sources_json = {"items": [{"title": "Source test", "url": "https://example.com/source"}]}
        article.fact_check_report_json = {"status": "passed"}
        article.completed_agent_keys = "__complete__"
        article.global_score = 96
        article.global_score_valid = 1
        article.human_validated_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def force_publish_article(article_id: str) -> None:
    from app.models.article import Article

    db = TestingSessionLocal()
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        assert article is not None
        now = article.published_at or datetime.now(timezone.utc)
        article.status = "published"
        article.published_at = now
        article.published_content = article.content
        article.published_title = article.title
        article.published_excerpt = article.excerpt
        article.published_meta_description = article.meta_description
        article.published_cover_image_url = article.cover_image_url
        article.published_faq_json = article.faq_json
        article.published_callouts_json = article.callouts_json
        db.commit()
    finally:
        db.close()
