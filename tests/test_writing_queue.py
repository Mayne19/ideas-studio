"""Tests du workflow Production -> Rédaction (file d'attente writer)."""
import json
from datetime import datetime, timedelta, timezone

from tests.conftest import TestingSessionLocal, register_and_login


def _setup_project(client, *, wc_min=None, wc_max=None):
    headers = register_and_login(client)
    payload = {"name": "Projet WQ"}
    if wc_min is not None:
        payload["word_count_min"] = wc_min
    if wc_max is not None:
        payload["word_count_max"] = wc_max
    project = client.post("/projects", json=payload, headers=headers).json()
    return headers, project


def _generate_idea(project_id: str, db):
    from app.services.idea_engine import generate_idea
    from app.services.providers.llm_provider import MockLLMProvider
    from app.services.providers.search_provider import get_search_provider

    idea = generate_idea(
        db=db,
        project_id=project_id,
        project_audience=None,
        project_language="fr",
        llm=MockLLMProvider(),
        search=get_search_provider(),
    )
    db.commit()
    return idea


def test_target_word_count_clamped_to_project_range(client):
    """Le mock propose 2500 mots ; la plage projet 900-1400 doit être respectée."""
    _headers, project = _setup_project(client, wc_min=900, wc_max=1400)
    db = TestingSessionLocal()
    try:
        idea = _generate_idea(project["id"], db)
        assert idea is not None
        assert idea.target_word_count is not None
        assert 900 <= idea.target_word_count <= 1400
        brief = json.loads(idea.planning_brief_json)
        assert 900 <= brief["target_word_count"] <= 1400
    finally:
        db.close()


def test_idea_generation_creates_no_articles(client):
    """La génération d'idées ne doit produire que des idées, jamais des brouillons."""
    from app.models.article import Article

    _headers, project = _setup_project(client)
    db = TestingSessionLocal()
    try:
        for _ in range(3):
            _generate_idea(project["id"], db)
        statuses = {row[0] for row in db.query(Article.status).filter(Article.project_id == project["id"]).all()}
        assert statuses <= {"idea_proposed"}
    finally:
        db.close()


def test_send_to_production_queues_writing(client):
    """Valider une idée doit la mettre en file d'attente rédaction."""
    headers, project = _setup_project(client)
    db = TestingSessionLocal()
    try:
        idea = _generate_idea(project["id"], db)
        idea_id = idea.id
    finally:
        db.close()

    resp = client.post(f"/articles/{idea_id}/send-to-production", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "writing_requested"
    assert data["workflow_status"] == "production"


def test_claim_respects_limit_and_never_double_claims(client):
    """Le claim borne le parallélisme et ne prend jamais deux fois la même idée."""
    from app.services.production_queue import claim_for_writing, send_to_production

    from app.models.article import Article

    _headers, project = _setup_project(client)
    db = TestingSessionLocal()
    try:
        ids = []
        for i in range(5):
            article = Article(
                project_id=project["id"],
                title=f"Idée {i}",
                slug=f"idee-{i}",
                keyword=f"mot cle unique {i}",
                status="idea_proposed",
                priority=0,
                word_count=0,
            )
            db.add(article)
            db.flush()
            send_to_production(db, article.id)
            ids.append(article.id)
        db.commit()

        first = claim_for_writing(db, project["id"], 3)
        assert len(first) == 3
        second = claim_for_writing(db, project["id"], 3)
        assert len(second) == 2
        assert set(first) & set(second) == set()
        assert set(first) | set(second) == set(ids)
    finally:
        db.close()


def test_write_queued_article_produces_draft(client, monkeypatch):
    """Un article réclamé doit être rédigé (mock) et finir en draft_ready."""
    import app.core.database as core_db
    from app.models.article import Article
    from app.services.production_queue import claim_for_writing, send_to_production, write_queued_article

    monkeypatch.setattr(core_db, "SessionLocal", TestingSessionLocal)

    _headers, project = _setup_project(client)
    db = TestingSessionLocal()
    try:
        idea = _generate_idea(project["id"], db)
        send_to_production(db, idea.id)
        db.commit()
        claimed = claim_for_writing(db, project["id"], 1)
        assert claimed == [idea.id]

        result = write_queued_article(idea.id, project["id"])
        assert result["status"] == "draft_ready"

        db.expire_all()
        article = db.get(Article, idea.id)
        assert article.status == "draft_ready"
        assert article.content
    finally:
        db.close()


def test_writing_failure_marks_failed_and_requeue_endpoint(client, monkeypatch):
    """Un échec writer doit donner un statut failed, relançable via l'endpoint."""
    import app.core.database as core_db
    import app.services.seo.seo_generation_orchestrator as orch
    from app.models.article import Article
    from app.services.production_queue import claim_for_writing, send_to_production, write_queued_article

    monkeypatch.setattr(core_db, "SessionLocal", TestingSessionLocal)

    def boom(*args, **kwargs):
        raise RuntimeError("writer crashed")

    monkeypatch.setattr(orch, "generate_full_article", boom)

    headers, project = _setup_project(client)
    db = TestingSessionLocal()
    try:
        idea = _generate_idea(project["id"], db)
        send_to_production(db, idea.id)
        db.commit()
        claim_for_writing(db, project["id"], 1)

        result = write_queued_article(idea.id, project["id"])
        assert result["status"] == "failed"

        db.expire_all()
        article = db.get(Article, idea.id)
        assert article.status == "failed"
        assert article.workflow_status == "error"
        idea_id = idea.id
    finally:
        db.close()

    resp = client.post(f"/articles/{idea_id}/requeue-writing", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "writing_requested"


def test_stale_writing_is_requeued(client):
    """Une rédaction sans update depuis plus de 30 min est remise en file."""
    from app.models.article import Article
    from app.services.production_queue import requeue_stale_writing, send_to_production

    _headers, project = _setup_project(client)
    db = TestingSessionLocal()
    try:
        idea = _generate_idea(project["id"], db)
        send_to_production(db, idea.id)
        idea.status = "writing_in_progress"
        idea.updated_at = datetime.now(timezone.utc) - timedelta(minutes=45)
        db.commit()

        requeued = requeue_stale_writing(db, project["id"])
        assert requeued == 1
        db.expire_all()
        article = db.get(Article, idea.id)
        assert article.status == "writing_requested"
    finally:
        db.close()


def test_cancel_queued_writing_returns_to_idea(client):
    """Annuler un article en file le fait revenir en idée."""
    headers, project = _setup_project(client)
    db = TestingSessionLocal()
    try:
        from app.services.production_queue import send_to_production
        idea = _generate_idea(project["id"], db)
        send_to_production(db, idea.id)
        db.commit()
        idea_id = idea.id
    finally:
        db.close()

    resp = client.post(f"/articles/{idea_id}/cancel-writing", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"id": idea_id, "status": "idea_proposed", "cancelled": True}


def test_cancel_in_progress_stops_at_checkpoint(client, monkeypatch):
    """Une rédaction en cours avec annulation demandée s'arrête au checkpoint et revient en idée."""
    import app.core.database as core_db
    from app.models.article import Article
    from app.services.production_queue import claim_for_writing, send_to_production, write_queued_article

    monkeypatch.setattr(core_db, "SessionLocal", TestingSessionLocal)

    headers, project = _setup_project(client)
    db = TestingSessionLocal()
    try:
        idea = _generate_idea(project["id"], db)
        send_to_production(db, idea.id)
        db.commit()
        claim_for_writing(db, project["id"], 1)
        idea_id = idea.id
    finally:
        db.close()

    # L'utilisateur demande l'annulation pendant que le job est claimé
    resp = client.post(f"/articles/{idea_id}/cancel-writing", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["cancel_requested"] is True

    result = write_queued_article(idea_id, project["id"])
    assert result["status"] == "cancelled"

    db = TestingSessionLocal()
    try:
        article = db.get(Article, idea_id)
        assert article.status == "idea_proposed"
        assert article.writing_cancel_requested is False
    finally:
        db.close()


def test_writing_error_visible_on_failure(client, monkeypatch):
    """L'échec d'une rédaction doit exposer sa raison dans writing_error."""
    import app.core.database as core_db
    import app.services.seo.seo_generation_orchestrator as orch
    from app.models.article import Article
    from app.services.production_queue import claim_for_writing, send_to_production, write_queued_article

    monkeypatch.setattr(core_db, "SessionLocal", TestingSessionLocal)

    def boom(*args, **kwargs):
        raise RuntimeError("quota provider dépassé")

    monkeypatch.setattr(orch, "generate_full_article", boom)

    _headers, project = _setup_project(client)
    db = TestingSessionLocal()
    try:
        idea = _generate_idea(project["id"], db)
        send_to_production(db, idea.id)
        db.commit()
        claim_for_writing(db, project["id"], 1)
        idea_id = idea.id
    finally:
        db.close()

    write_queued_article(idea_id, project["id"])

    db = TestingSessionLocal()
    try:
        article = db.get(Article, idea_id)
        assert article.status == "failed"
        assert "quota provider dépassé" in (article.writing_error or "")
    finally:
        db.close()
