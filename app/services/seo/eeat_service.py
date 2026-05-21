from __future__ import annotations

import re
from app.schemas.seo_workflow import EEATChecklist, asdict
from app.services.seo.helpers import strip_html


def check_eeat(content: str | None, sources: list[str] | None = None, author_name: str | None = None) -> EEATChecklist:
    report = EEATChecklist()

    if not content:
        report.manual_review_needed = True
        return report

    text = strip_html(content)
    word_count = len(text.split())

    checks = [
        {"name": "author_present", "label": "Auteur présent", "pass": bool(author_name)},
        {"name": "sources_present", "label": "Sources citées", "pass": bool(sources) or bool(re.search(r'https?://', text))},
        {"name": "examples_present", "label": "Exemples concrets", "pass": "par exemple" in text.lower() or "exemple" in text.lower()},
        {"name": "depth_adequate", "label": "Profondeur suffisante", "pass": word_count >= 800},
        {"name": "no_fake_claims", "label": "Pas d'affirmations non fondées", "pass": True},
        {"name": "nuance_present", "label": "Nuances et limites", "pass": any(m in text.lower() for m in ["cependant", "néanmoins", "limite", "attention", "parfois"])},
        {"name": "practical_advice", "label": "Conseils pratiques", "pass": any(m in text.lower() for m in ["conseil", "astuce", "pratique", "étape"])},
    ]

    for c in checks:
        report.checks.append(c)
        if c["pass"]:
            report.passed.append(c["name"])
        else:
            report.failed.append(c["name"])
            report.recommendations.append(f"Ajouter : {c['label']}")

    passed = len(report.passed)
    total = max(1, len(checks))
    report.score = round((passed / total) * 100, 1)

    if report.failed:
        report.manual_review_needed = True

    return report


def check_eeat_dict(content: str | None, sources: list[str] | None = None, author_name: str | None = None) -> dict:
    return asdict(check_eeat(content, sources, author_name))
