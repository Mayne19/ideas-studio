from __future__ import annotations

"""Volume tier (article_tier + section_tier) — sans colonne DB dédiée.

Classe chaque article selon sa volumétrie réelle (article_tier) et chaque
section H2 selon sa profondeur (section_tier). Heuristique 100% déterministe,
basée sur le volume de mots réel du contenu plutôt que sur la cible annoncée.

Fonctions LLM/agents ne sont jamais nécessaires : le tier découle directement
du nombre de mots. Le résultat est stocké comme artifact, pas en colonne.
"""

import re

from app.services.seo.helpers import strip_html


def _word_count(content: str | None) -> int:
    if not content:
        return 0
    return len(strip_html(content).split())


def _extract_h2_headings(content: str | None) -> list[str]:
    if not content:
        return []
    return [
        re.sub(r"<[^>]+>", "", m.group(1)).strip()
        for m in re.finditer(r"<h2[^>]*>(.*?)</h2>", content, re.IGNORECASE | re.DOTALL)
        if re.sub(r"<[^>]+>", "", m.group(1)).strip()
    ]


ARTICLE_TIER_BY_WORDS = [
    (5000, "pillar"),
    (2500, "long"),
    (1500, "medium"),
    (800, "short"),
]


def article_tier_for_words(word_count: int) -> str:
    for threshold, tier in ARTICLE_TIER_BY_WORDS:
        if word_count >= threshold:
            return tier
    return "micro"


def _section_tier_for_words(word_count: int) -> str:
    if word_count >= 400:
        return "deep"
    if word_count >= 150:
        return "standard"
    return "brief"


def compute_volume_tiers(content: str | None) -> dict:
    """Calcule article_tier (volumétrie globale) et section_tier (par H2).

    Retourne un dict stable prêt à être persisté comme artifact :
      - article_tier : micro | short | medium | long | pillar
      - article_words : nombre réel de mots
      - sections : [{heading, words, section_tier}]
      - flags : signaux d'attention (section creuse, article sur-épais…)
    """
    words = _word_count(content)
    article_tier = article_tier_for_words(words)

    headings = _extract_h2_headings(content)
    sections: list[dict] = []
    flags: list[str] = []

    if content:
        h2_positions = [
            m.start() for m in re.finditer(r"<h2[^>]*>", content, re.IGNORECASE)
        ]
        for i, pos in enumerate(h2_positions):
            end = h2_positions[i + 1] if i + 1 < len(h2_positions) else len(content)
            section_html = content[pos:end]
            section_words = _word_count(section_html)
            section_tier = _section_tier_for_words(section_words)
            sections.append({
                "heading": headings[i] if i < len(headings) else "",
                "words": section_words,
                "section_tier": section_tier,
            })
            if section_words < 100 and section_tier == "brief":
                flags.append(f"section_creuse:{headings[i][:40] if i < len(headings) else ''}")

    if not sections and words >= 500:
        flags.append("pas_de_h2_detecte")

    return {
        "article_tier": article_tier,
        "article_words": words,
        "sections": sections,
        "flags": flags,
        "version": "1.0",
    }
