from types import SimpleNamespace

from app.main import app
from app.models.reference import ArticleStatus
from app.services import local_writer_service


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeDb:
    def __init__(self, rows, project=None):
        self.rows, self.project, self.commits = rows, project, 0

    def execute(self, _query):
        return FakeResult(self.rows)

    def get(self, _model, _id):
        return self.project

    def commit(self):
        self.commits += 1


def article(article_id, status, title="Sujet"):
    return SimpleNamespace(id=article_id, slug=f"slug-{article_id}", status_reason_id=status,
                           current_revision=SimpleNamespace(title=title))


def test_writing_jobs_list_only_articles_in_writing_with_their_request(monkeypatch):
    requests = {"a2": {"keyword": "application langue", "context_hint": "débutants", "comment": "plus court"}}
    monkeypatch.setattr(local_writer_service, "get_latest_artifact", lambda db, aid, key: requests.get(aid))
    db = FakeDb([article("a1", ArticleStatus.IDEA_PROPOSED), article("a2", ArticleStatus.WRITING_REQUESTED, "Quelle appli ?"),
                 article("a3", ArticleStatus.REVIEW_NEEDED)])
    jobs = local_writer_service.writing_jobs(db, "p")
    assert [job["article_id"] for job in jobs] == ["a2"]
    assert jobs[0] == {"article_id": "a2", "subject": "Quelle appli ?", "keyword": "application langue",
                       "context": "débutants", "audience": None, "angle": None, "comment": "plus court"}


def test_site_articles_need_a_domain_and_build_blog_urls(monkeypatch):
    assert local_writer_service.site_articles(FakeDb([], project=SimpleNamespace(domain=None)), "p") == []
    published = SimpleNamespace(slug="tache-gras", current_revision=SimpleNamespace(body="<p>Le gras part au savon.</p>"))
    db = FakeDb([(published, "Tache de gras")], project=SimpleNamespace(domain="www.theslash.fr"))
    assert local_writer_service.site_articles(db, "p") == [
        {"titre": "Tache de gras", "url": "https://www.theslash.fr/blog/tache-gras", "resume": "Le gras part au savon."}]


def test_writer_report_keeps_cost_tokens_and_error(monkeypatch):
    saved = []
    monkeypatch.setattr(local_writer_service, "save_artifact", lambda db, aid, key, payload: saved.append((aid, key, payload)))
    db = FakeDb([])
    payload = local_writer_service.record_writer_report(
        db, SimpleNamespace(id="a2"), {"cost_usd": 1.33, "tokens": {"output": 21051}, "error": None, "other": "x"})
    assert payload == {"cost_usd": 1.33, "tokens": {"output": 21051}, "error": None}
    assert saved == [("a2", "editorial_writer_report", payload)] and db.commits == 1


def test_local_writer_routes_are_exposed():
    paths = app.openapi()["paths"]
    assert "/projects/{project_id}/local-writer/jobs" in paths
    assert "/projects/{project_id}/local-writer/site-articles" in paths
    assert "/projects/{project_id}/local-writer/articles/{article_id}/report" in paths
