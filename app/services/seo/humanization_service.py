from __future__ import annotations

import re
from app.schemas.seo_workflow import HumanizationReport, asdict
from app.services.seo.helpers import strip_html, detect_ai_phrases


def check_humanization(content: str | None) -> HumanizationReport:
    report = HumanizationReport()

    if not content:
        report.manual_review_needed = True
        return report

    text = strip_html(content).lower()

    ai_phrases = detect_ai_phrases(text)
    report.ai_phrases_detected = ai_phrases

    transitions = [
        "par ailleurs", "en outre", "de plus", "d'autre part",
        "cependant", "néanmoins", "toutefois", "en revanche",
    ]
    found_transitions = []
    for t in transitions:
        count = len(re.findall(re.escape(t), text))
        if count > 3:
            found_transitions.append(f"{t} ({count}x)")

    if found_transitions:
        report.repeated_patterns.append(f"Transitions répétées : {', '.join(found_transitions)}")

    generic_conclusions = [
        "en conclusion",
        "pour conclure",
        "en résumé",
    ]
    for gc in generic_conclusions:
        if gc in text:
            report.repeated_patterns.append(f"Conclusion générique détectée : '{gc}'")

    if ai_phrases:
        report.changes_suggested.append("Remplacer les phrases IA détectées par des formulations directes")
        report.manual_review_needed = True
        for phrase in ai_phrases:
            report.auto_fixes_applied.append(f"AI phrase marked: '{phrase}'")

    if not ai_phrases and not found_transitions:
        report.changes_suggested.append("Aucune trace IA évidente détectée")

    return report


def check_humanization_dict(content: str | None) -> dict:
    return asdict(check_humanization(content))
