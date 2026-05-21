from __future__ import annotations

import re

from app.schemas.seo_workflow import EditorialQualityReport, asdict
from app.services.seo.helpers import (
    detect_title_case_french,
    detect_long_dash,
    detect_h2_directly_followed_by_h3,
    detect_isolated_h3,
    detect_abusive_bold,
    detect_ai_phrases,
    detect_list_length_issues,
    strip_html,
    extract_headings_from_html,
)


def check_editorial_quality(content: str | None) -> EditorialQualityReport:
    report = EditorialQualityReport()

    if not content:
        report.manual_review_needed = True
        return report

    text = strip_html(content)
    html = content

    checks = [
        {
            "name": "no_h5_h6",
            "label": "Pas de H5/H6",
            "pass": True,
            "severity": "error",
        },
        {
            "name": "no_isolated_h3",
            "label": "Pas de H3 isolé",
            "pass": not detect_isolated_h3(html),
            "severity": "warning",
        },
        {
            "name": "no_h2_followed_by_h3",
            "label": "H2 non suivi directement par H3",
            "pass": len(detect_h2_directly_followed_by_h3(html)) == 0,
            "severity": "warning",
        },
        {
            "name": "no_french_title_case",
            "label": "Pas de Title Case artificiel en français",
            "pass": not detect_title_case_french(text[:200]),
            "severity": "warning",
        },
        {
            "name": "no_long_dashes",
            "label": "Pas de tirets longs",
            "pass": len(detect_long_dash(text)) == 0,
            "severity": "info",
        },
        {
            "name": "no_abusive_bold",
            "label": "Pas de gras abusif",
            "pass": len(detect_abusive_bold(html)) == 0,
            "severity": "warning",
        },
        {
            "name": "list_length_ok",
            "label": "Listes de longueur raisonnable",
            "pass": len(detect_list_length_issues(html)) == 0,
            "severity": "warning",
        },
        {
            "name": "ai_phrases_minimal",
            "label": "Pas de traces IA évidentes",
            "pass": len(detect_ai_phrases(text)) == 0,
            "severity": "warning",
        },
    ]

    headings = extract_headings_from_html(content)
    h5h6_matches = re.findall(r"<h([56])[^>]*>(.*?)</h\1>", html, re.IGNORECASE | re.DOTALL)
    if h5h6_matches:
        for c in checks:
            if c["name"] == "no_h5_h6":
                c["pass"] = False
                break

    for c in checks:
        if c["pass"]:
            report.passed_checks.append(c["name"])
        else:
            report.failed_checks.append(c["name"])
            report.issues.append({
                "check": c["name"],
                "severity": c.get("severity", "warning"),
                "message": f"Échec : {c['label']}",
            })
            report.recommendations.append(f"Corriger : {c['label']}")

    passed = len(report.passed_checks)
    total = max(1, len(checks))
    report.score = round((passed / total) * 100, 1)

    if report.failed_checks:
        report.manual_review_needed = True

    return report


def check_editorial_quality_dict(content: str | None) -> dict:
    return asdict(check_editorial_quality(content))
