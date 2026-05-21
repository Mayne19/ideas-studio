from __future__ import annotations

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
