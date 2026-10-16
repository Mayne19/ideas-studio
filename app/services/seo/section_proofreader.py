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
# Mode clarté : des évidences peuvent disparaître, rien ne doit s'ajouter.
CLARITY_MAX_WORD_DROP = 0.20
CLARITY_MAX_WORD_GROWTH = 0.10
MIN_UNIT_WORDS = 15

_HEADING_RE = re.compile(r"<(h[23])\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def heading_signature(html: str) -> list[tuple[str, str]]:
    return [(m.group(1).lower(), normalize_heading(m.group(2))) for m in _HEADING_RE.finditer(html or "")]


def _numbers(html: str) -> list[str]:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return [n.replace(",", ".") for n in _NUMBER_RE.findall(text)]


def rejection_reason(original: str, candidate: str, *, max_drop: float = MAX_WORD_DROP,
                     max_growth: float = MAX_WORD_GROWTH) -> str | None:
    """Raison du rejet d'une unité relue, ou None si elle est acceptable."""
    if not candidate.strip():
        return "sortie vide"
    if heading_signature(original) != heading_signature(candidate):
        return "titres H2/H3 modifiés"
    before = calculate_word_count(original)
    after = calculate_word_count(candidate)
    if before and after < before * (1 - max_drop):
        return f"perte de mots ({before} → {after})"
    if before and after > before * (1 + max_growth):
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


def build_clarity_prompt(unit_html: str, proper_nouns: list[str]) -> str:
    parts = [
        "Tu relis un extrait d'article pour un lecteur peu à l'aise en français. Réécris UNIQUEMENT les phrases "
        "difficiles :",
        "- tournure inversée ou nominale (« Ajouter de l'eau à ce moment-là achève la plante »), sujet abstrait "
        "au lieu de « vous », phrase de plus de 30 mots, incise qui coupe la phrase ;",
        "- préfère la forme « Si vous faites X, il se passe Y » et responsabilise le lecteur quand la phrase "
        "parle de son action (« Vous croyez bien faire en ajoutant de l'eau, mais vous noyez votre plante ») ;",
        "- supprime les évidences (« sans rien installer » pour un outil en ligne, « pas besoin de savoir coder »).",
        "Interdits : toucher aux chiffres, aux liens, aux titres (<h2>, <h3> mot pour mot), aux tableaux et aux "
        "listes ; ajouter une information ; « Franchement », « Curieusement », « Imaginez » ; le tiret cadratin.",
        "Les phrases déjà claires restent identiques.",
    ]
    if proper_nouns:
        parts.append("Noms propres attendus dans l'article : " + ", ".join(proper_nouns[:12]) + ".")
    parts += ["Retourne UNIQUEMENT le HTML relu, sans explication ni backticks.", "", "Extrait :", unit_html.strip()]
    return "\n".join(parts)


def _structure_regressed(units: list[str], index: int, original: str, candidate: str) -> bool:
    before = "".join(units)
    after = "".join(units[:index] + [candidate] + units[index + 1:])
    return _hard_failures(after) > _hard_failures(before)


def _hard_failures(content: str) -> int:
    from app.services.seo.structure_validator import validate_structure
    return validate_structure(content).get("hard_failures", 0)


def proofread_article(
    content: str,
    call_fn: CallFn,
    *,
    proper_nouns: list[str] | None = None,
    fatal_exceptions: tuple[type[BaseException], ...] = (),
    mode: str = "spelling",
) -> tuple[str, dict]:
    """Relit chaque unité de l'article ; retourne (contenu, rapport). Une
    unité dont la relecture est rejetée ou échoue reste inchangée.
    `mode` : "spelling" (orthographe, sans reformuler) ou "clarity"
    (réécriture des phrases difficiles pour un lecteur débutant)."""
    units = split_units(content)
    clarity = mode == "clarity"
    report: dict = {"units": [], "corrected": 0, "rejected": 0, "errors": 0, "mode": mode}
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
            if clarity:
                raw = call_fn(build_clarity_prompt(stripped, proper_nouns or []), f"ClarityPass_{index}", 0.3)
            else:
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
        if clarity:
            reason = rejection_reason(stripped, candidate, max_drop=CLARITY_MAX_WORD_DROP,
                                      max_growth=CLARITY_MAX_WORD_GROWTH)
            if reason is None and _structure_regressed(units, index, stripped, candidate + trailing):
                reason = "règles de structure en échec en plus"
        else:
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
