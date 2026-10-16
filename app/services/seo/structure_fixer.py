from __future__ import annotations

"""Correction ciblée des règles de structure dures (une passe au plus).

D'abord les corrections déterministes (H1 dans le corps, sauts de niveau,
tirets cadratins). Ensuite, pour chaque section qui viole encore une règle
dure corrigeable (paragraphe trop long, phrase trop longue, longueurs
uniformes, vocabulaire banni, introduction trop longue…), UN appel court au
modèle bon marché reçoit la section seule et la liste exacte des violations.

Garde-fous : la sortie est rejetée si elle perd ou renomme un H2/H3, perd un
lien, perd un nombre (les faits), change trop de volume, ou ne réduit pas le
nombre de violations de la section. Rejet = section d'origine conservée.
"""

import logging
import re
from typing import Callable

from app.core.utils import calculate_word_count
from app.services.seo.html_text_ops import html_to_text, split_units
from app.services.seo.structure_validator import failing_units, validate_structure

logger = logging.getLogger(__name__)

CallFn = Callable[[str, str, float], str]

MAX_SECTIONS_FIXED = 8
_TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")
_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_H_RE = re.compile(r"<h([23])\b[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)


def replace_em_dashes(content: str) -> str:
    """Tiret cadratin -> virgule, dans le texte seulement (jamais dans une balise)."""
    parts = _TAG_SPLIT_RE.split(content or "")
    for i, part in enumerate(parts):
        if part.startswith("<") or "—" not in part:
            continue
        part = re.sub(r"\s*—\s*([.,;:!?])", r"\1", part)
        part = re.sub(r"\s*—\s*", ", ", part)
        parts[i] = re.sub(r",\s*,", ",", part)
    return "".join(parts)


def demote_isolated_h3(content: str) -> str:
    """Section H2 avec un seul H3 (règle : 0 ou au moins 2) : ce H3 devient
    une phrase d'accroche en gras, sans perte de texte."""
    parts = re.split(r"(?=<h2\b)", content or "", flags=re.IGNORECASE)
    for i, part in enumerate(parts):
        h3s = re.findall(r"<h3\b[^>]*>.*?</h3>", part, re.IGNORECASE | re.DOTALL)
        if part.lower().startswith("<h2") and len(h3s) == 1:
            inner = re.sub(r"^<h3\b[^>]*>|</h3>$", "", h3s[0], flags=re.IGNORECASE)
            parts[i] = part.replace(h3s[0], f"<p><strong>{inner.strip()}</strong></p>", 1)
    return "".join(parts)


def strip_heading_tics(content: str) -> str:
    """« Comment fonctionne concrètement un CMS headless ? » -> « Comment
    fonctionne un CMS headless ? » : un titre n'a jamais besoin d'un tic."""
    from app.services.seo.content_structure_guard import strip_tics

    return re.sub(r"(<h[23]\b[^>]*>)(.*?)(</h[23]>)", lambda m: m.group(1) + strip_tics(m.group(2)) + m.group(3),
                  content or "", flags=re.IGNORECASE | re.DOTALL)


def remove_duplicates(content: str) -> str:
    """Section H2 au titre identique à une précédente (titres normalisés) et
    paragraphe recopié mot pour mot : seule la première occurrence reste."""
    from app.services.seo.html_text_ops import split_units, unit_heading

    def norm(text: str) -> str:
        return re.sub(r"\W+", " ", html_to_text(text).lower()).strip()

    kept, seen_headings = [], set()
    for index, unit in enumerate(split_units(content or "")):
        heading = norm(unit_heading(unit)) if index else ""
        if heading and heading in seen_headings:
            continue
        seen_headings.add(heading)
        kept.append(unit)
    seen_paragraphs: set[str] = set()

    def _dedupe_p(match: re.Match) -> str:
        key = norm(match.group(0))
        if len(key.split()) >= 8 and key in seen_paragraphs:
            return ""
        seen_paragraphs.add(key)
        return match.group(0)
    return re.sub(r"<p\b[^>]*>.*?</p>", _dedupe_p, "".join(kept), flags=re.IGNORECASE | re.DOTALL)


def remove_body_faq(content: str) -> str:
    """La FAQ est générée à part (bloc FAQ + balisage FAQPage) : une section
    « Questions fréquentes » dans le corps la dupliquait."""
    from app.services.seo.html_text_ops import split_units, unit_heading

    units = split_units(content or "")
    kept = [units[0]] + [
        u for u in units[1:]
        if not re.match(r"\s*(questions?\s+fr[ée]quentes|faq\b|foire aux questions)", unit_heading(u), re.IGNORECASE)
    ]
    return "".join(kept) if len(kept) > 1 or len(units) == 1 else content


def apply_deterministic_fixes(content: str, title: str | None) -> str:
    from app.services.seo.content_structure_guard import apply_structure_guards
    return remove_duplicates(strip_heading_tics(
        demote_isolated_h3(replace_em_dashes(apply_structure_guards(content, title)))))


def _headings(html: str) -> list[tuple[str, str]]:
    return [(m.group(1), html_to_text(m.group(2))) for m in _H_RE.finditer(html or "")]


def _numbers(html: str) -> set[str]:
    return {n.replace(",", ".") for n in _NUMBER_RE.findall(html_to_text(html))}


def guard_section_rewrite(before: str, after: str) -> str | None:
    """Raison du rejet, ou None si la réécriture est acceptable."""
    if not after.strip():
        return "sortie vide"
    if re.search(r"<h1\b", after, re.IGNORECASE):
        return "H1 ajouté"
    if _headings(before) != _headings(after):
        return "titres H2/H3 modifiés"
    missing_links = set(_HREF_RE.findall(before)) - set(_HREF_RE.findall(after))
    if missing_links:
        return f"{len(missing_links)} lien(s) perdu(s)"
    missing_numbers = _numbers(before) - _numbers(after)
    if missing_numbers:
        return "chiffre(s) perdu(s) : " + ", ".join(sorted(missing_numbers)[:5])
    wb, wa = calculate_word_count(before), calculate_word_count(after)
    if wb and (wa < 0.6 * wb or wa > 1.6 * wb):
        return f"volume modifié ({wb} -> {wa} mots)"
    return None


def build_fix_prompt(unit_html: str, violations: list[str], *, is_intro: bool) -> str:
    what = "l'introduction" if is_intro else "cette section"
    return "\n".join([
        f"Corrige {what} d'un article pour respecter les règles de structure ci-dessous.",
        "",
        "Violations à corriger :",
        *[f"- {v}" for v in violations[:10]],
        "",
        "Règles de correction :",
        "- Coupe les paragraphes trop longs (1 à 4 phrases par paragraphe), coupe les phrases de plus de 30 mots.",
        "- Varie la longueur des paragraphes (un paragraphe d'une phrase, un plus développé…).",
        "- Remplace le vocabulaire banni par un mot précis ; pas de tiret cadratin (—).",
        "- Garde mot pour mot chaque titre <h2> et <h3>, dans le même ordre.",
        "- Garde chaque lien <a href> avec la même URL, chaque chiffre, prix, date et nom propre.",
        "- N'ajoute aucune information ni aucun chiffre ; ne supprime aucune information.",
        "- Si un tableau ou une liste numérotée est demandé, construis-le uniquement à partir des "
        "informations déjà présentes dans ce HTML.",
        "- HTML simple : <h2>, <h3>, <p>, <ul>, <ol>, <li>, <table>, <blockquote>, <strong>, <em>, <a>.",
        "",
        "HTML à corriger :",
        unit_html.strip(),
        "",
        "Retourne uniquement le HTML corrigé, sans explication ni backticks.",
    ])


def fix_failing_sections(
    content: str,
    report: dict,
    call_fn: CallFn,
    *,
    title: str | None = None,
    recommended_format: str | None = None,
    fatal_exceptions: tuple[type[BaseException], ...] = (),
    max_sections: int = MAX_SECTIONS_FIXED,
) -> tuple[str, dict]:
    """Une passe : un appel par section en échec sur une règle dure
    corrigeable. Retourne (contenu, rapport de correction)."""
    from app.services.seo.section_writer import clean_unit_html

    failing = failing_units(report)
    fix_report: dict = {"attempted": [], "applied": [], "rejected": [], "llm_calls": 0}
    if not failing:
        return content, fix_report
    units = split_units(content)
    for idx in range(len(units)):
        key = "intro" if idx == 0 else f"section:{idx}"
        if key not in failing or not units[idx].strip():
            continue
        if len(fix_report["attempted"]) >= max_sections:
            break
        fix_report["attempted"].append(key)
        before = units[idx]
        fix_report["llm_calls"] += 1
        try:
            raw = call_fn(build_fix_prompt(before, failing[key], is_intro=idx == 0), f"StructureFix_{key}", 0.3)
        except fatal_exceptions:
            raise
        except Exception as exc:
            fix_report["rejected"].append({"unit": key, "reason": f"appel échoué : {exc}"})
            continue
        after = replace_em_dashes(clean_unit_html(raw))
        reason = guard_section_rewrite(before, after)
        if reason is None:
            trial = units[:idx] + [after.strip() + "\n"] + units[idx + 1:]
            trial_report = validate_structure("".join(trial), title, recommended_format)
            remaining = len(failing_units(trial_report).get(key, []))
            if remaining >= len(failing[key]):
                reason = f"aucune violation corrigée ({remaining} restante(s))"
        if reason:
            fix_report["rejected"].append({"unit": key, "reason": reason})
            continue
        units[idx] = after.strip() + "\n"
        fix_report["applied"].append(key)
    return "".join(units), fix_report
