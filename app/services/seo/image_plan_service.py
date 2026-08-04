from __future__ import annotations

import re

from app.schemas.seo_workflow import ImagePlan, asdict
from app.services.seo.adapters.image_sourcing_adapter import image_sourcing_adapter


def build_image_plan(keyword: str, outline: dict | None = None) -> tuple[ImagePlan, list[dict]]:
    """Une recherche Unsplash sur le seul mot-clé principal (ex: "CMS") renvoie
    des photos décoratives génériques puisque le mot-clé SEO n'est pas un
    concept visuel — chaque image est donc cherchée sur le titre H2 de la
    section où elle sera insérée (insert_images_in_content associe images et
    sections dans le même ordre), avec repli sur le mot-clé si l'outline est
    absent ou vide."""
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
    queries = section_headings or [keyword]

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
