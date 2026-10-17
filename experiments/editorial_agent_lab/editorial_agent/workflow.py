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
from .angle import propose_angle, validate_angle
from .fact_ledger import assign_fact_ids
from .ports import ArticleWriter, CompetitorAnalyzer, EditorialPlanner, ResearchProvider, SimilarityProvider
from .planning import build_reader_intent, validate_competitor_dossier, validate_plan_coverage, validate_source_diversity
from .validators import validate_draft, validate_facts, validate_plan


@dataclass
class EditorialAgent:
    """Agent applicatif avec dépendances injectées."""

    research: ResearchProvider
    competitor_analyzer: CompetitorAnalyzer
    planner: EditorialPlanner
    writer: ArticleWriter
    similarity: SimilarityProvider

    def generate(self, request: ArticleRequest, context: SiteContext) -> GenerationResult:
        urls = self.research.search_competitors(request.keyword, context.domain, limit=3)
        raw_competitors = [
            CompetitorPage(
                url=url,
                title=f"Concurrent {index}",
                content=self.research.fetch_page(url),
            )
            for index, url in enumerate(urls, start=1)
        ]
        competitors = self.competitor_analyzer.analyze(raw_competitors)
        reader = build_reader_intent(request.keyword, competitors)
        facts = assign_fact_ids(self.research.find_facts(request.keyword, reader))
        angle = propose_angle(reader, competitors, [fact.fact_id for fact in facts])
        plan = self.planner.build_plan(request, context, competitors, reader, angle, facts)
        draft = self.writer.write(request, context, competitors, reader, angle, facts, plan)

        issues = validate_competitor_dossier(competitors)
        issues.extend(validate_angle(angle, {fact.fact_id for fact in facts}))
        issues.extend(validate_plan(plan))
        issues.extend(validate_plan_coverage(plan))
        issues.extend(validate_facts(facts))
        issues.extend(validate_source_diversity(facts, urls))
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
        return GenerationResult(angle=angle, plan=plan, draft=draft, report=report)
