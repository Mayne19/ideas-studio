from __future__ import annotations

import re

from app.schemas.seo_workflow import ImagePlan, asdict
from app.services.seo.adapters.image_sourcing_adapter import image_sourcing_adapter


def build_image_plan(keyword: str, outline: dict | None = None) -> tuple[ImagePlan, list[dict]]:
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
    results = image_sourcing_adapter.search(keyword, limit=5)
    for r in results:
        plan.images.append(r)
        sources.append(r)

    if not plan.images:
        plan.limitations.append("No images found for keyword")

    return plan, sources


def build_image_plan_dict(keyword: str, outline: dict | None = None) -> dict:
    plan, sources = build_image_plan(keyword, outline)
    return {"image_plan": asdict(plan), "image_sources": sources}


_H2_RE = re.compile(r"(</h2>)", re.IGNORECASE)


def _image_html(source: dict) -> str:
    alt = (source.get("alt_text") or "").replace('"', "&quot;")
    author = source.get("author") or "Unsplash"
    source_url = source.get("source_url") or "https://unsplash.com"
    source_name = source.get("source_name") or "Unsplash"
    return (
        f'<img src="{source.get("image_url")}" alt="{alt}">'
        f'<p><em>Photo par <a href="{source_url}" target="_blank" rel="nofollow noopener">{author}</a>'
        f" sur {source_name}</em></p>"
    )


def insert_images_in_content(content: str, image_sources: list[dict]) -> str:
    """Insère une image après chaque section H2, dans l'ordre, jusqu'à
    épuisement des images disponibles — avec attribution obligatoire
    (licence Unsplash : usage_rights_status == 'free_with_attribution')."""
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
