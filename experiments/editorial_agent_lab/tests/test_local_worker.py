"""Rédacteur local : client CMS (connexion, jeton expiré) et boucle du worker
(dépôt, rapport du coût, erreur rapportée sans boucler)."""

import io
import json
from pathlib import Path
from urllib.error import HTTPError

from experiments.editorial_agent_lab.editorial_agent.cms_client import CmsClient, CmsError
from experiments.editorial_agent_lab.editorial_agent.writer import build_prompt
from experiments.editorial_agent_lab.local_worker import run_once


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def opener(responses, seen):
    def _open(request, timeout):
        seen.append((request.get_method(), request.full_url, request.headers.get("Authorization"),
                     json.loads(request.data) if request.data else None))
        status, payload = responses.pop(0)
        if status >= 400:
            raise HTTPError(request.full_url, status, "err", {}, io.BytesIO(b'{"detail": "x"}'))
        return FakeResponse(json.dumps(payload).encode())
    return _open


def test_cms_client_logs_in_and_retries_once_on_expired_token():
    seen = []
    cms = CmsClient("p1", api="https://cms.test", token="old", email="m@x.fr", password="pw",
                    opener=opener([(401, None), (200, {"access_token": "new"}), (200, [{"article_id": "a1"}])], seen))
    assert cms.jobs() == [{"article_id": "a1"}]
    assert [s[:3] for s in seen] == [("GET", "https://cms.test/projects/p1/local-writer/jobs", "Bearer old"),
                                     ("POST", "https://cms.test/auth/login", None),
                                     ("GET", "https://cms.test/projects/p1/local-writer/jobs", "Bearer new")]
    no_credentials = CmsClient("p1", api="https://cms.test", token=None, email=None, password=None,
                               opener=opener([], []))
    try:
        no_credentials.jobs()
    except CmsError as exc:
        assert exc.status == 401
    else:
        raise AssertionError("sans jeton ni identifiants, la connexion doit échouer")


def test_deposit_uses_the_editorial_workflow_route():
    seen = []
    cms = CmsClient("p1", api="https://cms.test", token="t", opener=opener([(200, {"id": "a1"})], seen))
    cms.deposit("a1", "# Titre", {"slug": "titre"}, "")
    assert seen[0][1] == "https://cms.test/projects/p1/editorial-workflow/articles/a1/deposit"
    assert seen[0][3] == {"markdown": "# Titre", "fiche": {"slug": "titre"}, "fiche_error": ""}


class FakeCms:
    def __init__(self, jobs):
        self._jobs, self.deposits, self.reports = jobs, [], []

    def jobs(self):
        return self._jobs

    def site_articles(self):
        return [{"titre": "Tache de gras", "url": "https://theslash.fr/blog/tache", "resume": "r"}]

    def deposit(self, article_id, markdown, fiche, fiche_error=""):
        self.deposits.append((article_id, markdown, fiche, fiche_error))

    def report(self, article_id, report):
        self.reports.append((article_id, report))


def fake_generate(tmp_path: Path, fail_for=()):
    calls = []

    def _generate(subject, *, site_articles, request, output_root):
        calls.append((subject, site_articles, request))
        if request["article_id"] in fail_for:
            raise RuntimeError("Claude Code a échoué")
        out = Path(output_root) / "slug"
        out.mkdir(parents=True)
        (out / "article.md").write_text("# Titre\n\nTexte.\n", encoding="utf-8")
        (out / "fiche.json").write_text('{"slug": "slug"}', encoding="utf-8")
        return {"output": {"article_md": str(out / "article.md"), "fiche_json": str(out / "fiche.json")},
                "fiche_error": "", "passed": True, "blocking_checks": [{"name": "x", "passed": True}],
                "writer": {"cost_usd": 1.2, "tokens": {"output": 9}, "duration_s": 200, "turns": 30}}
    return _generate, calls


def test_worker_writes_deposits_and_reports_cost(tmp_path):
    cms = FakeCms([{"article_id": "a1", "subject": "Quelle appli ?", "keyword": "appli langue", "comment": None}])
    generate_fn, calls = fake_generate(tmp_path)
    assert run_once(cms, failed=set(), generate_fn=generate_fn, output_root=tmp_path, log=lambda m: None) == 1
    assert calls[0][0] == "Quelle appli ?" and calls[0][1][0]["titre"] == "Tache de gras"
    assert cms.deposits == [("a1", "# Titre\n\nTexte.\n", {"slug": "slug"}, "")]
    assert cms.reports == [("a1", {"cost_usd": 1.2, "tokens": {"output": 9}, "duration_s": 200, "turns": 30,
                                   "checks": [{"name": "x", "passed": True}]})]


def test_worker_reports_an_error_and_does_not_retry_it(tmp_path):
    cms = FakeCms([{"article_id": "a1", "subject": "S1"}, {"article_id": "a2", "subject": "S2"}])
    generate_fn, calls = fake_generate(tmp_path, fail_for={"a1"})
    failed: set[str] = set()
    assert run_once(cms, failed=failed, generate_fn=generate_fn, output_root=tmp_path, log=lambda m: None) == 1
    assert failed == {"a1"} and cms.reports[0] == ("a1", {"error": "Claude Code a échoué"})
    assert [d[0] for d in cms.deposits] == ["a2"]
    run_once(cms, failed=failed, generate_fn=generate_fn, output_root=tmp_path / "2", log=lambda m: None)
    assert [c[2]["article_id"] for c in calls].count("a1") == 1


def test_request_details_are_passed_as_data_under_the_subject():
    prompt = build_prompt("Quelle appli ?", None, {"keyword": "appli langue", "comment": "Plus de sources officielles",
                                                    "context": "", "article_id": "a1"})
    assert prompt.splitlines() == ["/redaction-article", "", "Sujet : Quelle appli ?", "Mot-clé principal : appli langue",
                                   "Commentaire du relecteur : Plus de sources officielles"]
