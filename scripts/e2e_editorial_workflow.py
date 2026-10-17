"""Test de bout en bout du parcours éditorial (phase 7 de la refonte), sur le
backend réel : un sujet ajouté, rédigé (rédacteur local, skill), relu, validé,
programmé puis publié par la publication automatique.

Il crée un projet de test dédié (aucun article publié sur un vrai site), puis
appelle les mêmes routes que les écrans Idées, Relecture et Publication.

Usage, depuis la racine du dépôt (Claude Code connecté sur la machine) :
  IDEAS_STUDIO_EMAIL=… IDEAS_STUDIO_PASSWORD=… python scripts/e2e_editorial_workflow.py "<sujet>"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.editorial_agent_lab.editorial_agent.cms_client import CmsClient  # noqa: E402
from experiments.editorial_agent_lab.local_worker import run_once  # noqa: E402

PUBLICATION_WAIT_SECONDS = 9 * 60  # la publication automatique passe toutes les 5 minutes


def step(results: list[dict], name: str, ok: bool, detail: str = "") -> None:
    results.append({"step": name, "ok": ok, "detail": detail})
    print(f"{'OK ' if ok else 'ÉCHEC'} {name}{' : ' + detail if detail else ''}", flush=True)
    if not ok:
        raise SystemExit(json.dumps(results, ensure_ascii=False, indent=2))


def status_of(cms: CmsClient, article_id: str) -> str | None:
    rows = cms.request("GET", cms._project("/editorial-workflow/articles"))
    return next((row["status"] for row in rows if row["id"] == article_id), None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("subject")
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--api", default=None)
    args = parser.parse_args()
    results: list[dict] = []

    cms = CmsClient("", api=args.api)
    project = cms.request("POST", "/projects", {"name": f"Test de bout en bout {datetime.now():%Y-%m-%d %H:%M}",
                                                  "locale": "fr-FR"})
    cms.project_id = project["id"]
    step(results, "projet de test créé", bool(project.get("id")), project["id"])

    created = cms.request("POST", cms._project("/articles"), {"title": args.subject, "keyword": args.keyword})
    article_id = created["id"]
    step(results, "sujet ajouté (écran Idées)", status_of(cms, article_id) == "idea", article_id)

    cms.request("POST", cms._project(f"/editorial-workflow/articles/{article_id}/request-writing"))
    jobs = cms.jobs()
    step(results, "envoyé en rédaction", status_of(cms, article_id) == "writing"
         and any(job["article_id"] == article_id for job in jobs), f"{len(jobs)} sujet(s) dans la file")

    failed: set[str] = set()
    deposited = run_once(cms, failed=failed)
    step(results, "rédigé par le rédacteur local et déposé", deposited == 1 and not failed)
    step(results, "à relire", status_of(cms, article_id) == "review")

    article = cms.request("GET", f"/articles/{article_id}")
    content = article.get("content") or ""
    step(results, "relu : article mis en forme", "<h2" in content and '<aside class="summary">' in content,
         f"{len(content)} caractères HTML")

    validation = cms.request("POST", cms._project(f"/editorial-workflow/articles/{article_id}/validate"))
    checks = " | ".join(f"{c['name']} {'OK' if c['passed'] else 'ÉCHEC'}" for c in validation["checks"])
    step(results, "validé (3 contrôles techniques)", validation["passed"] and status_of(cms, article_id) == "validated",
         checks)

    when = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    scheduled = cms.request("POST", cms._project(f"/editorial-workflow/articles/{article_id}/schedule"),
                            {"scheduled_for": when})
    step(results, "programmé", scheduled["passed"] and status_of(cms, article_id) == "scheduled", when)

    deadline = time.time() + PUBLICATION_WAIT_SECONDS
    status = None
    while time.time() < deadline:
        status = status_of(cms, article_id)
        if status == "published":
            break
        time.sleep(30)
    step(results, "publié par la publication automatique", status == "published", f"statut final : {status}")

    print(json.dumps({"project_id": cms.project_id, "article_id": article_id, "steps": results},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
