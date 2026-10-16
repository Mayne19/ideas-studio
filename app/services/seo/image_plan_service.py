from __future__ import annotations

import re
from html import escape, unescape

from app.schemas.seo_workflow import ImagePlan, asdict
from app.services.seo.adapters.image_sourcing_adapter import get_brave_image_search_provider, get_image_sourcing_adapter


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
    brave_image_search_provider = get_brave_image_search_provider(project_id)
    image_sourcing_adapter = get_image_sourcing_adapter(project_id)

    seen_urls: set[str] = set()
    for section in section_plan.get("sections", []):
        if not isinstance(section, dict):
            continue
        decision = section.get("decision")
        section_heading = section.get("heading") or ""

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
            r["section_heading"] = section_heading
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


_H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
_P_END_RE = re.compile(r"</p\s*>", re.IGNORECASE)
_FIRST_P_RE = re.compile(r"<p[^>]*>(.*?)</p\s*>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")

UNSPLASH_UTM = "utm_source=ideas_studio&utm_medium=referral"
UNSPLASH_HOME_URL = f"https://unsplash.com/?{UNSPLASH_UTM}"


def _strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(_TAG_RE.sub("", value or ""))).strip()


def _with_utm(url: str) -> str:
    return f"{url}{'&' if '?' in url else '?'}{UNSPLASH_UTM}"


def image_alt_text(source: dict) -> str:
    """Alt rédigé dans la langue de l'article (alt_localized, cf.
    localize_image_alts) ; à défaut, le titre de la section illustrée.
    Jamais la description anglaise brute d'Unsplash (alt_text)."""
    return _strip_tags(source.get("alt_localized") or "") or _strip_tags(source.get("section_heading") or "")


def is_unsplash_source(source: dict) -> bool:
    return (source.get("source_name") or "").lower() == "unsplash"


def _unsplash_caption(source: dict) -> str:
    """Attribution exigée par les Unsplash API Guidelines : photographe et
    Unsplash, tous deux liés avec les paramètres UTM de l'application."""
    author = (source.get("author") or "").strip()
    profile = source.get("author_url") or source.get("source_url")
    if not author or not profile:
        return ""
    return (
        "<figcaption>Photo : "
        f'<a href="{escape(_with_utm(profile), quote=True)}">{escape(author)}</a>'
        f' sur <a href="{escape(UNSPLASH_HOME_URL, quote=True)}">Unsplash</a>'
        "</figcaption>"
    )


def _image_html(source: dict) -> str:
    # Les photos Unsplash portent une légende de crédit (photographe +
    # Unsplash, Unsplash API Guidelines). Pour les images de marque
    # (usage_rights_status == "official_source"), le statut d'usage n'est pas
    # garanti (dépend des conditions du site source) : l'éditeur reste
    # responsable de vérifier le droit d'usage avant publication finale.
    alt = escape(image_alt_text(source), quote=True)
    src = escape(source.get("image_url") or "", quote=True)
    caption = _unsplash_caption(source) if is_unsplash_source(source) else ""
    return f'<figure><img src="{src}" alt="{alt}">{caption}</figure>'


def _normalize_heading(heading: str) -> str:
    return _strip_tags(heading).lower().rstrip("?").strip()


def _usable_sources(image_sources: list[dict]) -> list[dict]:
    return [
        s for s in image_sources
        if s.get("image_url") and s.get("usage_rights_status") in ("free_with_attribution", "official_source")
    ]


def _sections(content: str) -> list[tuple[re.Match, int]]:
    """(titre H2, fin de section) — une section court jusqu'au H2 suivant."""
    matches = list(_H2_RE.finditer(content))
    return [
        (m, matches[i + 1].start() if i + 1 < len(matches) else len(content))
        for i, m in enumerate(matches)
    ]


def section_first_paragraph(content: str, heading: str, max_length: int = 300) -> str:
    """Texte du premier paragraphe de la section H2 correspondant à `heading`
    (contexte de rédaction de l'alt), vide si la section est introuvable."""
    target = _normalize_heading(heading)
    if not target or not content:
        return ""
    for match, end in _sections(content):
        current = _normalize_heading(match.group(1))
        if current and (target in current or current in target):
            paragraph = _FIRST_P_RE.search(content, match.end(), end)
            return _strip_tags(paragraph.group(1))[:max_length] if paragraph else ""
    return ""


def _insertion_point(content: str, h2_end: int, section_end: int) -> int:
    """Juste après le premier paragraphe de la section ; à défaut (section
    sans paragraphe), juste après le titre H2."""
    paragraph_end = _P_END_RE.search(content, h2_end, section_end)
    return paragraph_end.end() if paragraph_end else h2_end


def insert_images_in_content(content: str, image_sources: list[dict]) -> str:
    """Insère chaque image après le premier paragraphe de la section H2 à
    laquelle elle a été planifiée (appariement par titre de section), dans un
    <figure> avec légende de crédit pour Unsplash. Une image sans section
    correspondante va dans la première section restée sans image. Chaque
    source réellement insérée est marquée `inserted=True` (suivi des
    téléchargements Unsplash et choix de l'image de couverture). Accepte les
    images libres de droits Unsplash (free_with_attribution) et les images
    de marque sourcées sur un domaine officiel (official_source, cf.
    plan_section_images)."""
    usable = _usable_sources(image_sources)
    if not usable or not content:
        return content

    sections = _sections(content)
    if not sections:
        return content

    pending = list(usable)
    assigned: dict[int, dict] = {}

    for idx, (match, _end) in enumerate(sections):
        target = _normalize_heading(match.group(1))
        for pos, source in enumerate(pending):
            planned = _normalize_heading(source.get("section_heading") or "")
            if planned and target and (planned in target or target in planned):
                assigned[idx] = pending.pop(pos)
                break

    # Images restantes (section planifiée absente du contenu final) :
    # réparties dans les sections encore sans image, dans l'ordre.
    for idx in range(len(sections)):
        if not pending:
            break
        if idx not in assigned:
            assigned[idx] = pending.pop(0)

    # Insertion de la fin vers le début : les positions déjà calculées
    # restent valides.
    for idx in sorted(assigned, reverse=True):
        match, end = sections[idx]
        source = assigned[idx]
        point = _insertion_point(content, match.end(), end)
        content = content[:point] + _image_html(source) + content[point:]
        source["inserted"] = True

    return content


def localize_image_alts(
    content: str,
    image_sources: list[dict],
    language: str,
    keyword: str = "",
    db=None,
    project_id: str | None = None,
) -> None:
    """Renseigne `alt_localized` sur chaque image utilisable, rédigé dans la
    langue de l'article par UN seul appel LLM court (agent media_planner) qui
    décrit l'image dans le contexte de sa section. Sans provider ou en cas
    d'échec, image_alt_text() retombe sur le titre de la section."""
    usable = [s for s in _usable_sources(image_sources) if not s.get("alt_localized")]
    if not usable:
        return
    items = [
        {
            "section_heading": _strip_tags(s.get("section_heading") or ""),
            "section_excerpt": section_first_paragraph(content, s.get("section_heading") or ""),
            "photo_hint": _strip_tags(s.get("alt_text") or "")[:200],
        }
        for s in usable
    ]
    try:
        from app.services.agents.agent_services import write_image_alt_texts
        alts = write_image_alt_texts(items, language, keyword, db=db, project_id=project_id)
    except Exception:
        alts = []
    for source, alt in zip(usable, alts):
        alt = _strip_tags(alt or "")[:150]
        if alt:
            source["alt_localized"] = alt
