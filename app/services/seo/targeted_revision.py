"""Révision ciblée A9 (chaîne v2) : seulement les sections que le juge
éditorial (editorial_judge) désigne, avec sa consigne, au plus quelques
sections par passe. Chaque réécriture passe un garde-fou : mêmes titres,
mêmes liens, aucun chiffre nouveau absent de la section ou des faits
vérifiés, volume comparable. Une réécriture refusée laisse la section telle
quelle.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Callable

from app.core.utils import calculate_word_count
from app.services.seo.html_text_ops import html_to_text, split_units, unit_heading

logger = logging.getLogger(__name__)

CallFn = Callable[[str, str, float], str]
MAX_SECTIONS_PER_PASS = 4
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_H_RE = re.compile(r"<h([23])\b[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def locate_unit(units: list[str], section: str) -> int | None:
    """Index de l'unité visée par le juge (titre de section ou INTRODUCTION)."""
    target = _norm(section)
    if not target:
        return None
    if target in ("introduction", "intro"):
        return 0
    for i, unit in enumerate(units[1:], start=1):
        heading = _norm(unit_heading(unit))
        if heading and (heading == target or heading in target or target in heading):
            return i
    return None


def _numbers(text: str) -> set[str]:
    return {n.replace(",", ".") for n in _NUMBER_RE.findall(text or "")}


def guard_revision(before: str, after: str, allowed_numbers_text: str) -> str | None:
    if not after.strip():
        return "sortie vide"
    if re.search(r"<h1\b", after, re.IGNORECASE):
        return "H1 ajouté"
    heads_before = [(m.group(1), html_to_text(m.group(2))) for m in _H_RE.finditer(before)]
    heads_after = [(m.group(1), html_to_text(m.group(2))) for m in _H_RE.finditer(after)]
    if heads_before[:1] != heads_after[:1]:
        return "titre H2 modifié"
    if set(_HREF_RE.findall(before)) - set(_HREF_RE.findall(after)):
        return "lien perdu"
    new_numbers = _numbers(html_to_text(after)) - _numbers(html_to_text(before)) - _numbers(allowed_numbers_text)
    if new_numbers:
        return "chiffre(s) nouveau(x) non vérifié(s) : " + ", ".join(sorted(new_numbers)[:5])
    wb, wa = calculate_word_count(before), calculate_word_count(after)
    if wb and (wa < 0.5 * wb or wa > 1.8 * wb):
        return f"volume modifié ({wb} -> {wa} mots)"
    return None


def build_revision_prompt(unit_html: str, instructions: str, facts_block: str, reference_block: str,
                          *, is_intro: bool) -> str:
    what = "l'introduction" if is_intro else "cette section"
    parts = [
        f"Tu es le rédacteur de l'article. Le rédacteur en chef te demande de réviser {what} :",
        f"« {instructions} »",
        "",
        "Règles :",
        "- Applique la consigne, rien d'autre ; garde le reste du texte, le ton et la longueur.",
        "- Garde mot pour mot le titre <h2> (et les <h3> sauf si la consigne les vise), chaque lien <a href>.",
        "- Aucun chiffre, prix, date ou nom absent du texte actuel, des chiffres de référence ou des faits ci-dessous.",
        "- Aucun témoignage ni cas inventé ; pas de tiret cadratin ; HTML simple (<h2>, <h3>, <p>, <ul>, <ol>, "
        "<li>, <table>, <strong>, <em>, <a>).",
    ]
    if reference_block:
        parts += ["", reference_block]
    if facts_block:
        parts += ["", facts_block]
    parts += ["", "HTML actuel :", unit_html.strip(), "", "Retourne uniquement le HTML révisé, sans explication."]
    return "\n".join(parts)


def revise_sections(content: str, fixes: list[dict], call_fn: CallFn, *, facts_text: str = "",
                    reference_block: str = "", facts_block_for=None,
                    fatal_exceptions: tuple[type[BaseException], ...] = ()) -> tuple[str, dict]:
    """Applique les consignes du juge ; retourne (contenu, rapport).
    `facts_block_for(index) -> str` fournit les faits de la section."""
    from app.services.seo.section_writer import clean_unit_html, lost_h2s
    from app.services.seo.structure_fixer import replace_em_dashes

    report: dict = {"applied": [], "rejected": [], "unlocated": []}
    units = split_units(content)
    done: set[int] = set()
    for fix in fixes[:MAX_SECTIONS_PER_PASS]:
        index = locate_unit(units, fix.get("section", ""))
        if index is None or index in done:
            report["unlocated"].append(fix.get("section", ""))
            continue
        done.add(index)
        before = units[index]
        facts_block = facts_block_for(index) if facts_block_for else ""
        prompt = build_revision_prompt(before, fix["instructions"], facts_block, reference_block, is_intro=index == 0)
        try:
            raw = call_fn(prompt, f"TargetedRevision_{index}", 0.4)
        except fatal_exceptions:
            raise
        except Exception as exc:
            report["rejected"].append({"section": fix.get("section"), "reason": f"appel échoué : {exc}"[:300]})
            continue
        after = replace_em_dashes(clean_unit_html(raw))
        if index == 0:
            after = re.sub(r"<h[1-6]\b[^>]*>.*?</h[1-6]>", "", after, flags=re.IGNORECASE | re.DOTALL)
        reason = guard_revision(before, after, facts_text + " " + reference_block + " " + facts_block)
        if reason:
            report["rejected"].append({"section": fix.get("section"), "reason": reason})
            continue
        units[index] = after.strip() + "\n"
        report["applied"].append({"section": fix.get("section"), "instructions": fix["instructions"][:300]})
    revised = "".join(units)
    if lost_h2s(content, revised):
        return content, {**report, "applied": [], "rejected": report["rejected"] + [{"section": "*", "reason": "H2 perdu"}]}
    return revised, report
