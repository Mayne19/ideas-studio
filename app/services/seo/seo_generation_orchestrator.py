from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.agents.agent_router import AgentRouter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Article, ArticleRevision, ArticleScore, ArticleSeo, Category
from app.models.core import Project
from app.models.ai import WorkflowRun
from app.models.reference import ArticleStatus, RevisionSource, RunStatus, WorkflowPhase, set_article_status, set_run_status
from app.schemas.seo_workflow import asdict
from app.services.log_service import log_step
from app.services.providers.llm_provider import LLMProvider, GenerationFailedError
from app.services.providers.search_provider import SearchProvider as SearchProviderType
from app.core.utils import calculate_reading_time_minutes, calculate_word_count, generate_unique_slug, slugify

from app.services.seo.artifacts import save_artifact, get_latest_artifact
from app.services.seo.helpers import safe_json_dump, safe_json_load
from app.services.seo.project_context_service import build_project_context_dict
from app.services.seo.category_strategy_service import compute_category_strategy_dict
from app.services.seo.cannibalization_service import check_cannibalization_dict
from app.services.seo.intent_analysis_service import analyze_intent_dict
from app.services.seo.research_brief_service import build_research_brief_dict
from app.services.seo.source_quality_service import validate_sources
from app.services.seo.keyword_brief_service import build_keyword_brief_dict
from app.services.seo.editorial_angle_service import define_editorial_angle_dict
from app.services.seo.article_outline_planner import build_outline_dict
from app.services.seo.image_plan_service import build_image_plan_dict
from app.services.seo.callout_plan_service import build_callout_plan_dict
from app.services.seo.faq_plan_service import build_faq_plan_dict, generate_faq_list
from app.services.seo.internal_link_service import build_internal_link_plan_dict
from app.services.seo.external_link_service import build_external_link_plan_dict
from app.services.seo.language_quality_service import check_language_quality_dict
from app.services.seo.originality_service import check_originality_dict
from app.services.seo.humanization_service import check_humanization_dict
from app.services.seo.eeat_service import check_eeat_dict
from app.services.seo.editorial_quality_gate import check_editorial_quality_dict
from app.services.seo.seo_final_checklist_service import check_seo_final_dict
from app.services.seo.seo_review_service import build_aggregated_seo_review, build_review_error_report, run_and_store_seo_review
from app.services.seo.generation_report_service import build_generation_report_dict
from app.services.seo.adapters.serp_adapter import serp_adapter
from app.services.seo.adapters.trends_adapter import trends_adapter
from app.services.seo.adapters.image_sourcing_adapter import image_sourcing_adapter
from app.services.seo.adapters.language_adapter import language_adapter
from app.services.seo.adapters.content_extraction_adapter import content_extraction_adapter
from app.services.seo.adapters.scrapling_adapter import scrapling_adapter
from app.services.seo.adapters.originality_adapter import originality_adapter as orig_adapter
from app.services.seo.adapters.readability_adapter import readability_adapter
from app.services.seo.adapters.google_watch_adapter import google_watch_adapter


class WritingCancelledError(RuntimeError):
    """Levée quand l'utilisateur demande l'annulation d'une rédaction en cours."""


# Score global visé : sert à la fois de seuil de déclenchement et de condition
# d'arrêt du cycle d'auto-amélioration (les deux doivent rester identiques).
AUTO_IMPROVE_SCORE_TARGET = 90


class _DraftArticle:
    """Support de rédaction en mémoire — content.articles/article_revisions
    n'ont plus de colonnes plates (content/title/faq_json/...). Les champs de
    révision sont accumulés ici pendant tout le pipeline puis matérialisés en
    une seule ArticleRevision par _persist_revision(), voir REPRENDRE-LA-MAIN.md
    §6 étape 6 (content.article_revisions = historique, jamais de mutation en
    place d'une révision existante)."""

    def __init__(self, article: Article):
        self.article = article
        self.title: str = ""
        self.excerpt: str | None = None
        self.content: str | None = None
        self.faq: list = []
        self.callouts: list = []
        self.word_count: int = 0
        self.reading_time_minutes: int | None = None
        self.meta_title: str | None = None
        self.meta_description: str | None = None
        self.keyword: str = ""
        self.audience: str | None = None
        self.angle: str | None = None
        self.author_name: str | None = None
        self.structured_data_json: list | None = None

    @property
    def faq_json(self):
        return self.faq

    def __getattr__(self, name):
        return getattr(self.article, name)


class SEOGenerationOrchestrator:
    def __init__(
        self,
        db: Session,
        project_id: str,
        llm: LLMProvider,
        search: SearchProviderType,
        agent_router: Any | None = None,
    ):
        self.db = db
        self.project_id = project_id
        self.llm = llm
        self.search = search
        self.agent_router = agent_router
        self.project = db.get(Project, project_id)
        self.steps_completed: list[str] = []
        self.errors: list[str] = []
        self.limitations: list[str] = []
        self.tools_used: list[str] = []
        self.tools_not_configured: list[str] = []
        self.context: dict = {}
        self.started_at = perf_counter()
        self.workflow_run: WorkflowRun | None = None

    def _log(self, message: str, level: str = "info", step: str | None = None, article_id: str | None = None):
        log_step(self.db, self.project_id, message, level=level, step=step or "orchestrator", article_id=article_id)

    def _step(self, name: str):
        self.steps_completed.append(name)
        self._log(f"Step completed: {name}", level="info", step=name)

    def _error(self, step: str, message: str):
        self.errors.append(f"[{step}] {message}")
        self._log(message, level="error", step=step)

    def _check_tools(self):
        if serp_adapter.configured:
            self.tools_used.append("serpapi")
        else:
            self.tools_not_configured.append("serpapi")
            self.limitations.append("SERP provider not configured (SERP_API_KEY missing)")

    def _ensure_slug(self, article: Article, title: str, keyword: str):
        if article.slug and not article.slug.startswith("idea-"):
            return
        base = slugify(title or keyword or "article")
        existing = {
            row[0]
            for row in self.db.execute(
                select(Article.slug).where(
                    Article.project_id == self.project_id,
                    Article.id != article.id,
                    Article.slug.like(f"{base}%"),
                )
            ).all()
        }
        article.slug = generate_unique_slug(base, existing)

    def _get_category_name(self, category_id: str | None) -> str:
        if not category_id:
            return ""
        cat = self.db.get(Category, category_id)
        return cat.name if cat else ""

    def _save(self, article_id: str, agent_key: str, payload: Any):
        save_artifact(self.db, article_id, agent_key, payload if isinstance(payload, dict) else {"value": payload})

    def _get(self, article_id: str, agent_key: str) -> dict | None:
        return get_latest_artifact(self.db, article_id, agent_key)

    def generate_full_article(
        self,
        preferred_title: str | None = None,
        keyword: str | None = None,
        category_id: str | None = None,
        audience: str | None = None,
        angle: str | None = None,
        search_intent: str | None = None,
        context_hint: str | None = None,
        include_faq: bool | None = None,
        include_callouts: bool | None = None,
        existing_article_id: str | None = None,
    ) -> Article:
        self._check_tools()

        # 1. ProjectContext
        project_context = build_project_context_dict(self.db, self.project_id)
        self.context["project_context"] = project_context
        self._step("ProjectContext")

        # 2. CategoryStrategy
        category_strategy = compute_category_strategy_dict(self.db, self.project_id)
        self.context["category_strategy"] = category_strategy
        self._step("CategoryStrategy")

        chosen_category = category_id or category_strategy.get("chosen_category_id")
        category_name = self._get_category_name(chosen_category)

        # 3. IdeaDiscovery (basic)
        idea_discovery = {
            "title": preferred_title or keyword or "",
            "category_id": chosen_category,
            "main_keyword": keyword or "",
            "secondary_keywords": [],
            "detected_intent": search_intent or "informational",
            "source": "manual" if preferred_title else "category_strategy",
            "real_research_used": False,
            "opportunity_score": 0.7,
            "confidence_score": 0.5,
            "limitations": self.limitations.copy(),
        }
        self.context["idea_discovery"] = idea_discovery
        self._step("IdeaDiscovery")

        final_title = preferred_title or idea_discovery.get("title", "Article")
        final_keyword = keyword or idea_discovery.get("main_keyword", "")

        if not final_keyword:
            final_keyword = slugify(final_title)

        # 4. CannibalizationCheck
        cannibalization = check_cannibalization_dict(
            self.db, self.project_id, final_title, final_keyword, chosen_category
        )
        self.context["cannibalization_check"] = cannibalization
        self._step("CannibalizationCheck")

        if cannibalization.get("risk_level") == "high":
            self._log(f"Cannibalization risk: {cannibalization.get('recommendation')}", level="warning", step="CannibalizationCheck")

        # 5. IntentAnalysis
        intent_analysis = analyze_intent_dict(
            final_title, final_keyword, context_hint, category_name, idea_discovery, project_context
        )
        self.context["intent_analysis"] = intent_analysis
        self._step("IntentAnalysis")

        article_type = intent_analysis.get("article_type", "evergreen_information")

        # 6. ResearchBrief
        research_brief = build_research_brief_dict(final_keyword, final_title, category_name, project_id=self.project_id)
        self.context["research_brief"] = research_brief
        self._step("ResearchBrief")

        if research_brief.get("research_status") == "available":
            self.tools_used.append("serp_research")
            # 6b. SourceQuality — validate competitor URLs via Scrapling
            try:
                validated_sources = validate_sources(research_brief.get("sources_consulted", []))
                research_brief["sources_consulted"] = validated_sources
                self.context["research_brief"] = research_brief
                self._step("SourceQuality")
            except Exception as exc:
                self._error("SourceQuality", str(exc))
        else:
            self.limitations.append("No real SERP research available")

        # 6c. HumanInsights — matière humaine réelle (Reddit, StackOverflow, Nitter, forums)
        try:
            from app.services.seo.human_insights_service import extract_human_insights
            serp_sources = research_brief.get("sources_consulted", [])
            human_insights = extract_human_insights(
                keyword=final_keyword,
                project_id=self.project_id,
                serp_results=serp_sources,
                language=getattr(self.project, "language", "fr") or "fr",
            )
            self.context["human_insights"] = human_insights
            self._step(
                f"HumanInsights — {human_insights.get('total_insights', 0)} insights "
                f"depuis {len(human_insights.get('sources_scraped', []))} sources"
            )
        except Exception as exc:
            self._error("HumanInsights", str(exc))
            self.context["human_insights"] = {}

        # 7. KeywordBrief
        keyword_brief = build_keyword_brief_dict(
            final_keyword,
            secondary_keywords=[],
            related_questions=intent_analysis.get("sub_questions"),
            intent_analysis=intent_analysis,
            research_brief=research_brief,
        )
        self.context["keyword_brief"] = keyword_brief
        self._step("KeywordBrief")

        # 8. EditorialAngle
        editorial_angle = define_editorial_angle_dict(
            final_title, final_keyword, intent_analysis, research_brief, category_name
        )
        self.context["editorial_angle"] = editorial_angle
        self._step("EditorialAngle")

        # 9. ArticleOutline
        outline = build_outline_dict(
            final_title, final_keyword, intent_analysis, research_brief,
            keyword_brief, editorial_angle, article_type
        )
        self.context["outline"] = outline
        self._step("ArticleOutline")

        # 9b. CannibalizationCheckOutline (after plan)
        cannibalization_outline = check_cannibalization_dict(
            self.db, self.project_id, final_title, final_keyword, chosen_category
        )
        self.context["cannibalization_outline"] = cannibalization_outline
        if cannibalization_outline.get("risk_level") != "none":
            self._log(
                f"Post-outline cannibalization risk: {cannibalization_outline.get('recommendation')} "
                f"({len(cannibalization_outline.get('similar_articles', []))} articles similaires)",
                level="warning", step="CannibalizationCheckOutline",
            )
        self._step("CannibalizationCheckOutline")

        cannibalization_hints = (
            cannibalization_outline.get("similar_articles")
            if cannibalization_outline.get("risk_level") != "none"
            else None
        )

        # 10. ImagePlan
        image_plan_result = build_image_plan_dict(final_keyword, outline)
        self.context["image_plan"] = image_plan_result.get("image_plan", {})
        self.context["image_sources"] = image_plan_result.get("image_sources", [])
        self._step("ImagePlan")

        if image_plan_result.get("image_plan", {}).get("provider_configured"):
            self.tools_used.append("unsplash")
        else:
            self.tools_not_configured.append("image_sourcing")
            self.limitations.append("Image sourcing provider not configured")

        # 11. CalloutPlan
        callout_plan = build_callout_plan_dict(self.db, self.project_id, final_keyword, outline)
        self.context["callout_plan"] = callout_plan
        self._step("CalloutPlan")

        # 12. FAQPlan
        faq_plan = build_faq_plan_dict(final_keyword, intent_analysis)
        self.context["faq_plan"] = faq_plan
        self._step("FAQPlan")

        # 13. InternalLinkPlan
        internal_links = build_internal_link_plan_dict(
            self.db, self.project_id, final_keyword, chosen_category,
            cannibalization_hints=cannibalization_hints,
        )
        self.context["internal_links"] = internal_links
        self._step("InternalLinkPlan")

        # 14. ExternalLinkPlan
        external_links = build_external_link_plan_dict(final_keyword, research_brief, project_id=self.project_id)
        self.context["external_links"] = external_links
        self._step("ExternalLinkPlan")

        # Create or reuse article
        if existing_article_id:
            article = self.db.get(Article, existing_article_id)
            if article is None:
                raise GenerationFailedError(f"Article {existing_article_id} non trouvé")
            draft = _DraftArticle(article)
            if article.current_revision:
                draft.title = article.current_revision.title
                draft.excerpt = article.current_revision.excerpt
                draft.content = article.current_revision.body
                draft.faq = article.current_revision.faq or []
                draft.callouts = article.current_revision.callouts or []
            if preferred_title and not draft.title:
                draft.title = preferred_title
            seo = self.db.get(ArticleSeo, article.id)
            draft.meta_title = seo.meta_title if seo else None
            draft.meta_description = seo.meta_description if seo else None
            draft.keyword = final_keyword
            draft.audience = audience
            draft.angle = angle
            set_article_status(article, ArticleStatus.WRITING_IN_PROGRESS)
            article.updated_at = datetime.now(timezone.utc)
            self.db.flush()
        else:
            article = Article(
                id=str(uuid.uuid4()),
                project_id=self.project_id,
                category_id=chosen_category,
                slug=f"idea-{uuid.uuid4().hex[:8]}",
                search_intent=search_intent or intent_analysis.get("explicit_intent"),
                status_reason_id=ArticleStatus.WRITING_IN_PROGRESS,
                state_id=0,
                priority=0,
                opportunity_score=idea_discovery.get("opportunity_score", 0.5),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.db.add(article)
            self.db.flush()
            draft = _DraftArticle(article)
            draft.title = final_title
            draft.keyword = final_keyword
            draft.audience = audience or project_context.get("target_audience")
            draft.angle = angle or editorial_angle.get("main_angle")

        self.workflow_run = WorkflowRun(
            article_id=article.id,
            phase_id=WorkflowPhase.PRODUCTION,
            status_reason_id=RunStatus.RUNNING,
            state_id=0,
        )
        self.db.add(self.workflow_run)
        self.db.flush()

        # Store all context as artifacts (ai.artifacts, remplace les colonnes *_json)
        self._save(article.id, "project_context", project_context)
        self._save(article.id, "category_strategy", category_strategy)
        self._save(article.id, "idea_discovery", idea_discovery)
        self._save(article.id, "cannibalization_check", cannibalization)
        self._save(article.id, "cannibalization_outline", cannibalization_outline)
        self._save(article.id, "intent_analysis", intent_analysis)
        self._save(article.id, "research_brief", research_brief)
        self._save(article.id, "keyword_brief", keyword_brief)
        self._save(article.id, "editorial_angle", editorial_angle)
        self._save(article.id, "outline", outline)
        self._save(article.id, "image_plan", image_plan_result.get("image_plan", {}))
        self._save(article.id, "image_sources", {"items": image_plan_result.get("image_sources", [])})
        self._save(article.id, "callout_plan", callout_plan)
        self._save(article.id, "internal_links", internal_links)
        self._save(article.id, "external_links", external_links)
        self._save(article.id, "human_insights", self.context.get("human_insights") or {})

        # Plage de mots : catégorie (prioritaire) puis profil éditorial projet
        wc_min, wc_max = None, None
        if article.category_id:
            cat = self.db.get(Category, article.category_id)
            if cat:
                overrides = cat.overrides or {}
                wc_min = overrides.get("word_count_min")
                wc_max = overrides.get("word_count_max")
        if not wc_min and not wc_max:
            profile = self.project.active_editorial_profile if self.project else None
            if profile:
                wc_min = profile.word_count_min
                wc_max = profile.word_count_max

        # Passer la plage au prompt du writer
        if wc_min or wc_max:
            wc_instruction = []
            if wc_min:
                wc_instruction.append(f"minimum {wc_min} mots")
            if wc_max:
                wc_instruction.append(f"maximum {wc_max} mots")
            self.context["word_count_range"] = " et ".join(wc_instruction)

        # Infer content_format from target_word_count if not already set
        if not article.content_format:
            from app.services.seo.format_expectations import infer_format
            target_wc = article.target_word_count
            if target_wc is None:
                # Inférer depuis le milieu de la plage configurée
                if wc_min and wc_max:
                    target_wc = (wc_min + wc_max) // 2
                else:
                    target_wc = wc_max or wc_min
            article.content_format = infer_format(target_wc)
            self._log(
                f"content_format inféré : {article.content_format} (target_word_count={target_wc})",
                step="content_format_init",
            )

        self._log(f"Draft article created: {article.id}", level="info", step="create_article", article_id=article.id)
        self._step("DraftWriting")

        # 14b. Pre-writing context validation
        ctx_ready, ctx_missing = self._validate_writing_context()
        if not ctx_ready:
            self._log(
                f"Context incomplet avant rédaction — champs manquants : {', '.join(ctx_missing)}",
                level="warning", step="PreWritingContextCheck",
            )
            self.limitations.append(f"incomplete_context: {', '.join(ctx_missing)}")

        # 15. Writing
        try:
            self._generate_content(draft, outline, keyword_brief, include_callouts, include_faq)
        except WritingCancelledError:
            raise
        except Exception as exc:
            self._error("Writing", str(exc))
            set_article_status(article, ArticleStatus.FAILED)
            article.updated_at = datetime.now(timezone.utc)
            set_run_status(self.workflow_run, RunStatus.FAILED)
            self.workflow_run.error = str(exc)
            self.workflow_run.finished_at = datetime.now(timezone.utc)
            self.db.flush()
            self._finalize_report(article, draft, category_name, intent_analysis, research_brief, keyword_brief, outline, faq_plan, callout_plan, image_plan_result)
            try:
                from app.services.notification_service import create_notification
                create_notification(
                    db=self.db,
                    project_id=article.project_id,
                    title="Échec de génération",
                    message=f'La génération de "{draft.title or draft.keyword}" a échoué. '
                            f'Vérifiez les logs dans Paramètres → IA.',
                    level="error",
                    type="generation_failed",
                    link=f"/projects/{article.project_id}/settings/ia",
                )
            except Exception:
                pass
            return article

        sources_list = [
            s.get("snippet", "") or s.get("text", "") or str(s)
            for s in research_brief.get("sources_consulted", [])
        ]

        # 16. LanguageQualityPass
        try:
            language_quality = check_language_quality_dict(draft.content)
            self._save(article.id, "language_quality_report", language_quality)
            self.tools_used.append("languagetool" if language_quality.get("external_tool_used") else "language_heuristic")
            self._step("LanguageQualityPass")
        except Exception as exc:
            self._error("LanguageQualityPass", str(exc))
            language_quality = None

        # 17. OriginalityPass
        try:
            originality = check_originality_dict(draft.content, sources_list)
            self._save(article.id, "originality_report", originality)
            self.tools_used.append("ngram_heuristic")
            self._step("OriginalityPass")
        except Exception as exc:
            self._error("OriginalityPass", str(exc))
            originality = None

        # 18. HumanizationPass
        try:
            humanization = check_humanization_dict(draft.content)
            self._save(article.id, "humanization_report", humanization)
            self._step("HumanizationPass")
        except Exception as exc:
            self._error("HumanizationPass", str(exc))
            humanization = None

        # 18b. ReadabilityV2
        try:
            from app.services.seo.readability_service import compute_readability_score
            readability_result = compute_readability_score(draft)
            self._save(article.id, "readability_report", readability_result)
            self._step("ReadabilityV2")
        except Exception as exc:
            self._error("ReadabilityV2", str(exc))
            readability_result = None

        # 19. EEATPass
        try:
            eeat = check_eeat_dict(draft.content, sources_list, draft.author_name)
            self._save(article.id, "eeat_checklist", eeat)
            self._step("EEATPass")
        except Exception as exc:
            self._error("EEATPass", str(exc))
            eeat = None

        # 20. EditorialQualityGate
        try:
            editorial_quality = check_editorial_quality_dict(draft.content)
            self._save(article.id, "editorial_quality_report", editorial_quality)
            self._step("EditorialQualityGate")
        except Exception as exc:
            self._error("EditorialQualityGate", str(exc))
            editorial_quality = None

        structured_data = None
        # 21. SEOFinalChecklist
        try:
            try:
                from app.services.structured_data_builder import build_structured_data
                structured_data = build_structured_data(
                    title=draft.title,
                    slug=article.slug,
                    meta_title=draft.meta_title,
                    meta_description=draft.meta_description,
                    excerpt=draft.excerpt,
                    author=draft.author_name,
                    published_at=article.published_at,
                    updated_at=article.updated_at,
                    category=category_name,
                    content=draft.content,
                    faq_json=json.dumps(draft.faq) if draft.faq else None,
                    cover_image_url=None,
                    site_name=self.project.name if self.project else None,
                    organization_name=self.project.name if self.project else None,
                )
                draft.structured_data_json = structured_data
                self._save(article.id, "structured_data", structured_data)
                self._step("StructuredDataBuilder")
            except Exception as exc:
                self._error("StructuredDataBuilder", str(exc))

            try:
                from app.services.seo.geo_expert_service import compute_geo_score
                geo_result = compute_geo_score(draft)
                self._save(article.id, "geo_optimization", geo_result)
                self._step("GEOOptimizer")
            except Exception as exc:
                self._error("GEOOptimizer", str(exc))

            faq_count = len(draft.faq) if isinstance(draft.faq, list) else 0

            has_sd = bool(structured_data)
            seo_final = check_seo_final_dict(
                content=draft.content,
                title=draft.title,
                slug=article.slug,
                meta_title=draft.meta_title,
                meta_description=draft.meta_description,
                keyword=draft.keyword,
                faq_count=faq_count,
                internal_links=internal_links.get("links", []) if isinstance(internal_links, dict) else [],
                external_links=external_links.get("links", []) if isinstance(external_links, dict) else [],
                images=image_plan_result.get("image_sources", []),
                has_structured_data=has_sd,
            )
            self._save(article.id, "seo_final_checklist", seo_final)
            self._step("SEOFinalChecklist")
        except Exception as exc:
            self._error("SEOFinalChecklist", str(exc))
            seo_final = None

        # 22. SEOReview (aggregated)
        try:
            seo_review = build_aggregated_seo_review(
                language_quality=language_quality,
                originality=originality,
                humanization=humanization,
                eeat=eeat,
                editorial_quality=editorial_quality,
                seo_final=seo_final,
            )
            self._save(article.id, "seo_review", seo_review)
            self._step("SEOReview")
        except Exception as exc:
            self._error("SEOReview", str(exc))
            self._save(article.id, "seo_review", build_review_error_report(str(exc)))

        # 20b. FactCheckPass (LLM-based)
        try:
            if self.agent_router is not None:
                from app.services.agents.agent_services import fact_check_article
                fact_check = fact_check_article(draft.content or "", draft.title, draft.keyword, db=self.db, project_id=self.project_id)
                self._save(article.id, "fact_check_report", fact_check)
                self._step("FactCheckPass")
        except Exception as exc:
            self._error("FactCheckPass", str(exc))

        # 20c. EditorialReview (LLM-based)
        try:
            if self.agent_router is not None:
                from app.services.agents.agent_services import editorial_review
                review_data = editorial_review(draft.content or "", draft.title, draft.keyword, db=self.db, project_id=self.project_id)
                editorial_quality_report = self._get(article.id, "editorial_quality_report") or {}
                editorial_quality_report["llm_review"] = review_data
                self._save(article.id, "editorial_quality_report", editorial_quality_report)
                self._step("EditorialReview")
        except Exception as exc:
            self._error("EditorialReview", str(exc))

        # 20d. SEOOptimizerPass (LLM-based)
        try:
            if self.agent_router is not None:
                from app.services.agents.agent_services import seo_optimize_content
                seo_opt = seo_optimize_content(
                    draft.content or "", draft.title, draft.keyword,
                    meta_title=draft.meta_title, meta_description=draft.meta_description,
                    db=self.db,
                    project_id=self.project_id,
                )
                seo_final_checklist = self._get(article.id, "seo_final_checklist") or {}
                seo_final_checklist["llm_optimizations"] = seo_opt
                self._save(article.id, "seo_final_checklist", seo_final_checklist)
                self._step("SEOOptimizerPass")
        except Exception as exc:
            self._error("SEOOptimizerPass", str(exc))

        # 20e. QualityRating (LLM-based)
        try:
            if self.agent_router is not None:
                from app.services.agents.agent_services import quality_rate_article
                quality = quality_rate_article(draft.content or "", draft.title, draft.keyword, db=self.db, project_id=self.project_id)
                editorial_quality_report = self._get(article.id, "editorial_quality_report") or {}
                editorial_quality_report["llm_quality_rating"] = quality
                self._save(article.id, "editorial_quality_report", editorial_quality_report)
                self._step("QualityRatingPass")
        except Exception as exc:
            self._error("QualityRatingPass", str(exc))

        # 23. GenerationReport
        self._finalize_report(article, draft, category_name, intent_analysis, research_brief, keyword_brief, outline, faq_plan, callout_plan, image_plan_result)

        set_run_status(self.workflow_run, RunStatus.SUCCEEDED)
        self.workflow_run.finished_at = datetime.now(timezone.utc)
        self.db.flush()

        self._log(f"Article generation completed in {int((perf_counter() - self.started_at) * 1000)}ms", level="info", step="orchestrator", article_id=article.id)

        return article

    def _validate_writing_context(self) -> tuple[bool, list[str]]:
        """Check that critical context artifacts are populated before launching the writer."""
        required = [
            ("outline", "Plan de l'article"),
            ("keyword_brief", "Brief mots-clés"),
            ("intent_analysis", "Analyse d'intention"),
            ("editorial_angle", "Angle éditorial"),
        ]
        missing = []
        for key, label in required:
            value = self.context.get(key)
            if not value:
                missing.append(label)
        return len(missing) == 0, missing

    def _raise_if_cancelled(self, article: Article) -> None:
        """Vérifie en base (valeur fraîche) si l'annulation a été demandée."""
        if self.workflow_run is None:
            return
        try:
            flag = self.db.execute(
                select(WorkflowRun.cancel_requested).where(WorkflowRun.id == self.workflow_run.id)
            ).scalar()
        except Exception:
            return
        if flag:
            set_run_status(self.workflow_run, RunStatus.CANCELLED)
            self.workflow_run.finished_at = datetime.now(timezone.utc)
            self.db.flush()
            raise WritingCancelledError(f"Annulation demandée pour l'article {article.id}")

    def _get_agent_provider(self, agent_id: str, fallback: LLMProvider | None = None) -> LLMProvider:
        if self.agent_router is not None:
            try:
                return self.agent_router.get_provider(agent_id, project_id=self.project_id)
            except Exception:
                pass
        return fallback or self.llm

    def _write_through_agent(self, prompt: str, agent_id: str, **kwargs) -> str:
        provider = self._get_agent_provider(agent_id)
        return provider.generate_text(prompt, **kwargs)

    def _generate_content(self, draft: _DraftArticle, outline: dict, keyword_brief: dict, include_callouts: bool | None, include_faq: bool | None = None):
        article = draft.article
        self._raise_if_cancelled(article)
        writer_llm = self._get_agent_provider("writer", self.llm)
        if writer_llm.is_mock:
            draft.content = f"<h1>{draft.title}</h1><p>Contenu mock pour {draft.keyword}</p>"
            draft.word_count = calculate_word_count(draft.content)
            draft.reading_time_minutes = calculate_reading_time_minutes(draft.word_count)
            self._ensure_slug(article, draft.title, draft.keyword)
            self._persist_revision(draft)
            set_article_status(article, ArticleStatus.DRAFT_READY)
            article.updated_at = datetime.now(timezone.utc)
            self.db.flush()
            return

        outline_sections = outline.get("sections", [])

        prompt_parts = [
            f"Rédige un article de blog SEO en français, complet et utile.",
            f"Titre : {draft.title}",
            f"Mot-clé principal : {draft.keyword}",
            f"Mot(s)-clé(s) secondaire(s) : {', '.join(keyword_brief.get('secondary_keywords', []))}",
            f"Intention de recherche : {article.search_intent or 'informational'}",
            f"Angle éditorial : {draft.angle or 'Informatif et pratique'}",
            f"Audience : {draft.audience or 'Grand public'}",
            "",
            "Règles strictes :",
            "- Rédige en HTML compatible TipTap : <h1>, <h2>, <h3>, <p>, <ul>, <ol>, <li>, <blockquote>, <table>, <strong>, <em>",
            "- Pas de Markdown brut visible, pas de ## visibles, pas de [Mock]",
            "- Pas de H5/H6",
            "- Pas de H2 suivi directement par H3 (mets une phrase entre les deux)",
            "- Introduction courte et efficace (2-3 phrases max)",
            "- Après l'introduction, insère un callout résumé (blockquote HTML) récapitulant les 2-3 points clés en 1-2 phrases",
            "- Début qui satisfait rapidement l'intention du lecteur",
            "- Ton humain, direct, concret, pas de texte robotique",
            "- N'utilise JAMAIS le tiret cadratin (—). "
            "  Remplace-le systématiquement par une virgule, un point-virgule, ou reformule la phrase. "
            "  Exemple interdit : 'Le résultat — surprenant — dépasse les attentes.' "
            "  Correct : 'Le résultat, surprenant, dépasse les attentes.'",
            "- REFORMULATION vs PARAPHRASE, règle absolue : "
            "  La paraphrase est INTERDITE. La reformulation totale est OBLIGATOIRE. "
            "  Différence : "
            "  PARAPHRASE (interdit) = changer 2 ou 3 mots dans la phrase originale. "
            "    Exemple : 'j'ai faim' → 'je suis affamé' : c'est la même idée avec un synonyme. INTERDIT. "
            "  REFORMULATION (obligatoire) = exprimer la même idée avec un angle, une structure "
            "  et des mots entièrement différents. "
            "    Exemple : 'j'ai faim' → 'il me faut mettre quelque chose sous la dent' : angle différent. CORRECT. "
            "  Cette règle s'applique à TOUTES les sources : insights humains, données SERP, "
            "  textes concurrents, études, statistiques. "
            "  Si tu ne peux pas reformuler totalement, utilise une citation formelle (blockquote).",
            "- Quand tu utilises un insight venant d'un utilisateur réel (Reddit, forum, Stack Overflow...) : "
            "  reformule complètement l'idée avec tes propres mots, puis ajoute un lien hypertexte "
            "  sur la phrase pointant vers la source originale. "
            "  Format : <a href='URL_SOURCE' target='_blank' rel='nofollow'>texte ancre naturel</a>",
            "- Si tu veux reproduire exactement ce qu'une personne a dit mot pour mot : "
            "  utilise obligatoirement une balise blockquote avec attribution et lien. "
            "  Format HTML exact : "
            "  <blockquote>"
            "    'Texte exact de la citation telle que dite par la personne.'"
            "    <cite><a href='URL_SOURCE' target='_blank' rel='nofollow'>Nom / Pseudo, Plateforme</a></cite>"
            "  </blockquote>",
            "- Pour les publications de personnalités d'autorité reconnues dans le domaine "
            "  (PDG, experts de référence, chercheurs, etc.) publiées sur Twitter/X, LinkedIn, "
            "  ou d'autres réseaux sociaux : intègre le post directement via son code d'intégration natif. "
            "  Pour Twitter/X : utilise le format <blockquote class='twitter-tweet'>...</blockquote> "
            "  avec le script https://platform.twitter.com/widgets.js "
            "  Pour LinkedIn : utilise le lien embed natif de LinkedIn. "
            "  Ne résume jamais un tweet d'autorité : intègre-le.",
            "- Inclus une liste à puces si pertinent",
            "- Tableau seulement si utile pour comparer ou résumer",
            "- Ne crée PAS de section 'Conclusion', 'En résumé' ou 'Pour conclure' séparée",
            "- Termine l'article dans la dernière section du plan sans H2 supplémentaire",
            "- Si un résumé est utile, intègre-le dans la dernière section existante",
        ]

        if self.context.get("word_count_range"):
            prompt_parts.append(
                f"- Volume obligatoire : {self.context['word_count_range']}. "
                "Ne dépasse jamais le maximum. Ne descends jamais sous le minimum."
            )

        prompt_parts.extend(["", "Plan à suivre :"])

        for section in outline_sections:
            heading = section.get("heading", "")
            purpose = section.get("purpose", "")
            key_points = section.get("key_points", [])
            prompt_parts.append(f"- H{section.get('level', 2)}: {heading} ({purpose})")
            if key_points:
                prompt_parts.append(f"  Points: {', '.join(key_points)}")

        prompt_parts.append("")
        if include_callouts:
            prompt_parts.append("Prévois 1-2 callouts pertinents sous forme de paragraphes introduits naturellement.")
        prompt_parts.append("La FAQ sera générée séparément : ne l'inclus pas dans le contenu principal.")
        prompt_parts.append("Sois précis, original et utile.")

        # Injecter la matière humaine si disponible
        insights = self.context.get("human_insights") or {}
        if insights and insights.get("total_insights", 0) > 0:
            prompt_parts.append("\n=== MATIÈRE HUMAINE RÉELLE (à intégrer naturellement) ===")
            if insights.get("questions"):
                prompt_parts.append(
                    "VRAIES QUESTIONS posées par des utilisateurs :\n"
                    + "\n".join(f"- {q}" for q in insights["questions"][:10])
                )
            if insights.get("pain_points"):
                prompt_parts.append(
                    "VRAIES DOULEURS et frustrations :\n"
                    + "\n".join(f"- {p}" for p in insights["pain_points"][:8])
                )
            if insights.get("real_examples"):
                prompt_parts.append(
                    "EXEMPLES RÉELS partagés par des utilisateurs :\n"
                    + "\n".join(f"- {e}" for e in insights["real_examples"][:6])
                )
            if insights.get("objections"):
                prompt_parts.append(
                    "OBJECTIONS et scepticismes :\n"
                    + "\n".join(f"- {o}" for o in insights["objections"][:6])
                )
            if insights.get("positive_experiences"):
                prompt_parts.append(
                    "EXPÉRIENCES POSITIVES réelles :\n"
                    + "\n".join(f"- {p}" for p in insights["positive_experiences"][:6])
                )
            if insights.get("debates"):
                prompt_parts.append(
                    "DÉBATS et controverses :\n"
                    + "\n".join(f"- {d}" for d in insights["debates"][:5])
                )
            if insights.get("vocabulary"):
                prompt_parts.append(
                    "VOCABULAIRE utilisé par les vrais utilisateurs :\n"
                    + "\n".join(f"- {v}" for v in insights["vocabulary"][:8])
                )
            sourced = [i for i in insights.get("all_insights", []) if isinstance(i, dict) and i.get("source_url")]
            if sourced:
                prompt_parts.append(
                    "SOURCES ORIGINALES des insights (à utiliser pour les liens hypertexte et les citations, "
                    "n'invente jamais d'URL) :\n"
                    + "\n".join(
                        f"- \"{str(i.get('content', ''))[:90]}\" → {i.get('source_url')} "
                        f"({i.get('source_name', '')}, {i.get('author') or 'anonyme'})"
                        for i in sourced[:15]
                    )
                )
            prompt_parts.append(
                "INSTRUCTIONS : réponds aux vraies questions ci-dessus. Adresse les vraies douleurs. "
                "Utilise le vocabulaire naturel de ces utilisateurs. L'article doit sembler écrit par "
                "quelqu'un qui connaît vraiment le sujet et les vraies préoccupations des lecteurs."
            )

        content_prompt = "\n".join(prompt_parts)
        if self.agent_router is not None:
            from app.services.agents.agent_router import call_agent
            content, result = call_agent(
                "writer",
                "generate_text",
                content_prompt,
                db=self.db,
                project_id=self.project_id,
                article_id=article.id,
                temperature=0.7,
            )
            if result.status != "success":
                raise GenerationFailedError(result.error or "La rédaction par agent a échoué.")
        else:
            content = writer_llm.generate_text(content_prompt, temperature=0.7)

        if not content or not content.strip():
            raise GenerationFailedError("Le provider IA n'a pas retourné de contenu exploitable pour la rédaction.")

        self._raise_if_cancelled(article)

        draft.content = content
        draft.word_count = calculate_word_count(content)
        draft.reading_time_minutes = calculate_reading_time_minutes(draft.word_count)
        self._ensure_slug(article, draft.title, draft.keyword)

        if not draft.meta_title:
            meta_prompt = f"Écris un meta title SEO (max 60 car.) pour : {draft.title}. Mot-clé : {draft.keyword}"
            if self.agent_router is not None:
                from app.services.agents.agent_router import call_agent
                meta_title, result = call_agent(
                    "meta_writer",
                    "generate_text",
                    meta_prompt,
                    db=self.db,
                    project_id=self.project_id,
                    article_id=article.id,
                    temperature=0.3,
                )
                draft.meta_title = ((meta_title if result.status == "success" else draft.title) or draft.title)[:255]
            else:
                title_llm = self._get_agent_provider("meta_writer", writer_llm)
                draft.meta_title = (title_llm.generate_text(meta_prompt, temperature=0.3) or draft.title)[:255]

        if not draft.meta_description:
            desc_prompt = f"Écris une meta description SEO (140-160 car.) pour : {draft.title}. Mot-clé : {draft.keyword}"
            if self.agent_router is not None:
                from app.services.agents.agent_router import call_agent
                meta_description, result = call_agent(
                    "meta_writer",
                    "generate_text",
                    desc_prompt,
                    db=self.db,
                    project_id=self.project_id,
                    article_id=article.id,
                    temperature=0.3,
                )
                draft.meta_description = (meta_description if result.status == "success" else "")[:500]
            else:
                desc_llm = self._get_agent_provider("meta_writer", writer_llm)
                draft.meta_description = (desc_llm.generate_text(desc_prompt, temperature=0.3) or "")[:500]

        draft.excerpt = self._extract_excerpt(content)

        # FAQ
        if include_faq is not False:
            self._generate_faq(draft)

        self._persist_revision(draft)
        set_article_status(article, ArticleStatus.DRAFT_READY)
        article.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        # AutoScoring post-génération
        try:
            from app.services.seo.seo_review_service import run_and_store_seo_review
            run_and_store_seo_review(self.db, article)
            from app.services.scoring_service import compute_global_score
            scoring = compute_global_score(self.db, article.id, article=article)
            self.db.add(ArticleScore(
                article_id=article.id,
                revision_id=article.current_revision_id,
                global_score=scoring.get("global_score"),
                seo_score=scoring.get("seo_contrib"),
                eeat_score=scoring.get("eeat_contrib"),
                readability_score=scoring.get("readability_contrib"),
                geo_score=scoring.get("geo_contrib"),
            ))
            self.db.flush()
            self._step("AutoScoring")
        except Exception as exc:
            self._error("AutoScoring", str(exc))

        # Notifier que l'article est prêt à valider
        try:
            from app.services.notification_service import create_notification
            latest_score = self.db.execute(
                select(ArticleScore.global_score)
                .where(ArticleScore.article_id == article.id)
                .order_by(ArticleScore.evaluated_at.desc())
                .limit(1)
            ).scalar()
            create_notification(
                db=self.db,
                project_id=article.project_id,
                title="Article prêt à valider",
                message=f'"{draft.title}" a été rédigé et scoré. Score global : {latest_score or "—"}.',
                level="success",
                type="article_ready",
                link=f"/projects/{article.project_id}/production?tab=validate",
            )
        except Exception:
            pass

        # Cycle d'auto-amélioration si score insuffisant
        self._raise_if_cancelled(article)
        try:
            current_score = self.db.execute(
                select(ArticleScore.global_score)
                .where(ArticleScore.article_id == article.id)
                .order_by(ArticleScore.evaluated_at.desc())
                .limit(1)
            ).scalar()
            if current_score is not None and current_score < AUTO_IMPROVE_SCORE_TARGET:
                self._auto_improve_score(draft, max_iterations=2)
        except Exception as exc:
            self._error("AutoImprove", str(exc))

    def _persist_revision(self, draft: _DraftArticle) -> ArticleRevision:
        article = draft.article
        last_no = self.db.execute(
            select(ArticleRevision.revision_no)
            .where(ArticleRevision.article_id == article.id)
            .order_by(ArticleRevision.revision_no.desc())
            .limit(1)
        ).scalar_one_or_none()
        revision = ArticleRevision(
            article_id=article.id,
            revision_no=(last_no or 0) + 1,
            source=RevisionSource.AI,
            title=draft.title,
            excerpt=draft.excerpt,
            body=draft.content,
            faq=draft.faq or [],
            callouts=draft.callouts or [],
            word_count=draft.word_count,
            reading_time_minutes=draft.reading_time_minutes,
        )
        self.db.add(revision)
        self.db.flush()
        article.current_revision_id = revision.id

        seo = self.db.get(ArticleSeo, article.id)
        if seo is None:
            seo = ArticleSeo(article_id=article.id)
            self.db.add(seo)
        seo.meta_title = draft.meta_title
        seo.meta_description = draft.meta_description
        self.db.flush()
        return revision

    def _auto_improve_score(self, draft: _DraftArticle, max_iterations: int = 2):
        """Tant que global_score < AUTO_IMPROVE_SCORE_TARGET, améliore le signal le plus faible."""
        from app.services.seo.seo_review_service import run_and_store_seo_review
        from app.services.scoring_service import compute_global_score

        article = draft.article
        IMPROVEMENT_INSTRUCTIONS = {
            'EEAT': (
                "Enrichis cet article avec des données chiffrées sourcées et des exemples concrets. "
                "Ajoute au moins une statistique avec sa source et un exemple spécifique non mentionné."
            ),
            'SEO': (
                "Optimise la densité du mot-clé cible dans les titres H2 et dans le corps du texte. "
                "Assure-toi que le H1 et au moins un H2 contiennent le mot-clé principal."
            ),
            'Lisibilité': (
                "Raccourcis les phrases de plus de 25 mots. Simplifie le vocabulaire complexe. "
                "Vise des phrases directes, courtes et claires."
            ),
            'Originalité': (
                "Remplace les formulations génériques par des angles uniques. "
                "Supprime les introductions clichées. Ajoute une perspective distincte absente de l'article."
            ),
            'GEO': (
                "Restructure les débuts de paragraphes pour qu'ils répondent directement à une question implicite. "
                "Chaque section H2 doit s'ouvrir sur une réponse directe et autonome."
            ),
        }

        for iteration in range(max_iterations):
            self._raise_if_cancelled(article)
            latest = self.db.execute(
                select(ArticleScore)
                .where(ArticleScore.article_id == article.id)
                .order_by(ArticleScore.evaluated_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            current_score = latest.global_score if latest else None
            if current_score is None or current_score >= AUTO_IMPROVE_SCORE_TARGET:
                break

            signals = {
                'EEAT': latest.eeat_score if latest else None,
                'SEO': latest.seo_score if latest else None,
                'Lisibilité': latest.readability_score if latest else None,
                'Originalité': None,
                'GEO': latest.geo_score if latest else None,
            }
            valid_signals = {k: v for k, v in signals.items() if v is not None}
            if not valid_signals:
                break

            weakest_signal = min(valid_signals, key=valid_signals.get)
            instruction = IMPROVEMENT_INSTRUCTIONS.get(weakest_signal, "Améliore la qualité globale du texte.")

            improve_prompt = (
                f"Améliore ce contenu HTML en appliquant UNE SEULE modification ciblée.\n\n"
                f"Instruction : {instruction}\n\n"
                "Règles impératives :\n"
                "- Conserve exactement la structure HTML (balises H1, H2, H3, p, ul, li)\n"
                "- Ne change pas le titre principal (H1)\n"
                "- Ne modifie pas la longueur totale de plus de 20%\n"
                "- Retourne uniquement le HTML amélioré, sans explication, sans backticks\n\n"
                f"Contenu :\n{(draft.content or '')[:4000]}"
            )

            try:
                # Passe par l'agent editor : le provider configuré pour la révision
                # doit aussi piloter les retouches automatiques.
                editor_llm = self._get_agent_provider("editor", self.llm)
                if editor_llm.is_mock:
                    break
                improved = editor_llm.generate_text(improve_prompt)
                if improved and len(improved) > 200:
                    draft.content = improved
                    draft.word_count = calculate_word_count(improved)
                    draft.reading_time_minutes = calculate_reading_time_minutes(draft.word_count)
                    self._persist_revision(draft)
                    article.updated_at = datetime.now(timezone.utc)
                    self.db.flush()

                    try:
                        run_and_store_seo_review(self.db, article)
                        scoring = compute_global_score(self.db, article.id, article=article)
                        self.db.add(ArticleScore(
                            article_id=article.id,
                            revision_id=article.current_revision_id,
                            global_score=scoring.get("global_score"),
                            seo_score=scoring.get("seo_contrib"),
                            eeat_score=scoring.get("eeat_contrib"),
                            readability_score=scoring.get("readability_contrib"),
                            geo_score=scoring.get("geo_contrib"),
                        ))
                        self.db.flush()
                    except Exception as score_exc:
                        self._error(f"AutoImprove_rescore_{iteration}", str(score_exc))

                    self._step(f"AutoImprove_{weakest_signal}_iter{iteration + 1}")
            except Exception as exc:
                self._error(f"AutoImprove_{weakest_signal}_iter{iteration + 1}", str(exc))
                break

    def _generate_faq(self, draft: _DraftArticle):
        article = draft.article
        faq_llm = self._get_agent_provider("faq_generator", self.llm)
        if faq_llm.is_mock:
            return

        # Enrichir avec les vraies questions humaines si disponibles
        insights = self.context.get("human_insights") or {}
        real_questions = insights.get("questions", [])
        real_pains = insights.get("pain_points", [])
        human_context = ""
        if real_questions:
            human_context += (
                "\nVraies questions posées par des utilisateurs réels "
                "(Google People Also Ask, Reddit, forums, inspire-toi sans les copier) :\n"
                + "\n".join(f"- {q}" for q in real_questions[:8])
            )
        if real_pains:
            human_context += (
                "\nVraies douleurs/frustrations des utilisateurs :\n"
                + "\n".join(f"- {p}" for p in real_pains[:5])
            )

        faq_intro = (
            f"Génère 3 à 5 questions fréquentes (FAQ) à partir de cet article"
            + (f" en t'inspirant de ces vraies questions d'utilisateurs :{human_context}\n\n" if human_context else ".\n")
        )

        faq_prompt = (
            faq_intro
            + f"Titre : {draft.title}\n"
            f"Mot-clé principal : {draft.keyword}\n"
            f"Extrait du contenu :\n{draft.content[:1500]}\n\n"
            "Règles strictes :\n"
            "- Chaque réponse : 1 à 4 phrases maximum\n"
            "- Les questions ne doivent pas répéter les titres H2 de l'article\n"
            "- Questions variées : définition, cas d'usage, comparaison, conseil\n"
            "- Réponses directes, sans formule introductive\n\n"
            'Réponds uniquement avec un objet JSON au format {"faq":[{"question":"...","answer":"..."}]}.'
        )
        try:
            faq_data = faq_llm.generate_json(
                faq_prompt,
                schema_hint='{"faq":[{"question":"...","answer":"..."}]}',
            )
            faq_items = faq_data.get("faq") if isinstance(faq_data, dict) else None
            if isinstance(faq_items, list):
                normalized = []
                for item in faq_items:
                    if not isinstance(item, dict):
                        continue
                    q = str(item.get("question", "")).strip()
                    a = str(item.get("answer", "")).strip()
                    if q and a:
                        normalized.append({"question": q, "answer": a})
                if 2 <= len(normalized) <= 6:
                    draft.faq = normalized
        except Exception:
            pass

    def _extract_excerpt(self, content: str, max_length: int = 300) -> str:
        text = content
        if text.startswith("<"):
            text = __import__("re").sub(r"<[^>]+>", " ", text)
            text = __import__("re").sub(r"\s+", " ", text).strip()
        return text[:max_length]

    def _get_article_cost_data(self, article_id: str) -> dict:
        """Aggregate cost data from ai.usage_events for this article."""
        from app.models.ai import UsageEvent

        try:
            logs = self.db.execute(
                select(UsageEvent).where(UsageEvent.article_id == article_id)
            ).scalars().all()
        except Exception:
            return {
                "estimated_cost_eur": None,
                "actual_cost_eur": None,
                "cost_status": "not_tracked",
                "cost_breakdown_json": [],
                "cost_warnings": [],
            }

        if not logs:
            return {
                "estimated_cost_eur": None,
                "actual_cost_eur": None,
                "cost_status": "not_tracked",
                "cost_breakdown_json": [],
                "cost_warnings": [],
            }

        total_estimated = 0.0
        total_actual = 0.0
        has_unknown = False       # prix du modèle inconnu -> total estimé non fiable
        has_unmeasured = False    # tokens non remontés par le provider -> pas de coût constaté
        breakdown = []
        warnings = []

        for log in logs:
            est = log.estimated_cost
            act = log.actual_cost
            if est is not None:
                total_estimated += float(est)
            else:
                has_unknown = True
            if act is not None:
                total_actual += float(act)
            else:
                has_unmeasured = True

            breakdown.append({
                "agent_key": log.agent_key,
                "provider": log.provider_code or "",
                "model": log.model or "",
                "input_tokens": log.prompt_tokens or 0,
                "output_tokens": log.completion_tokens or 0,
                "estimated_cost_eur": est,
                "actual_cost_eur": act,
                "cost_status": (
                    "unknown_price" if est is None
                    else "tracked" if act is not None
                    else "estimated"
                ),
            })

        if has_unknown:
            warnings.append("Certains modèles n'ont pas de prix configuré.")
        if has_unmeasured:
            warnings.append(
                "Certains appels n'ont pas remonté leur consommation réelle de tokens : "
                "le coût affiché reste une estimation."
            )

        cost_limit_eur = None
        try:
            from app.models.ai import Pipeline
            pipeline = self.db.get(Pipeline, self.project_id)
            if pipeline and pipeline.cost_limit_per_article:
                cost_limit_eur = float(pipeline.cost_limit_per_article)
        except Exception:
            pass

        total_estimated = round(total_estimated, 6) if not has_unknown else None
        # Le coût constaté n'a de sens que si chaque appel a remonté ses tokens réels.
        total_actual = round(total_actual, 6) if not (has_unknown or has_unmeasured) else None

        if cost_limit_eur is not None and total_estimated is not None and total_estimated > cost_limit_eur:
            cost_status = "over_limit"
            warnings.append(f"Coût ({total_estimated} EUR) dépasse la limite ({cost_limit_eur} EUR)")
        elif has_unknown:
            cost_status = "partial_unknown"
        else:
            cost_status = "within_limit"

        return {
            "estimated_cost_eur": total_estimated,
            "actual_cost_eur": total_actual,
            "cost_limit_eur": cost_limit_eur,
            "cost_status": cost_status,
            "cost_breakdown_json": breakdown,
            "cost_warnings": warnings,
        }

    def _finalize_report(
        self,
        article: Article,
        draft: _DraftArticle,
        category_name: str,
        intent_analysis: dict,
        research_brief: dict,
        keyword_brief: dict,
        outline: dict,
        faq_plan: dict,
        callout_plan: dict,
        image_plan_result: dict,
    ):
        adapters_status = {}
        for adapter in (
            serp_adapter, trends_adapter, image_sourcing_adapter, language_adapter,
            scrapling_adapter, content_extraction_adapter, orig_adapter, readability_adapter, google_watch_adapter,
        ):
            try:
                adapters_status[adapter.provider_name] = adapter.get_status()
            except Exception:
                adapters_status[adapter.provider_name] = {"error": "status_unavailable"}

        cost_data = self._get_article_cost_data(article.id)

        try:
            report = build_generation_report_dict(
                provider=self.llm.provider_name,
                model=self.llm.model_name or "",
                title_requested=draft.title,
                title_final=draft.title,
                category_id=article.category_id,
                category_name=category_name,
                main_keyword=draft.keyword or "",
                secondary_keywords=keyword_brief.get("secondary_keywords", []),
                detected_intent=intent_analysis.get("explicit_intent", ""),
                expected_answer=intent_analysis.get("expected_answer", ""),
                article_type=intent_analysis.get("article_type", "evergreen_information"),
                outline_used=bool(outline.get("sections")),
                faq_generated=bool(draft.faq),
                callouts_proposed=len(callout_plan.get("callouts", [])),
                images_proposed=len(image_plan_result.get("image_plan", {}).get("images", [])),
                internal_links_proposed=len(self.context.get("internal_links", {}).get("links", [])),
                external_links_proposed=len(self.context.get("external_links", {}).get("links", [])),
                research_status=research_brief.get("research_status", "not_available"),
                sources_used=[s.get("url", "") for s in research_brief.get("sources_consulted", []) if isinstance(s, dict)],
                tools_used=self.tools_used,
                tools_not_configured=self.tools_not_configured,
                adapters_status=adapters_status,
                word_count=draft.word_count,
                reading_time_minutes=draft.reading_time_minutes or 1,
                steps_completed=self.steps_completed,
                errors=self.errors,
                limitations=self.limitations,
                final_status=article.status_reason_id,
                **cost_data,
            )
            self._save(article.id, "generation_report", report)
        except Exception as exc:
            self._error("GenerationReport", str(exc))

        self._step("GenerationReport")


def generate_full_article(
    db: Session,
    project_id: str,
    llm: LLMProvider,
    search: SearchProviderType,
    *,
    preferred_title: str | None = None,
    keyword: str | None = None,
    category_id: str | None = None,
    audience: str | None = None,
    angle: str | None = None,
    search_intent: str | None = None,
    context_hint: str | None = None,
    include_faq: bool | None = None,
    include_callouts: bool | None = None,
    agent_router: Any | None = None,
    existing_article_id: str | None = None,
) -> Article:
    orchestrator = SEOGenerationOrchestrator(db, project_id, llm, search, agent_router=agent_router)
    return orchestrator.generate_full_article(
        preferred_title=preferred_title,
        keyword=keyword,
        category_id=category_id,
        audience=audience,
        angle=angle,
        search_intent=search_intent,
        context_hint=context_hint,
        include_faq=include_faq,
        include_callouts=include_callouts,
        existing_article_id=existing_article_id,
    )
