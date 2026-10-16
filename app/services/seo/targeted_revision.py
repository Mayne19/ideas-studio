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
    # Le juge recopie parfois l'étiquette du digest : « SECTION « Titre » ».
    section = re.sub(r"^\s*(?:##\s*)?section\s*", "", section or "", flags=re.IGNORECASE)
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


_THOUSANDS_RE = re.compile(r"(?<=\d)[\s\u00a0\u202f.](?=\d{3}\b)")


def _numbers(text: str) -> set[str]:
    """Nombres du texte, séparateurs de milliers retirés (« 5 000 » = 5000)."""
    text = _THOUSANDS_RE.sub("", text or "")
    return {n.replace(",", ".") for n in _NUMBER_RE.findall(text)}


def _is_trivial_number(n: str) -> bool:
    """Petits entiers (étapes, « 2 ans », « 3 devis ») et années : pas des
    chiffres à sourcer."""
    try:
        value = float(n)
    except ValueError:
        return False
    return (value.is_integer() and value <= 12) or (value.is_integer() and 1990 <= value <= 2035)


# Montant, pourcentage ou volume : le chiffre que le lecteur retient et qui
# doit venir des faits vérifiés.
_FIGURE_RE = re.compile(
    r"\d[\d\s\u00a0.,]*\s?(?:€|\$|euros?|dollars?|%|k€|M€|millions?|milliards?)", re.IGNORECASE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
# Calcul montré ou exemple annoncé (autorisés par le rédacteur, vérifiés par
# le juge) : « soit 0,39 $ par réponse », « Prenons un loyer de 600 € ».
_CALC_OR_EXAMPLE_RE = re.compile(
    r"\b(soit|prenons|par exemple|exemple|imaginons un|si vous [a-zé]+ \d|calcul|au total|multipli|divis)\b|[=×÷]|\d\s*[x*/]\s*\d",
    re.IGNORECASE)


def unverified_figures(content: str, allowed_text: str) -> dict[int, list[str]]:
    """A7 déterministe : {index d'unité: phrases portant un montant ou un
    pourcentage dont les nombres n'apparaissent ni dans les faits vérifiés,
    ni dans les chiffres de référence, ni dans les notes de l'expert}."""
    allowed = _numbers(allowed_text)
    found: dict[int, list[str]] = {}
    for index, unit in enumerate(split_units(content)):
        text = html_to_text(re.sub(r"<h[1-6]\b[^>]*>.*?</h[1-6]>", " ", unit, flags=re.IGNORECASE | re.DOTALL))
        for sentence in _SENTENCE_SPLIT_RE.split(text):
            if _CALC_OR_EXAMPLE_RE.search(sentence):
                continue
            figures = _FIGURE_RE.findall(sentence)
            nums = {n for f in figures for n in _numbers(f)}
            if any(n not in allowed and not _is_trivial_number(n) for n in nums):
                found.setdefault(index, []).append(sentence.strip()[:300])
    return found


def figure_fixes(content: str, allowed_text: str, max_sections: int = MAX_SECTIONS_PER_PASS) -> list[dict]:
    """Consignes de révision pour les chiffres non vérifiés (avant le juge)."""
    units = split_units(content)
    fixes = []
    for index, sentences in list(unverified_figures(content, allowed_text).items())[:max_sections]:
        section = "INTRODUCTION" if index == 0 else unit_heading(units[index])
        fixes.append({
            "section": section,
            "instructions": "Ces phrases contiennent des chiffres absents des faits vérifiés : remplace chaque "
                            "chiffre par la valeur des chiffres de référence ou des faits si elle existe, ou montre "
                            "le calcul qui y mène à partir des faits, ou présente-le comme un exemple (« Prenons… ») ; "
                            "sinon reformule sans chiffre. Phrases : " + " | ".join(f"« {s} »" for s in sentences[:4]),
        })
    return fixes


# Commentaire sur l'article ou la consigne recopié dans le texte (« Cette
# architecture dépasse les simples mentions théoriques… », fuite observée).
_META_RE = re.compile(
    r"\b(cette section|cet article|l'article|la section|le lecteur|les lecteurs|la consigne|"
    r"mentions? théoriques?|dépasse les simples|comme demandé|le rédacteur)\b", re.IGNORECASE)


def guard_revision(before: str, after: str, allowed_numbers_text: str) -> str | None:
    if not after.strip():
        return "sortie vide"
    new_meta = set(m.lower() for m in _META_RE.findall(html_to_text(after))) - \
        set(m.lower() for m in _META_RE.findall(html_to_text(before)))
    if new_meta:
        return "commentaire interne ajouté : " + ", ".join(sorted(new_meta))
    if re.search(r"<h1\b", after, re.IGNORECASE):
        return "H1 ajouté"
    heads_before = [(m.group(1), html_to_text(m.group(2))) for m in _H_RE.finditer(before)]
    heads_after = [(m.group(1), html_to_text(m.group(2))) for m in _H_RE.finditer(after)]
    if heads_before[:1] != heads_after[:1]:
        return "titre H2 modifié"
    # Une révision ne crée ni ne duplique de section : mêmes H2, dans le même
    # ordre (une section recopiée en double est passée par ce trou).
    if [h for h in heads_after if h[0] == "2"] != [h for h in heads_before if h[0] == "2"]:
        return "sections H2 ajoutées ou supprimées"
    if len([h for h in heads_after if h[0] == "3"]) > len([h for h in heads_before if h[0] == "3"]) + 1:
        return "trop de sous-titres H3 ajoutés"
    if set(_HREF_RE.findall(before)) - set(_HREF_RE.findall(after)):
        return "lien perdu"
    new_numbers = {
        n for n in _numbers(html_to_text(after)) - _numbers(html_to_text(before)) - _numbers(allowed_numbers_text)
        if not _is_trivial_number(n)
    }
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
        "- La consigne t'est adressée : n'en recopie rien et ne commente jamais le texte (« cette section », "
        "« cet article », « le lecteur ») ; écris directement le contenu, phrases liées les unes aux autres.",
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
