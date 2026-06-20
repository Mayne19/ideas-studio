from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def build_structured_data(
    title: str | None = None,
    slug: str | None = None,
    meta_title: str | None = None,
    meta_description: str | None = None,
    excerpt: str | None = None,
    author: str | None = None,
    published_at: datetime | None = None,
    updated_at: datetime | None = None,
    category: str | None = None,
    content: str | None = None,
    faq_json: str | None = None,
    cover_image_url: str | None = None,
    canonical_url: str | None = None,
    site_name: str | None = None,
    organization_name: str | None = None,
) -> dict[str, Any]:
    schemas: list[dict] = []
    warnings: list[str] = []

    headline = meta_title or title or ""
    description = meta_description or excerpt or ""

    if not headline:
        warnings.append("Titre manquant pour les données structurées.")

    # BlogPosting / Article
    if headline:
        blog_posting: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
        }
        if headline:
            blog_posting["headline"] = headline
        if description:
            blog_posting["description"] = description
        if published_at:
            blog_posting["datePublished"] = published_at.isoformat()
        if updated_at:
            blog_posting["dateModified"] = updated_at.isoformat()
        if author:
            blog_posting["author"] = {
                "@type": "Person",
                "name": author,
            }
        else:
            warnings.append("Auteur manquant pour les données structurées.")
        if cover_image_url:
            blog_posting["image"] = cover_image_url
        if canonical_url:
            blog_posting["mainEntityOfPage"] = canonical_url
        elif slug:
            blog_posting["mainEntityOfPage"] = slug
        if category:
            blog_posting["articleSection"] = category

        schemas.append(blog_posting)

    # FAQPage
    if faq_json:
        try:
            faq_data = json.loads(faq_json) if isinstance(faq_json, str) else faq_json
            if isinstance(faq_data, list) and len(faq_data) >= 2:
                main_entity: list[dict] = []
                for item in faq_data:
                    q = item.get("question", "") if isinstance(item, dict) else ""
                    a = item.get("answer", "") if isinstance(item, dict) else ""
                    if q and a:
                        main_entity.append({
                            "@type": "Question",
                            "name": q,
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": a,
                            },
                        })
                if len(main_entity) >= 2:
                    schemas.append({
                        "@context": "https://schema.org",
                        "@type": "FAQPage",
                        "mainEntity": main_entity,
                    })
        except (json.JSONDecodeError, TypeError, AttributeError):
            warnings.append("FAQ JSON invalide pour données structurées.")

    # BreadcrumbList
    if category:
        schemas.append({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": category, "item": canonical_url or slug or ""},
            ],
        })

    # Organization (if name provided)
    if organization_name or site_name:
        org: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "Organization",
        }
        if organization_name:
            org["name"] = organization_name
        elif site_name:
            org["name"] = site_name
        schemas.append(org)

    if not schemas:
        warnings.append("Aucune donnée structurée générée.")

    has_faq = False
    if faq_json:
        try:
            faq_data = json.loads(faq_json) if isinstance(faq_json, str) else faq_json
            has_faq = isinstance(faq_data, list) and len(faq_data) >= 2
        except (json.JSONDecodeError, TypeError):
            has_faq = False

    return {
        "has_faq": has_faq,
        "schemas": schemas,
        "status": "generated" if schemas else "empty",
        "warnings": warnings,
        "schema_count": len(schemas),
    }
