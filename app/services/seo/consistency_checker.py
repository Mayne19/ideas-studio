"""Contrôle de cohérence de l'article entier, corrections ciblées.

Rédigé section par section, l'article peut se contredire (l'introduction
annonce 1 500–2 000 € quand la section détaillée dit 1 500–3 000 €) ou
répéter la même phrase dans l'introduction et la première section. Un seul
appel liste ces problèmes en JSON, avec la phrase exacte à modifier ; le code
applique ensuite des remplacements ou suppressions de phrases de façon
déterministe. Jamais de réécriture complète : une correction qui ne se
localise pas exactement (phrase absente, ambiguë, dans un titre, contenant un
lien) est ignorée et tracée dans le rapport.
"""
from __future__ import annotations

import logging
from typing import Callable

from app.core.utils import calculate_word_count
from app.services.seo.html_text_ops import (
    cleanup_html, extract_json_object, find_sentence_span, html_to_text, span_is_plain,
    split_units, text_blocks, unit_heading,
)
from app.services.seo.section_writer import lost_h2s

logger = logging.getLogger(__name__)

CallFn = Callable[[str, str, float], str]

MAX_FIXES = 12
MAX_VERIFIED_FACTS = 30
# Au-delà, la « correction » ressemble à une réécriture : on refuse.
MAX_TOTAL_WORD_DROP = 0.08


def build_article_digest(content: str) -> str:
    """Texte de l'article bloc par bloc, sections étiquetées."""
    lines: list[str] = []
    for index, unit in enumerate(split_units(content)):
        blocks = text_blocks(unit)
        if not blocks:
            continue
        label = "INTRODUCTION" if index == 0 else f"SECTION « {unit_heading(unit)} »"
        lines.append(f"## {label}")
        lines.extend(f"- {block}" for block in blocks)
        lines.append("")
    return "\n".join(lines).strip()


def build_consistency_prompt(content: str, verified_facts: list[str] | None = None) -> str:
    parts = [
        "Tu es secrétaire de rédaction. Vérifie la cohérence interne de cet article et signale uniquement :",
        "1. Les contradictions : un même chiffre, prix, durée, pourcentage ou affirmation donné avec des "
        "valeurs différentes à deux endroits de l'article.",
        "2. Les doublons : une phrase de l'introduction répétée (identique ou quasi identique) dans une section.",
        "3. Les affirmations non étayées : une règle, un chiffre ou un effet présenté comme certain, absent "
        "des faits vérifiés et douteux ou faux (idées reçues SEO, obligations inventées, « Google favorise… », "
        "« les registres suspendent… »).",
        "4. Les témoignages inventés : propos ou expérience attribués à une personne ou un client non sourcés.",
        "5. Les fragments : une phrase incomplète ou sans lien avec le paragraphe qui l'entoure.",
        "",
        "Pour chaque problème, désigne LA phrase à corriger, copiée mot pour mot depuis l'article :",
        "- contradiction : corrige la phrase la moins précise ou la moins étayée (souvent l'introduction) "
        "pour l'aligner sur la valeur détaillée dans la section ou dans les faits vérifiés ; "
        "action \"replace\", la phrase corrigée ne change que la valeur fautive.",
        "- doublon : garde la phrase de l'introduction, supprime l'occurrence dans la section "
        "(action \"remove\") ; si la section deviendrait vide de sens, reformule-la (action \"replace\").",
        "- affirmation non étayée : supprime-la (action \"remove\") ou, si le paragraphe en dépend, "
        "remplace-la par une formulation prudente et exacte sans nouveau chiffre (action \"replace\").",
        "- témoignage inventé ou fragment : supprime la phrase (action \"remove\").",
        "Ne signale pas un conseil pratique raisonnable ni une évidence du métier : seulement ce qu'un expert "
        "relèverait comme faux, invérifiable ou incohérent.",
        "N'invente aucun problème : si l'article est cohérent, renvoie une liste vide.",
        "",
        "Réponds UNIQUEMENT en JSON :",
        '{"issues": [{"type": "contradiction" | "duplicate" | "unsupported" | "invented" | "fragment", "sentence": "phrase exacte de l\'article", '
        '"action": "replace" | "remove", "replacement": "phrase corrigée (vide si remove)", '
        '"related_sentence": "l\'autre phrase concernée", "reason": "explication courte"}]}',
    ]
    if verified_facts:
        parts += ["", "Faits vérifiés (font foi en cas de doute) :"]
        parts += [f"- {fact}" for fact in verified_facts[:MAX_VERIFIED_FACTS]]
    parts += ["", "Article :", build_article_digest(content)]
    return "\n".join(parts)


def _validate_issue(issue: dict) -> str | None:
    action = str(issue.get("action") or "").strip().lower()
    sentence = str(issue.get("sentence") or "").strip()
    if action not in ("replace", "remove"):
        return "action inconnue"
    if len(sentence.split()) < 4:
        return "phrase trop courte pour être localisée sans ambiguïté"
    if action == "replace":
        replacement = str(issue.get("replacement") or "").strip()
        if not replacement:
            return "remplacement vide"
        if "<" in replacement or ">" in replacement:
            return "remplacement contenant du HTML"
        ratio = len(replacement) / max(1, len(sentence))
        if ratio < 0.4 or ratio > 1.8:
            return "remplacement trop différent de la phrase d'origine"
        if replacement == sentence:
            return "remplacement identique"
    return None


def apply_consistency_fixes(content: str, issues: list[dict], max_fixes: int = MAX_FIXES) -> tuple[str, list[dict], list[dict]]:
    """Applique les corrections localisables ; retourne (contenu, appliquées, ignorées)."""
    applied: list[dict] = []
    skipped: list[dict] = []
    original = content
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        record = {
            "type": str(issue.get("type") or ""),
            "action": str(issue.get("action") or "").strip().lower(),
            "sentence": str(issue.get("sentence") or "").strip(),
            "replacement": str(issue.get("replacement") or "").strip(),
            "reason": str(issue.get("reason") or "")[:300],
        }
        if len(applied) >= max_fixes:
            skipped.append({**record, "skipped_because": "plafond de corrections atteint"})
            continue
        problem = _validate_issue(issue)
        if problem:
            skipped.append({**record, "skipped_because": problem})
            continue
        span = find_sentence_span(content, record["sentence"])
        if span is None:
            skipped.append({**record, "skipped_because": "phrase introuvable, ambiguë ou dans un titre"})
            continue
        start, end = span
        fragment = content[start:end]
        if not span_is_plain(fragment):
            skipped.append({**record, "skipped_because": "phrase contenant un lien ou du balisage de bloc"})
            continue
        new_text = record["replacement"] if record["action"] == "replace" else ""
        candidate = content[:start] + new_text + content[end:]
        if lost_h2s(content, candidate):
            skipped.append({**record, "skipped_because": "la correction ferait disparaître une section"})
            continue
        content = candidate
        applied.append({**record, "before": html_to_text(fragment)})
    if applied:
        content = cleanup_html(content)
    before_words = calculate_word_count(original)
    if before_words and calculate_word_count(content) < before_words * (1 - MAX_TOTAL_WORD_DROP):
        rejected = [{**a, "skipped_because": "trop de texte supprimé au total"} for a in applied]
        return original, [], skipped + rejected
    if lost_h2s(original, content):
        rejected = [{**a, "skipped_because": "section H2 perdue"} for a in applied]
        return original, [], skipped + rejected
    return content, applied, skipped


def check_and_fix_consistency(
    content: str,
    call_fn: CallFn,
    *,
    verified_facts: list[str] | None = None,
    fatal_exceptions: tuple[type[BaseException], ...] = (),
) -> tuple[str, dict]:
    """Un appel de détection, puis corrections déterministes. Retourne
    (contenu, rapport) ; en cas d'échec, le contenu est inchangé."""
    report: dict = {"issues_found": 0, "applied": [], "skipped": [], "error": None}
    try:
        raw = call_fn(build_consistency_prompt(content, verified_facts), "ConsistencyCheck", 0.1)
    except fatal_exceptions:
        raise
    except Exception as exc:
        logger.warning("consistency_check: appel en échec : %s", exc)
        report["error"] = str(exc)[:300]
        return content, report
    data = extract_json_object(raw)
    if data is None or not isinstance(data.get("issues"), list):
        report["error"] = "réponse JSON invalide"
        return content, report
    issues = [i for i in data["issues"] if isinstance(i, dict)]
    report["issues_found"] = len(issues)
    content, applied, skipped = apply_consistency_fixes(content, issues)
    report["applied"] = applied
    report["skipped"] = skipped
    return content, report
