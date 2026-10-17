from types import SimpleNamespace

from app.models.reference import ArticleStatus
from app.main import app
from app.services.editorial_workflow_service import (
    EditorialStatus,
    technical_checks,
    workflow_status,
)


def test_public_statuses_cover_the_new_path():
    assert workflow_status(SimpleNamespace(status_reason_id=ArticleStatus.IDEA_PROPOSED)) == EditorialStatus.IDEA
    assert workflow_status(SimpleNamespace(status_reason_id=ArticleStatus.WRITING_IN_PROGRESS)) == EditorialStatus.WRITING
    assert workflow_status(SimpleNamespace(status_reason_id=ArticleStatus.REVIEW_NEEDED)) == EditorialStatus.REVIEW
    assert workflow_status(SimpleNamespace(status_reason_id=ArticleStatus.READY_TO_PUBLISH)) == EditorialStatus.VALIDATED
    assert workflow_status(SimpleNamespace(status_reason_id=ArticleStatus.UPDATE_RECOMMENDED)) == EditorialStatus.UPDATE


def test_technical_validation_uses_the_three_lab_controls():
    article = '<aside class="summary"><p class="summary-title">En résumé</p><p>Réponse.</p></aside>'
    fiche = {
        "meta_title": "Titre",
        "meta_description": "Description",
        "slug": "titre",
        "mot_cle_principal": "titre",
        "sources": [],
        "images": [],
        "liens_internes_places": [],
        "liens_internes_suggeres": [],
        "faq": [],
    }
    checks = technical_checks(article, fiche)
    assert [check["name"] for check in checks] == [
        "encadré « En résumé »",
        "aucun tiret cadratin",
        "fiche json valide",
    ]
    assert all(check["passed"] for check in checks)


def test_new_workflow_routes_are_exposed_without_replacing_old_routes():
    paths = app.openapi()["paths"]
    assert "/projects/{project_id}/editorial-workflow/articles" in paths
    assert "/projects/{project_id}/editorial-workflow/articles/{article_id}/deposit" in paths
    assert "/projects/{project_id}/editorial-workflow/articles/{article_id}/schedule" in paths
    assert "/projects/{project_id}/articles/generate" in paths
