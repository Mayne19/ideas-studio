"""Opérations déterministes sur le HTML d'un article : découpage par section,
localisation d'une phrase citée par un modèle, extraction de JSON.

Utilisé par les passes de finition (relecture par section, cohérence,
citations) : le modèle désigne une phrase exacte, le code fait la
modification. Aucune réécriture libre de l'article.
"""
from __future__ import annotations

import html as html_lib
import json
import re
from typing import Any

_H2_START_RE = re.compile(r"<h2\b", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
# Entre deux mots d'une phrase citée : espaces, balises inline, espace insécable.
_GAP = r"(?:\s|&nbsp;|&#160;|<[^>]+>)+"
_HEADING_OPEN_RE = re.compile(r"<h[1-6]\b", re.IGNORECASE)
_HEADING_CLOSE_RE = re.compile(r"</h[1-6]\s*>", re.IGNORECASE)
_A_OPEN_RE = re.compile(r"<a\b", re.IGNORECASE)
_A_CLOSE_RE = re.compile(r"</a\s*>", re.IGNORECASE)
_BLOCK_TEXT_RE = re.compile(r"<(p|li)\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)


def html_to_text(fragment: str) -> str:
    text = html_lib.unescape(_TAG_RE.sub(" ", fragment or ""))
    return re.sub(r"\s+", " ", text).strip()


def split_units(content: str) -> list[str]:
    """Découpe l'article en unités : l'introduction (texte avant le premier
    <h2>, éventuellement vide) puis un bloc par <h2> jusqu'au suivant.
    "".join(split_units(c)) == c."""
    content = content or ""
    starts = [m.start() for m in _H2_START_RE.finditer(content)]
    if not starts:
        return [content]
    units = [content[: starts[0]]]
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(content)
        units.append(content[start:end])
    return units


def unit_heading(unit: str) -> str:
    m = re.search(r"<h2\b[^>]*>(.*?)</h2>", unit or "", re.IGNORECASE | re.DOTALL)
    return html_to_text(m.group(1)) if m else ""


def text_blocks(content: str) -> list[str]:
    """Texte des paragraphes et éléments de liste, dans l'ordre."""
    return [t for t in (html_to_text(m.group(2)) for m in _BLOCK_TEXT_RE.finditer(content or "")) if t]


def _sentence_pattern(sentence: str) -> re.Pattern | None:
    tokens = [t for t in re.split(r"\s+", html_lib.unescape(sentence or "").strip()) if t]
    if len(tokens) < 3:
        return None
    parts = []
    for token in tokens:
        # Le texte de l'article peut contenir les entités HTML des caractères
        # spéciaux (&amp;, &rsquo;…) : on accepte les deux formes.
        alternatives = {re.escape(token), re.escape(html_lib.escape(token, quote=False))}
        parts.append("(?:" + "|".join(sorted(alternatives)) + ")")
    return re.compile(_GAP.join(parts))


def _inside(content: str, pos: int, open_re: re.Pattern, close_re: re.Pattern) -> bool:
    before = content[:pos]
    last_open = None
    for m in open_re.finditer(before):
        last_open = m.end()
    if last_open is None:
        return False
    return not close_re.search(before, last_open)


def inside_heading(content: str, pos: int) -> bool:
    return _inside(content, pos, _HEADING_OPEN_RE, _HEADING_CLOSE_RE)


def inside_link(content: str, pos: int) -> bool:
    return _inside(content, pos, _A_OPEN_RE, _A_CLOSE_RE)


def find_sentence_span(content: str, sentence: str) -> tuple[int, int] | None:
    """Position (début, fin) de la phrase dans le HTML, tolérante aux balises
    inline et aux espaces. None si absente, ambiguë (plusieurs occurrences)
    ou située dans un titre."""
    pattern = _sentence_pattern((sentence or "").strip())
    if pattern is None:
        return None
    matches = [m for m in pattern.finditer(content or "") if not inside_heading(content, m.start())]
    if len(matches) != 1:
        return None
    return matches[0].start(), matches[0].end()


def span_is_plain(fragment: str, allowed: tuple[str, ...] = ("strong", "em", "b", "i")) -> bool:
    """Le fragment ne contient que des balises inline autorisées et équilibrées
    (jamais de fermeture/ouverture de bloc, jamais de lien)."""
    tags = re.findall(r"<\s*(/?)\s*([a-zA-Z0-9]+)[^>]*>", fragment or "")
    depth: dict[str, int] = {}
    for closing, name in tags:
        name = name.lower()
        if name not in allowed:
            return False
        depth[name] = depth.get(name, 0) + (-1 if closing else 1)
        if depth[name] < 0:
            return False
    return all(v == 0 for v in depth.values())


def cleanup_html(content: str) -> str:
    """Après suppression de phrases : paragraphes vides, espaces doublés."""
    content = re.sub(r"<(p|li)\b[^>]*>\s*</\1>\s*", "", content, flags=re.IGNORECASE)
    content = re.sub(r"[ \t]{2,}", " ", content)
    content = re.sub(r"\s+([.,;:!?])(?=\s|<|$)", r"\1", content)
    content = re.sub(r"(<(?:p|li)\b[^>]*>)\s+", r"\1", content, flags=re.IGNORECASE)
    return content


def extract_json_object(raw: str) -> dict[str, Any] | None:
    """Premier objet JSON d'une réponse de modèle (backticks tolérés)."""
    text = (raw or "").strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        value = json.loads(text[start: end + 1])
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None
