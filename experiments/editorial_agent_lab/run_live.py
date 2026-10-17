"""Lance un unique essai réel du laboratoire éditorial."""

from __future__ import annotations

import argparse
from pathlib import Path

from .editorial_agent.live_runner import LiveRunConfig, LiveRunError, run_live


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keyword")
    parser.add_argument("--site-name", default="Ideas Studio")
    parser.add_argument("--domain", default="example.com")
    parser.add_argument("--category", default="")
    parser.add_argument("--editor-notes", default="")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--model", default=None, help="Réservé à la future configuration explicite")
    parser.add_argument("--max-cost-usd", type=float, default=3.0)
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/editorial_agent_lab/run"))
    args = parser.parse_args()
    config = LiveRunConfig(
        keyword=args.keyword,
        site_name=args.site_name,
        domain=args.domain,
        category=args.category,
        editor_notes=args.editor_notes,
        project_id=args.project_id,
        model=args.model,
        max_cost_usd=args.max_cost_usd,
        output_dir=args.output_dir,
    )
    try:
        report = run_live(config)
    except LiveRunError as exc:
        print(f"LIVE_RUN_BLOCKED: {exc}")
        return 2
    print(f"LIVE_RUN_DONE: {report['output']['article_html']}")
    print(f"REPORT: {report['output']['report_json']}")
    print(f"MODEL: {report['model']} | COST_USD: {report['cost_usd']} | BLOCKERS: {len(report['blocking_issues'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
