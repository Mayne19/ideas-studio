from __future__ import annotations

import re
from urllib.parse import urlparse

from app.schemas.seo_workflow import SEOFinalChecklist, asdict
from app.services.seo.helpers import (
    strip_html,
    extract_headings_from_html,
    detect_isolated_h3,
    detect_h2_directly_followed_by_h3,
)

_ANCHOR_RE = re.compile(r"<a\b[^>]*\bhref\s*=\s*[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE | re.DOTALL)


def count_links_in_content(content: str | None) -> tuple[int, int]:
    """Compte les liens réellement insérés dans le contenu HTML.

    Retourne (liens_internes, liens_externes) :
    - interne = lien relatif vers une autre page du site (/articles/..., /blog/...)
    - externe = lien absolu (http/https) vers un domaine autre que le site courant.

    Le checklist SEO valide désormais les liens *dans l'article* et non plus
    le simple fait qu'un plan de maillage ait été calculé (un plan calculé
    mais jamais injecté dans le contenu ne compte pas)."""
    if not content:
        return 0, 0
    internal = 0
    external = 0
    for href in _ANCHOR_RE.findall(content):
        href = (href or "").strip()
        if not href:
            continue
        lowered = href.lower()
        if lowered.startswith(("http://", "https://")):
            parsed = urlparse(href)
            host = (parsed.hostname or "").lower()
            if host.endswith((".ideas-studio", "ideas-studio")):
                continue
            external += 1
        elif href.startswith("/"):
            internal += 1
    return internal, external


def check_seo_final(
    content: str | None,
    title: str | None = None,
    slug: str | None = None,
    meta_title: str | None = None,
    meta_description: str | None = None,
    keyword: str | None = None,
    faq_count: int = 0,
    internal_links: list | None = None,
    external_links: list | None = None,
    images: list | None = None,
    has_structured_data: bool = False,
    min_word_count: int | None = None,
) -> SEOFinalChecklist:
    report = SEOFinalChecklist()
    text = strip_html(content) if content else ""
    word_count = len(text.split())
    kw = (keyword or "").lower()
    internal_count, external_count = count_links_in_content(content)
    # 800 mots par défaut seulement si aucune cible de format n'est fournie —
    # une catégorie configurée en format "short" (word_count_min < 800, voir
    # article_tier_service/format_expectations) ne pouvait jamais valider ce
    # check, et l'auto-amélioration poussait alors le contenu au-delà du
    # word_count_max de la catégorie pour tenter de le satisfaire, entrant en
    # conflit avec sa propre correction de volume dans la même boucle.
    depth_target = min_word_count if min_word_count is not None else 800

    checks = [
        {"name": "title_present", "label": "Titre présent", "pass": bool(title)},
        {"name": "slug_present", "label": "Slug présent", "pass": bool(slug)},
        {"name": "meta_title_present", "label": "Meta title présent", "pass": bool(meta_title)},
        {"name": "meta_description_present", "label": "Meta description présente", "pass": bool(meta_description)},
        {"name": "keyword_in_title", "label": "Mot-clé dans le titre", "pass": kw and title and kw in title.lower()},
        {"name": "content_depth", "label": "Profondeur suffisante", "pass": word_count >= depth_target},
        {"name": "keyword_in_intro", "label": "Mot-clé dans l'introduction", "pass": kw and content and (kw in content[:500].lower() if content else False)},
        {"name": "no_isolated_h3", "label": "Pas de H3 isolé", "pass": not detect_isolated_h3(content or "")},
        {"name": "structure_valid", "label": "Structure H2/H3 correcte", "pass": len(detect_h2_directly_followed_by_h3(content or "")) == 0},
        {"name": "faq_valid", "label": "FAQ valide (2-6 questions)", "pass": faq_count == 0 or (2 <= faq_count <= 6)},
        {"name": "internal_links", "label": "Liens internes", "pass": internal_count >= 1},
        {"name": "external_links", "label": "Liens externes", "pass": external_count >= 1},
        {"name": "images_alt", "label": "Images avec alt", "pass": images is None or len(images) == 0 or all(i.get("alt_text") for i in images if i.get("image_url"))},
        {"name": "structured_data", "label": "Données structurées", "pass": has_structured_data},
    ]

    for c in checks:
        report.checks.append(c)
        if c["pass"]:
            report.passed.append(c["name"])
        else:
            report.failed.append(c["name"])
            report.recommendations.append(f"Ajouter/améliorer : {c['label']}")

    passed = len(report.passed)
    total = max(1, len(checks))
    report.score = round((passed / total) * 100, 1)

    if report.failed:
        report.manual_review_needed = True

    return report


def check_seo_final_dict(
    content: str | None = None,
    title: str | None = None,
    slug: str | None = None,
    meta_title: str | None = None,
    meta_description: str | None = None,
    keyword: str | None = None,
    faq_count: int = 0,
    internal_links: list | None = None,
    external_links: list | None = None,
    images: list | None = None,
    has_structured_data: bool = False,
    min_word_count: int | None = None,
) -> dict:
    return asdict(check_seo_final(
        content, title, slug, meta_title, meta_description,
        keyword, faq_count, internal_links, external_links, images,
        has_structured_data=has_structured_data,
        min_word_count=min_word_count,
    ))
