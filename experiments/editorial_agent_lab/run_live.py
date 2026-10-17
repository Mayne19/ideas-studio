"""Génère un article avec le rédacteur du laboratoire (agent Claude Code et
skill redaction-article), sans OpenRouter ni CMS."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .editorial_agent.runner import OUTPUT_ROOT, generate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subject", help="sujet ou mot-clé de l'article")
    parser.add_argument("--site-articles", type=Path, default=None,
                        help="fichier JSON : liste d'articles du site {titre, url, resume}")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    site_articles = json.loads(args.site_articles.read_text(encoding="utf-8")) if args.site_articles else None
    try:
        report = generate(args.subject, site_articles=site_articles, output_root=args.output_root)
    except RuntimeError as exc:
        print(f"ECHEC : {exc}")
        return 2
    writer = report["writer"]
    print(f"ARTICLE : {report['output']['article_md']}")
    print(f"FICHE : {report['output']['fiche_json']}")
    print(f"COUT_USD : {writer['cost_usd']} | JETONS : {writer['tokens']} | DUREE_S : {writer['duration_s']}")
    for check in report["blocking_checks"]:
        print(f"CONTROLE {check['name']} : {'OK' if check['passed'] else 'ECHEC ' + check['detail']}")
    print(f"PLAGIAT (alerte) : {len(report['plagiarism']['findings'])} phrase(s) identique(s)")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
