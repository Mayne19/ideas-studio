"""Relecture orthographique section par section.

Le modèle bon marché laisse passer des jetons corrompus (« WordFréquemment »
pour « WordPress »), des fautes d'accord et de frappe. Un appel court par
unité (introduction, puis chaque bloc <h2>) corrige l'orthographe, la
grammaire et les mots corrompus, SANS reformuler. La sortie est rejetée
(unité d'origine conservée) si :
- l'ensemble des titres <h2>/<h3> change ;
- le nombre de mots baisse de plus de 10 % (ou monte de plus de 15 %) ;
- les liens (href) ou les nombres de l'unité changent.

Le module reçoit `call_fn(prompt, step, temperature) -> str` (testable avec
un faux provider).
"""
from __future__ import annotations

import logging
import re
from typing import Callable

from app.core.utils import calculate_word_count
from app.services.seo.html_text_ops import split_units, unit_heading
from app.services.seo.section_writer import clean_unit_html, normalize_heading

logger = logging.getLogger(__name__)

CallFn = Callable[[str, str, float], str]

MAX_WORD_DROP = 0.10
MAX_WORD_GROWTH = 0.15
MIN_UNIT_WORDS = 15

_HEADING_RE = re.compile(r"<(h[23])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def heading_signature(html: str) -> list[tuple[str, str]]:
    return [(m.group(1).lower(), normalize_heading(m.group(2))) for m in _HEADING_RE.finditer(html or "")]


def _numbers(html: str) -> list[str]:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return [n.replace(",", ".") for n in _NUMBER_RE.findall(text)]


def rejection_reason(original: str, candidate: str) -> str | None:
    """Raison du rejet d'une unité relue, ou None si elle est acceptable."""
    if not candidate.strip():
        return "sortie vide"
    if heading_signature(original) != heading_signature(candidate):
        return "titres H2/H3 modifiés"
    before = calculate_word_count(original)
    after = calculate_word_count(candidate)
    if before and after < before * (1 - MAX_WORD_DROP):
        return f"perte de mots ({before} → {after})"
    if before and after > before * (1 + MAX_WORD_GROWTH):
        return f"ajout de texte ({before} → {after})"
    if sorted(_HREF_RE.findall(original)) != sorted(_HREF_RE.findall(candidate)):
        return "liens modifiés"
    if sorted(_numbers(original)) != sorted(_numbers(candidate)):
        return "chiffres modifiés"
    return None


def build_proofread_prompt(unit_html: str, proper_nouns: list[str]) -> str:
    parts = [
        "Tu es correcteur professionnel en français. Relis l'extrait HTML ci-dessous et corrige UNIQUEMENT :",
        "- les fautes d'orthographe, d'accord, de conjugaison et de ponctuation ;",
        "- les mots corrompus, collés ou tronqués (ex. « WordFréquemment » au lieu de « WordPress ») : "
        "rétablis le mot voulu d'après le contexte.",
        "Interdits : reformuler, ajouter ou supprimer une phrase, modifier un chiffre, un lien, une balise "
        "ou un titre (<h2>, <h3> mot pour mot).",
        "Si l'extrait ne contient aucune faute, renvoie-le identique.",
    ]
    if proper_nouns:
        parts.append("Noms propres attendus dans l'article : " + ", ".join(proper_nouns[:12]) + ".")
    parts += [
        "Retourne UNIQUEMENT le HTML corrigé, sans explication ni backticks.",
        "",
        "Extrait :",
        unit_html.strip(),
    ]
    return "\n".join(parts)


def proofread_article(
    content: str,
    call_fn: CallFn,
    *,
    proper_nouns: list[str] | None = None,
    fatal_exceptions: tuple[type[BaseException], ...] = (),
) -> tuple[str, dict]:
    """Relit chaque unité de l'article ; retourne (contenu, rapport). Une
    unité dont la relecture est rejetée ou échoue reste inchangée."""
    units = split_units(content)
    report: dict = {"units": [], "corrected": 0, "rejected": 0, "errors": 0}
    output: list[str] = []
    for index, unit in enumerate(units):
        heading = unit_heading(unit) or ("introduction" if index == 0 else f"section {index}")
        if calculate_word_count(unit) < MIN_UNIT_WORDS:
            output.append(unit)
            continue
        entry = {"unit": heading, "status": "unchanged"}
        # Les espaces de fin d'unité (séparateurs entre blocs) sont conservés tels quels.
        stripped = unit.rstrip()
        trailing = unit[len(stripped):]
        try:
            raw = call_fn(build_proofread_prompt(stripped, proper_nouns or []), f"Proofreading_{index}", 0.1)
        except fatal_exceptions:
            raise
        except Exception as exc:
            logger.warning("proofreading: unité %s en échec : %s", heading, exc)
            entry.update(status="error", reason=str(exc)[:200])
            report["errors"] += 1
            report["units"].append(entry)
            output.append(unit)
            continue
        candidate = clean_unit_html(raw)
        reason = rejection_reason(stripped, candidate)
        if reason:
            entry.update(status="rejected", reason=reason)
            report["rejected"] += 1
            output.append(unit)
        elif candidate.strip() != stripped.strip():
            entry["status"] = "corrected"
            report["corrected"] += 1
            output.append(candidate + trailing)
        else:
            output.append(unit)
        report["units"].append(entry)
    return "".join(output), report
