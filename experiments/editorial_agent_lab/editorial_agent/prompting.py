"""Composition du contexte transmis au rédacteur unique."""

from __future__ import annotations

import json

from .models import (
    ArticlePlan,
    ArticleRequest,
    CompetitorPage,
    EditorialAngle,
    FactRecord,
    ReaderIntent,
    SiteContext,
)


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
            "L'introduction reste inférieure ou égale à 10 %.",
            "Le call out En résumé vient entre l'introduction et le premier H2.",
            "La FAQ est définie par le plan et ne répète pas le corps.",
            "Ne lance aucune réécriture automatique pour une alerte de similarité.",
            "Rends uniquement le JSON demandé, sans article de référence à imiter.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
