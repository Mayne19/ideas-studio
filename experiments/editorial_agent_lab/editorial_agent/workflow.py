"""Orchestration du processus éditorial isolé."""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    ArticleRequest,
    CompetitorPage,
    GenerationReport,
    GenerationResult,
    ReaderIntent,
    SiteContext,
)
from .ports import ArticleWriter, EditorialPlanner, ResearchProvider, SimilarityProvider
from .validators import validate_draft, validate_facts, validate_plan


@dataclass
class EditorialAgent:
    """Agent applicatif avec dépendances injectées."""

    research: ResearchProvider
    planner: EditorialPlanner
    writer: ArticleWriter
    similarity: SimilarityProvider

    def generate(self, request: ArticleRequest, context: SiteContext) -> GenerationResult:
        urls = self.research.search_competitors(request.keyword, context.domain, limit=3)
        competitors = [
            CompetitorPage(
                url=url,
                title=f"Concurrent {index}",
                content=self.research.fetch_page(url),
            )
            for index, url in enumerate(urls, start=1)
        ]
        reader = self._infer_reader(request, competitors)
        facts = self.research.find_facts(request.keyword, reader)
        plan = self.planner.build_plan(request, context, competitors, reader, facts)
        draft = self.writer.write(request, context, competitors, reader, facts, plan)

        issues = validate_plan(plan)
        issues.extend(validate_facts(facts))
        issues.extend(validate_draft(draft, plan))
        similarity_findings = self.similarity.scan(
            draft.content_html,
            [str(url) for url in urls],
        )

        report = GenerationReport(
            keyword=request.keyword,
            searches=1,
            pages_read=len(competitors),
            blocking_issues=[issue for issue in issues if issue.blocking],
            warnings=[issue for issue in issues if not issue.blocking],
            similarity_findings=similarity_findings,
        )
        return GenerationResult(plan=plan, draft=draft, report=report)

    @staticmethod
    def _infer_reader(request: ArticleRequest, competitors: list[CompetitorPage]) -> ReaderIntent:
        missing = (
            competitors[0].missing_topics[0]
            if competitors and competitors[0].missing_topics
            else "une réponse concrète"
        )
        return ReaderIntent(
            real_question=f"Comment répondre utilement à : {request.keyword} ?",
            reader_level="débutant",
            main_problem=request.keyword,
            likely_trap=missing,
            concrete_gain="savoir quoi faire après la lecture",
        )
