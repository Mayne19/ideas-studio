"""Un essai complet : rédaction par l'agent Claude Code (skill
redaction-article), séparation article / fiche, contrôles, fichiers de sortie
dans outputs/<slug>/ (article.md, fiche.json, report.json)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .checks import blocking_checks
from .claude_cli_client import run_writer
from .similarity import fetch_text, plagiarism_alert
from .writer import article_slug, build_prompt, split_output

LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = LAB_ROOT / "outputs"


def generate(subject: str, *, site_articles: list[dict] | None = None, output_root: Path = OUTPUT_ROOT,
             writer: Callable[[str], dict] = run_writer, fetch: Callable[[str], str] = fetch_text) -> dict:
    started = datetime.now(timezone.utc)
    prompt = build_prompt(subject, site_articles)
    result = writer(prompt)
    article, fiche, fiche_error = split_output(result["text"])
    slug = article_slug(subject, fiche)
    out_dir = Path(output_root) / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "article.md").write_text(article + "\n", encoding="utf-8")
    (out_dir / "raw_output.md").write_text(result["text"] + "\n", encoding="utf-8")
    fiche_path = out_dir / "fiche.json"
    if fiche is not None:
        fiche_path.write_text(json.dumps(fiche, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checks = blocking_checks(article, fiche, fiche_error)
    sources = [s.get("url", "") for s in (fiche or {}).get("sources") or [] if isinstance(s, dict) and s.get("url")]
    report = {
        "subject": subject,
        "started_at": started.isoformat(),
        "writer": {"agent": "claude code, skill redaction-article", "cost_usd": result.get("cost_usd"),
                   "tokens": result.get("tokens"), "duration_s": result.get("duration_s"),
                   "turns": result.get("turns"), "web_search_requests": result.get("web_search_requests"),
                   "model_usage": result.get("model_usage")},
        "blocking_checks": checks,
        "passed": all(c["passed"] for c in checks),
        "plagiarism": plagiarism_alert(article, sources, fetch),
        "output": {"article_md": str(out_dir / "article.md"), "raw_output_md": str(out_dir / "raw_output.md"),
                   "fiche_json": str(fiche_path) if fiche is not None else None,
                   "report_json": str(out_dir / "report.json")},
    }
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
