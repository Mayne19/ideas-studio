"""Rédacteur unique en une passe, indépendant du fournisseur de modèle."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import (
    ArticleDraft,
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
    """Le modèle n'a pas rendu le contrat JSON attendu."""


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
class SinglePassWriter:
    """Un appel au modèle, puis validation du contrat, sans correction cachée."""

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
    ) -> ArticleDraft:
        user_context = build_writer_context(request, site, competitors, reader, angle, facts, plan)
        raw = self.call(self.system_prompt, user_context)
        return ArticleDraft.model_validate(_extract_json(raw))


def load_lab_prompt() -> str:
    path = Path(__file__).resolve().parents[1] / "AGENT_WRITER_PROMPT.md"
    return path.read_text(encoding="utf-8")
