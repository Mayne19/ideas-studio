"""Rédacteur local : tourne sur le Mac, récupère les sujets « en rédaction »
du CMS, les rédige avec l'agent Claude Code (skill redaction-article,
abonnement local) et dépose l'article, la fiche et le rapport (coût réel).

Usage, depuis la racine du dépôt :
  IDEAS_STUDIO_EMAIL=… IDEAS_STUDIO_PASSWORD=… \\
  python -m experiments.editorial_agent_lab.local_worker <project_id> [--once] [--interval 60]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Callable

from .editorial_agent.cms_client import CmsClient
from .editorial_agent.runner import OUTPUT_ROOT, generate

WORKER_OUTPUT_ROOT = OUTPUT_ROOT / "cms"


def process_job(cms: CmsClient, job: dict, site_articles: list[dict], *,
                generate_fn: Callable[..., dict] = generate, output_root: Path = WORKER_OUTPUT_ROOT) -> dict:
    """Rédige un sujet et dépose le résultat ; une erreur est rapportée au CMS
    (l'article reste « en rédaction »), puis relancée pour le journal du worker."""
    article_id = job["article_id"]
    try:
        report = generate_fn(job["subject"], site_articles=site_articles, request=job,
                             output_root=Path(output_root) / article_id)
        markdown = Path(report["output"]["article_md"]).read_text(encoding="utf-8")
        fiche_path = report["output"].get("fiche_json")
        fiche = json.loads(Path(fiche_path).read_text(encoding="utf-8")) if fiche_path else None
        cms.deposit(article_id, markdown, fiche, report.get("fiche_error") or "")
    except Exception as exc:  # noqa: BLE001 - toute erreur est rapportée au CMS
        cms.report(article_id, {"error": str(exc)[:500]})
        raise
    writer = report["writer"]
    cms.report(article_id, {"cost_usd": writer.get("cost_usd"), "tokens": writer.get("tokens"),
                            "duration_s": writer.get("duration_s"), "turns": writer.get("turns"),
                            "checks": report["blocking_checks"]})
    return report


def run_once(cms: CmsClient, *, failed: set[str], generate_fn: Callable[..., dict] = generate,
             output_root: Path = WORKER_OUTPUT_ROOT, log: Callable[[str], None] = print) -> int:
    """Traite les sujets en attente ; un sujet en échec n'est pas retenté avant
    le redémarrage du worker. Rend le nombre d'articles déposés."""
    jobs = [job for job in cms.jobs() if job["article_id"] not in failed]
    if not jobs:
        return 0
    site_articles = cms.site_articles()
    done = 0
    for job in jobs:
        log(f"rédaction : {job['subject']} ({job['article_id']})")
        try:
            report = process_job(cms, job, site_articles, generate_fn=generate_fn, output_root=output_root)
        except Exception as exc:  # noqa: BLE001
            failed.add(job["article_id"])
            log(f"échec : {job['article_id']} : {exc}")
            continue
        done += 1
        log(f"déposé : {job['article_id']} ; coût {report['writer'].get('cost_usd')} $ ; "
            f"contrôles {'OK' if report['passed'] else 'à corriger'}")
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project_id")
    parser.add_argument("--api", default=None, help="URL du backend (défaut : production)")
    parser.add_argument("--once", action="store_true", help="un seul passage puis arrêt")
    parser.add_argument("--interval", type=int, default=60, help="secondes entre deux passages")
    args = parser.parse_args()
    cms = CmsClient(args.project_id, api=args.api)
    failed: set[str] = set()
    while True:
        try:
            run_once(cms, failed=failed)
        except Exception as exc:  # noqa: BLE001 - réseau ou CMS indisponible : on réessaie au passage suivant
            print(f"CMS injoignable : {exc}")
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
