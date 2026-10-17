"""Étapes de rédaction, d'extraction et de relecture du laboratoire."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import (
    ArticlePlan,
    ArticleRequest,
    CompetitorPage,
    EditorialAngle,
    FactRecord,
    ReaderIntent,
    SiteContext,
)
from .prompting import build_writer_context


class WriterCall(Protocol):
    def __call__(self, system: str, user: str) -> str: ...


class WriterOutputError(ValueError):
    """Le modèle n'a pas rendu le format attendu par l'étape."""


def _extract_json(text: str) -> dict:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise WriterOutputError("réponse sans objet JSON")
    try:
        data = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as exc:
        raise WriterOutputError(f"JSON invalide : {exc}") from exc
    if not isinstance(data, dict):
        raise WriterOutputError("le JSON doit être un objet")
    return data


@dataclass
class MarkdownWriter:
    """Produit uniquement l'article complet en Markdown."""

    call: WriterCall
    system_prompt: str

    def write(
        self,
        request: ArticleRequest,
        site: SiteContext,
        competitors: list[CompetitorPage],
        reader: ReaderIntent,
        angle: EditorialAngle,
        facts: list[FactRecord],
        plan: ArticlePlan,
    ) -> str:
        user_context = build_writer_context(request, site, competitors, reader, angle, facts, plan)
        raw = self.call(self.system_prompt, user_context)
        markdown = (raw or "").strip()
        if not markdown:
            raise WriterOutputError("réponse Markdown vide")
        return markdown


@dataclass
class StructuredExtractor:
    """Transforme séparément le Markdown et la recherche en données JSON."""

    call: WriterCall
    system_prompt: str

    def extract(self, article_markdown: str, research: str) -> dict:
        raw = self.call(
            self.system_prompt,
            "Article Markdown :\n\n" + article_markdown + "\n\nRecherche :\n\n" + research,
        )
        data = _extract_json(raw)
        required = ("title", "meta_title", "meta_description", "slug", "faq", "sources", "facts", "self_review")
        missing = [key for key in required if key not in data]
        if missing:
            raise WriterOutputError("clés absentes : " + ", ".join(missing))
        return data


@dataclass
class StyleReviewer:
    """Relit séparément le Markdown uniquement pour sa fluidité."""

    call: WriterCall
    system_prompt: str
    instruction: str

    def review(self, article_markdown: str) -> str:
        raw = self.call(self.system_prompt, self.instruction + "\n\nArticle Markdown :\n\n" + article_markdown)
        reviewed = (raw or "").strip()
        if not reviewed:
            raise WriterOutputError("relecture Markdown vide")
        return reviewed


def load_lab_prompt() -> str:
    path = Path(__file__).resolve().parents[1] / "AGENT_WRITER_PROMPT.md"
    return path.read_text(encoding="utf-8")
