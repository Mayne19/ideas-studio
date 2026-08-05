from __future__ import annotations

import re

from app.schemas.seo_workflow import ImagePlan, asdict
from app.services.seo.adapters.image_sourcing_adapter import image_sourcing_adapter, brave_image_search_provider


def build_image_plan(
    keyword: str,
    outline: dict | None = None,
    db=None,
    project_id: str | None = None,
) -> tuple[ImagePlan, list[dict]]:
    """Plan d'images par section, avec trois stratégies de sourcing distinctes :
    - sujet abstrait/technique -> pas d'image (Unsplash n'a rien de pertinent
      pour "robots.txt" ou "Comment choisir ?")
    - outil/marque identifié -> image cherchée sur le domaine officiel de la
      marque (ex: recherche restreinte à canva.com pour un article sur Canva),
      jamais sur un site concurrent de theslash
    - sujet concret générique -> banque de photos (Unsplash), comme avant

    La décision par section vient de plan_section_images() (agent LLM
    media_planner) ; sans provider LLM configuré, aucune image n'est
    proposée plutôt que de deviner heuristiquement (mieux vaut zéro image
    qu'une image hors sujet)."""
    plan = ImagePlan()
    sources: list[dict] = []

    section_headings = [
        s.get("heading") for s in (outline or {}).get("sections", [])
        if isinstance(s, dict) and s.get("heading") and s.get("level", 2) == 2
    ]
    if not section_headings:
        plan.limitations.append("No sections available to plan images against")
        return plan, sources

    from app.services.agents.agent_services import plan_section_images
    section_plan = plan_section_images(section_headings, keyword, db=db, project_id=project_id)

    if section_plan.get("status") != "success":
        plan.provider_configured = False
        plan.limitations = [
            "Image planning LLM not available — no images sourced automatically "
            "(no fallback to keyword-based search: a wrong image is worse than none)",
        ]
        return plan, sources

    competitor_domains = _get_competitor_domains(db, project_id)
    plan.provider_configured = True

    seen_urls: set[str] = set()
    for section in section_plan.get("sections", []):
        if not isinstance(section, dict):
            continue
        decision = section.get("decision")

        if decision == "brand":
            brand_domain = (section.get("brand_domain") or "").strip().lower()
            brand_name = section.get("brand_name") or brand_domain
            if not brand_domain or _is_competitor_domain(brand_domain, competitor_domains):
                continue
            if not brave_image_search_provider.configured:
                continue
            results = brave_image_search_provider.search_on_domain(brand_name, brand_domain, limit=1)
        elif decision == "stock":
            stock_query = section.get("stock_query") or section.get("heading") or keyword
            if not image_sourcing_adapter.configured:
                continue
            results = image_sourcing_adapter.search(stock_query, limit=1)
        else:
            # "skip" ou décision inconnue : aucune image pour cette section.
            continue

        for r in results:
            if not r.get("image_url") or r["image_url"] in seen_urls:
                continue
            if r.get("source_name") and _is_competitor_domain(r["source_name"], competitor_domains):
                continue
            seen_urls.add(r["image_url"])
            plan.images.append(r)
            sources.append(r)
            break

    if not plan.images:
        plan.limitations.append("No images found (all sections skipped or no results)")

    return plan, sources


def _get_competitor_domains(db, project_id: str | None) -> set[str]:
    """Domaines à ne jamais utiliser comme source d'image de marque — lus
    depuis editorial_profiles.rules.competitor_domains (JSON libre, pas de
    colonne dédiée), configurable par projet sans migration de schéma."""
    if db is None or not project_id:
        return set()
    try:
        from app.models.core import Project
        project = db.get(Project, project_id)
        profile = project.active_editorial_profile if project else None
        domains = (profile.rules or {}).get("competitor_domains", []) if profile else []
        return {d.strip().lower() for d in domains if isinstance(d, str) and d.strip()}
    except Exception:
        return set()


def _is_competitor_domain(domain_or_url: str, competitor_domains: set[str]) -> bool:
    if not competitor_domains:
        return False
    lowered = domain_or_url.lower()
    return any(comp in lowered for comp in competitor_domains)


def build_image_plan_dict(
    keyword: str,
    outline: dict | None = None,
    db=None,
    project_id: str | None = None,
) -> dict:
    plan, sources = build_image_plan(keyword, outline, db=db, project_id=project_id)
    return {"image_plan": asdict(plan), "image_sources": sources}


_H2_RE = re.compile(r"(</h2>)", re.IGNORECASE)


def _image_html(source: dict) -> str:
    # Licence Unsplash : gratuite, aucune attribution requise pour l'usage —
    # décision produit du 2026-08-04 de ne pas afficher de légende de crédit.
    # Pour les images de marque (usage_rights_status == "official_source"),
    # le statut d'usage n'est pas garanti (dépend des conditions du site
    # source) : on garde le nom/alt natif de l'image tel que publié par la
    # marque plutôt que d'en inventer un, l'éditeur reste responsable de
    # vérifier le droit d'usage avant publication finale.
    alt = (source.get("alt_text") or "").replace('"', "&quot;")
    return f'<img src="{source.get("image_url")}" alt="{alt}">'


def insert_images_in_content(content: str, image_sources: list[dict]) -> str:
    """Insère une image après chaque section H2, dans l'ordre, jusqu'à
    épuisement des images disponibles. Accepte les images libres de droits
    Unsplash (free_with_attribution) et les images de marque sourcées sur un
    domaine officiel (official_source, cf. plan_section_images)."""
    usable = [
        s for s in image_sources
        if s.get("image_url") and s.get("usage_rights_status") in ("free_with_attribution", "official_source")
    ]
    if not usable or not content:
        return content

    remaining = list(usable)

    def _replace(match: re.Match) -> str:
        if not remaining:
            return match.group(0)
        source = remaining.pop(0)
        return match.group(0) + _image_html(source)

    return _H2_RE.sub(_replace, content)
