"""Composition du contexte transmis au rédacteur unique."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .models import (
    ArticlePlan,
    ArticleRequest,
    CompetitorPage,
    EditorialAngle,
    FactRecord,
    ReaderIntent,
    SiteContext,
)


def load_system_prompt(
    *,
    site_name: str = "le site",
    site_domain: str = "ce site",
    language: str = "français",
    country: str = "France",
    today: date | None = None,
) -> str:
    """Charge le prompt du laboratoire et remplace uniquement ses variables."""

    path = Path(__file__).resolve().parents[1] / "AGENT_WRITER_PROMPT.md"
    text = path.read_text(encoding="utf-8")
    values = {
        "{site_name}": site_name or "le site",
        "{site_domain}": site_domain or "ce site",
        "{language}": language or "français",
        "{country}": country or "France",
        "{date}": (today or date.today()).isoformat(),
    }
    for key, value in values.items():
        text = text.replace(key, value)
    return text


def build_writer_context(
    request: ArticleRequest,
    site: SiteContext,
    competitors: list[CompetitorPage],
    reader: ReaderIntent,
    angle: EditorialAngle,
    facts: list[FactRecord],
    plan: ArticlePlan,
) -> str:
    """Produit un contexte inspectable, stable et sans texte de référence copié."""

    payload = {
        "request": request.model_dump(mode="json"),
        "site": site.model_dump(mode="json"),
        "reader": reader.model_dump(mode="json"),
        "angle": angle.model_dump(mode="json"),
        "competitors": [competitor.model_dump(mode="json") for competitor in competitors],
        "facts": [fact.model_dump(mode="json") for fact in facts],
        "plan": plan.model_dump(mode="json"),
        "rules": [
            "Rédige tout l'article en une seule passe.",
            "L'introduction reste courte et ne dépasse jamais 15 %.",
            "Le call out En résumé vient entre l'introduction et le premier H2.",
            "La FAQ est définie par le plan et ne répète pas le corps.",
            "Ne lance aucune réécriture automatique pour une alerte de similarité.",
            "Rends uniquement l'article complet en Markdown, sans article de référence à imiter.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
