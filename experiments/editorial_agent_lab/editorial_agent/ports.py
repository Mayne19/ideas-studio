"""Ports externes du noyau éditorial."""

from __future__ import annotations

from typing import Protocol

from .models import (
    ArticleDraft,
    ArticlePlan,
    ArticleRequest,
    CompetitorPage,
    FactRecord,
    ReaderIntent,
    SiteContext,
)


class ResearchProvider(Protocol):
    def search_competitors(self, keyword: str, domain: str, limit: int = 3) -> list[str]: ...

    def fetch_page(self, url: str) -> str: ...

    def find_facts(self, keyword: str, reader: ReaderIntent) -> list[FactRecord]: ...


class EditorialPlanner(Protocol):
    def build_plan(
        self,
        request: ArticleRequest,
        context: SiteContext,
        competitors: list[CompetitorPage],
        reader: ReaderIntent,
        facts: list[FactRecord],
    ) -> ArticlePlan: ...


class ArticleWriter(Protocol):
    def write(
        self,
        request: ArticleRequest,
        context: SiteContext,
        competitors: list[CompetitorPage],
        reader: ReaderIntent,
        facts: list[FactRecord],
        plan: ArticlePlan,
    ) -> ArticleDraft: ...


class SimilarityProvider(Protocol):
    def scan(self, content_html: str, sources: list[str]) -> list[dict[str, object]]: ...
