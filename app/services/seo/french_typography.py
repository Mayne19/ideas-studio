"""Typographie française déterministe, appliquée au contenu final.

Le rédacteur oublie régulièrement l'espace avant « : ; ? ! » (« coûts
cachés: rédaction », « en 2026? »), ce qui trahit un texte non relu. Ici :
espace insécable (U+00A0) avant ces signes et à l'intérieur des guillemets
français, dans le texte seulement (jamais dans une balise ni une URL), sans
toucher les heures ni les ratios (14:30, 16:9).
"""
from __future__ import annotations

import re

NBSP = " "
_TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")
# Signe double précédé d'un caractère non blanc ou d'espaces ordinaires.
_BEFORE_DOUBLE_RE = re.compile(r"(?<=[^\s\d(])[ \t]*([;:!?])(?=\s|$|[«»\"')])")
_BEFORE_DOUBLE_AFTER_DIGIT_RE = re.compile(r"(?<=\d)[ \t]*([;!?])(?=\s|$)|(?<=\d)[ \t]*(:)(?=\s|$)")
_OPEN_QUOTE_RE = re.compile(r"«[ \t]*")
_CLOSE_QUOTE_RE = re.compile(r"[ \t]*»")


def fix_french_text(text: str) -> str:
    if not text:
        return text
    if "://" in text:
        # Texte qui contient une URL : on ne touche que les segments hors URL.
        parts = re.split(r"(\S+://\S+)", text)
        return "".join(p if "://" in p else fix_french_text(p) for p in parts)
    text = _BEFORE_DOUBLE_RE.sub(lambda m: NBSP + m.group(1), text)
    text = _BEFORE_DOUBLE_AFTER_DIGIT_RE.sub(lambda m: NBSP + (m.group(1) or m.group(2)), text)
    text = _OPEN_QUOTE_RE.sub("«" + NBSP, text)
    text = _CLOSE_QUOTE_RE.sub(NBSP + "»", text)
    return text


def fix_french_typography(html: str) -> str:
    """Applique fix_french_text aux nœuds texte du HTML."""
    parts = _TAG_SPLIT_RE.split(html or "")
    return "".join(p if p.startswith("<") else fix_french_text(p) for p in parts)
