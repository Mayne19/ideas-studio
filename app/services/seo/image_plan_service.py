from __future__ import annotations

import re

from app.schemas.seo_workflow import ImagePlan, asdict
from app.services.seo.adapters.image_sourcing_adapter import image_sourcing_adapter


# Titres H2 purement structurels, sans contenu visuel propre (numérotation
# d'étapes, questions génériques...) — chercher une image dessus seuls
# renvoie n'importe quoi ("Qu'est-ce que c'est ?" -> panneau "ouch" trouvé
# en production). Combinés au mot-clé principal, ils n'apportent rien de
# plus qu'une recherche sur le mot-clé seul.
_GENERIC_HEADING_PATTERNS = re.compile(
    r"^(qu['’]est.ce que|pourquoi|comment\s*\??|conclusion|résumé|"
    r"étape\s*\d|astuces?|conseils?|introduction|en\s+bref|faq)\b",
    re.IGNORECASE,
)


def build_image_plan(keyword: str, outline: dict | None = None) -> tuple[ImagePlan, list[dict]]:
    """Une recherche Unsplash sur le seul titre H2 (ex: "Qu'est-ce que c'est ?")
    renvoie des photos sans rapport dès que le titre est structurel plutôt que
    visuellement concret — le mot-clé principal de l'article ancre donc
    toujours la requête, complété par le titre H2 seulement s'il ajoute un
    terme concret (pas une simple formule de structure)."""
    plan = ImagePlan()
    sources: list[dict] = []

    if not image_sourcing_adapter.configured:
        plan.provider_configured = False
        plan.limitations = [
            "Image provider not configured (UNSPLASH_ACCESS_KEY missing)",
            "No images sourced automatically",
        ]
        return plan, sources

    plan.provider_configured = True

    section_headings = [
        s.get("heading") for s in (outline or {}).get("sections", [])
        if isinstance(s, dict) and s.get("heading") and s.get("level", 2) == 2
    ]
    if section_headings:
        queries = [
            keyword if _GENERIC_HEADING_PATTERNS.match(heading.strip()) else f"{keyword} {heading}"
            for heading in section_headings
        ]
    else:
        queries = [keyword]

    seen_urls: set[str] = set()
    for query in queries:
        results = image_sourcing_adapter.search(query, limit=1)
        for r in results:
            if r.get("image_url") in seen_urls:
                continue
            seen_urls.add(r.get("image_url"))
            plan.images.append(r)
            sources.append(r)
            break

    if not plan.images:
        plan.limitations.append("No images found for keyword")

    return plan, sources


def build_image_plan_dict(keyword: str, outline: dict | None = None) -> dict:
    plan, sources = build_image_plan(keyword, outline)
    return {"image_plan": asdict(plan), "image_sources": sources}


_H2_RE = re.compile(r"(</h2>)", re.IGNORECASE)


def _image_html(source: dict) -> str:
    # Licence Unsplash : gratuite, aucune attribution requise pour l'usage —
    # décision produit du 2026-08-04 de ne pas afficher de légende de crédit.
    alt = (source.get("alt_text") or "").replace('"', "&quot;")
    return f'<img src="{source.get("image_url")}" alt="{alt}">'


def insert_images_in_content(content: str, image_sources: list[dict]) -> str:
    """Insère une image après chaque section H2, dans l'ordre, jusqu'à
    épuisement des images disponibles."""
    usable = [s for s in image_sources if s.get("image_url") and s.get("usage_rights_status") == "free_with_attribution"]
    if not usable or not content:
        return content

    remaining = list(usable)

    def _replace(match: re.Match) -> str:
        if not remaining:
            return match.group(0)
        source = remaining.pop(0)
        return match.group(0) + _image_html(source)

    return _H2_RE.sub(_replace, content)
