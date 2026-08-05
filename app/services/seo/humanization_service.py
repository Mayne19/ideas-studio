from __future__ import annotations

import re
from app.schemas.seo_workflow import HumanizationReport, asdict
from app.services.seo.helpers import strip_html, detect_ai_phrases
from app.services.seo.human_presence_service import (
    GENERIC_OPENERS,
    WORTHLESS_FILLER_PHRASES,
    EMPTY_SUPERLATIVES,
    WORN_EXPRESSIONS,
    HUMAN_MARKERS,
    CONCLUSION_STARTERS,
)


def _extract_paragraphs(content: str) -> list[str]:
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", content, flags=re.IGNORECASE | re.DOTALL)
    return [strip_html(p).strip() for p in paragraphs if strip_html(p).strip()]


def _extract_sections(content: str) -> list[str]:
    h2_positions = [
        m.start()
        for m in re.finditer(r"<h2[^>]*>(.*?)</h2>", content, re.IGNORECASE | re.DOTALL)
    ]
    if not h2_positions:
        return [strip_html(content)]
    sections = []
    for i, pos in enumerate(h2_positions):
        end = h2_positions[i + 1] if i + 1 < len(h2_positions) else len(content)
        sections.append(strip_html(content[pos:end]))
    return sections


def check_humanization(content: str | None) -> HumanizationReport:
    """10 tests universels de présence humaine, 100% heuristiques.

    Réutilise les listes de signaux de human_presence_service (ouvertures
    génériques, transitions creuses, superlatifs vides, expressions usées,
    marqueurs de voix humaine, lanceurs de conclusion) pour garantir la
    cohérence des deux services.
    """
    report = HumanizationReport()

    if not content or len(strip_html(content).strip()) < 50:
        report.manual_review_needed = True
        report.changes_suggested.append("Contenu insuffisant pour évaluer la présence humaine")
        return report

    text = strip_html(content).lower()
    paragraphs = _extract_paragraphs(content)
    sections = _extract_sections(content)

    ai_phrases = detect_ai_phrases(text)
    report.ai_phrases_detected = ai_phrases

    # Test 1 — phrases d'ouverture génériques (intro + début de section)
    intro_text = " ".join(paragraphs[:2]).lower() if paragraphs else ""
    generic_openers = [o for o in GENERIC_OPENERS if o in intro_text]
    section_openers = []
    for section in sections:
        first_sentence = section.strip()[:120].lower()
        for opener in GENERIC_OPENERS:
            if opener in first_sentence:
                section_openers.append(opener)
    if generic_openers:
        report.repeated_patterns.append(
            f"Ouverture générique en intro : {', '.join(generic_openers)}"
        )
    if section_openers:
        report.repeated_patterns.append(
            f"Ouverture générique en début de section : {', '.join(sorted(set(section_openers)))}"
        )

    # Test 2 — transitions creuses et expressions de remplissage
    filler_hits = [f for f in WORTHLESS_FILLER_PHRASES if f in text]
    if filler_hits:
        report.repeated_patterns.append(
            f"Expressions de remplissage : {', '.join(filler_hits)}"
        )

    # Test 3 — superlatifs vides
    superlatives = [w for w in EMPTY_SUPERLATIVES if re.search(rf"\b{re.escape(w)}\b", text)]
    if superlatives:
        report.repeated_patterns.append(f"Superlatifs vides : {', '.join(superlatives)}")

    # Test 4 — expressions usées
    worn = [w for w in WORN_EXPRESSIONS if w in text]
    if worn:
        report.repeated_patterns.append(f"Expressions usées : {', '.join(worn)}")

    # Test 5 — transitions en excès (répétition mécanique)
    transitions = [
        "par ailleurs", "en outre", "de plus", "d'autre part",
        "cependant", "néanmoins", "toutefois", "en revanche",
    ]
    overused = []
    for t in transitions:
        count = len(re.findall(re.escape(t), text))
        if count > 3:
            overused.append(f"{t} ({count}x)")
    if overused:
        report.repeated_patterns.append(f"Transitions répétées : {', '.join(overused)}")

    # Test 6 — longueur de phrase uniforme (aucune phrase courte de rythme)
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    has_short_punch = any(len(s.split()) <= 8 for s in sentences) if sentences else True
    if sentences and not has_short_punch:
        report.repeated_patterns.append("Aucune phrase courte de rythme détectée")

    # Test 7 — absence de marqueur de voix humaine
    marker_count = sum(1 for marker in HUMAN_MARKERS if marker in text)
    if marker_count == 0:
        report.repeated_patterns.append("Aucun marqueur de voix humaine")

    # Test 8 — conclusion générique (résumé au lieu de clore)
    last_paragraphs = " ".join(paragraphs[-2:]).lower() if len(paragraphs) >= 2 else text
    for gc in CONCLUSION_STARTERS:
        if gc in last_paragraphs:
            report.repeated_patterns.append(f"Conclusion générique détectée : '{gc}'")

    # Test 9 — tiret cadratin
    if "—" in content:
        report.repeated_patterns.append("Tiret cadratin présent")

    # Test 10 — répétition des premiers mots de paragraphe
    if paragraphs:
        starters = [re.sub(r"[^a-zà-ÿ]+", "", p.split()[0].lower()) for p in paragraphs if p.split()]
        if starters:
            counts = {}
            for s in starters:
                counts[s] = counts.get(s, 0) + 1
            repeats = {s: c for s, c in counts.items() if c >= 3}
            if repeats:
                detail = ", ".join(f"'{s}' ({c}x)" for s, c in sorted(repeats.items()))
                report.repeated_patterns.append(f"Premiers mots de paragraphe répétés : {detail}")

    if ai_phrases:
        report.changes_suggested.append("Remplacer les phrases IA détectées par des formulations directes")
        report.manual_review_needed = True
        for phrase in ai_phrases:
            report.auto_fixes_applied.append(f"AI phrase marked: '{phrase}'")

    if report.repeated_patterns:
        report.changes_suggested.append("Corriger les patterns détectés pour une voix plus humaine")
        report.manual_review_needed = True

    if not ai_phrases and not report.repeated_patterns:
        report.changes_suggested.append("Aucune trace IA évidente détectée")

    return report


def check_humanization_dict(content: str | None) -> dict:
    return asdict(check_humanization(content))
