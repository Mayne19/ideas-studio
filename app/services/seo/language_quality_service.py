from __future__ import annotations

import re
from app.schemas.seo_workflow import LanguageQualityReport, asdict
from app.services.seo.adapters.language_adapter import language_adapter
from app.services.seo.helpers import strip_html


def check_language_quality(content: str | None) -> LanguageQualityReport:
    report = LanguageQualityReport()

    if not content:
        report.manual_review_needed = True
        return report

    text = strip_html(content)

    if language_adapter.configured:
        lt_result = language_adapter.check(text)
        report.external_tool_used = lt_result.get("external_tool_used", False)
        report.tool_used = lt_result.get("tool_used", "heuristic")
        if lt_result.get("issues"):
            report.issues = lt_result["issues"][:30]
            report.suggestions.append(f"{len(lt_result['issues'])} issue(s) detected by LanguageTool")
    else:
        report.tool_used = "heuristic"
        report.external_tool_used = False
        report.suggestions.append("LanguageTool not configured — heuristic check only")

    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    for s in sentences:
        words_count = len(s.split())
        if words_count > 40:
            report.issues.append({
                "type": "sentence_length",
                "message": f"Phrase trop longue ({words_count} mots)",
                "suggestion": "Réduire la longueur de la phrase",
            })
            if f"Phrase trop longue" not in str(report.suggestions):
                report.suggestions.append("Réduire les phrases de plus de 40 mots")

    if not report.issues:
        report.suggestions.append("Aucun problème linguistique majeur détecté")

    return report


def check_language_quality_dict(content: str | None) -> dict:
    return asdict(check_language_quality(content))
