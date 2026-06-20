from __future__ import annotations

import re
from app.schemas.seo_workflow import SEOFinalChecklist, asdict
from app.services.seo.helpers import (
    strip_html,
    extract_headings_from_html,
    detect_isolated_h3,
    detect_h2_directly_followed_by_h3,
)


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
) -> SEOFinalChecklist:
    report = SEOFinalChecklist()
    text = strip_html(content) if content else ""
    word_count = len(text.split())
    kw = (keyword or "").lower()

    checks = [
        {"name": "title_present", "label": "Titre présent", "pass": bool(title)},
        {"name": "slug_present", "label": "Slug présent", "pass": bool(slug)},
        {"name": "meta_title_present", "label": "Meta title présent", "pass": bool(meta_title)},
        {"name": "meta_description_present", "label": "Meta description présente", "pass": bool(meta_description)},
        {"name": "keyword_in_title", "label": "Mot-clé dans le titre", "pass": kw and title and kw in title.lower()},
        {"name": "content_depth", "label": "Profondeur suffisante", "pass": word_count >= 800},
        {"name": "keyword_in_intro", "label": "Mot-clé dans l'introduction", "pass": kw and content and (kw in content[:500].lower() if content else False)},
        {"name": "no_isolated_h3", "label": "Pas de H3 isolé", "pass": not detect_isolated_h3(content or "")},
        {"name": "structure_valid", "label": "Structure H2/H3 correcte", "pass": len(detect_h2_directly_followed_by_h3(content or "")) == 0},
        {"name": "faq_valid", "label": "FAQ valide (2-6 questions)", "pass": faq_count == 0 or (2 <= faq_count <= 6)},
        {"name": "internal_links", "label": "Liens internes", "pass": bool(internal_links)},
        {"name": "external_links", "label": "Liens externes", "pass": bool(external_links)},
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
) -> dict:
    return asdict(check_seo_final(
        content, title, slug, meta_title, meta_description,
        keyword, faq_count, internal_links, external_links, images,
        has_structured_data=has_structured_data,
    ))
