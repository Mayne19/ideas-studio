from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.agents.agent_router import AgentRouter

from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.category import Category
from app.models.project import Project
from app.schemas.seo_workflow import asdict
from app.services.log_service import log_step
from app.services.providers.llm_provider import LLMProvider, GenerationFailedError
from app.services.providers.search_provider import SearchProvider as SearchProviderType
from app.core.utils import calculate_reading_time_minutes, calculate_word_count, generate_unique_slug, slugify

from app.services.seo.helpers import safe_json_dump, safe_json_load
from app.services.seo.project_context_service import build_project_context_dict
from app.services.seo.category_strategy_service import compute_category_strategy_dict
from app.services.seo.cannibalization_service import check_cannibalization_dict
from app.services.seo.intent_analysis_service import analyze_intent_dict
from app.services.seo.research_brief_service import build_research_brief_dict
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
from app.services.seo.adapters.originality_adapter import originality_adapter as orig_adapter
from app.services.seo.adapters.readability_adapter import readability_adapter
from app.services.seo.adapters.google_watch_adapter import google_watch_adapter


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
        self.project = db.query(Project).filter(Project.id == project_id).first()
        self.steps_completed: list[str] = []
        self.errors: list[str] = []
        self.limitations: list[str] = []
        self.tools_used: list[str] = []
        self.tools_not_configured: list[str] = []
        self.context: dict = {}
        self.started_at = perf_counter()

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

    def _ensure_slug(self, article: Article):
        if article.slug and not article.slug.startswith("idea-"):
            return
        base = slugify(article.title or article.keyword or "article")
        existing = {
            row[0]
            for row in self.db.query(Article.slug).filter(
                Article.project_id == self.project_id,
                Article.id != article.id,
                Article.slug.like(f"{base}%"),
            ).all()
        }
        article.slug = generate_unique_slug(base, existing)

    def _get_category_name(self, category_id: str | None) -> str:
        if not category_id:
            return ""
        cat = self.db.query(Category).filter(Category.id == category_id).first()
        return cat.name if cat else ""

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
        research_brief = build_research_brief_dict(final_keyword, final_title, category_name)
        self.context["research_brief"] = research_brief
        self._step("ResearchBrief")

        if research_brief.get("research_status") == "available":
            self.tools_used.append("serp_research")
        else:
            self.limitations.append("No real SERP research available")

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
        external_links = build_external_link_plan_dict(final_keyword, research_brief)
        self.context["external_links"] = external_links
        self._step("ExternalLinkPlan")

        # Create article
        article = Article(
            id=str(uuid.uuid4()),
            project_id=self.project_id,
            category_id=chosen_category,
            title=final_title,
            slug=f"idea-{uuid.uuid4().hex[:8]}",
            keyword=final_keyword,
            audience=audience or project_context.get("target_audience"),
            angle=angle or editorial_angle.get("main_angle"),
            search_intent=search_intent or intent_analysis.get("explicit_intent"),
            status="writing_in_progress",
            priority=0,
            word_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            opportunity_score=idea_discovery.get("opportunity_score", 0.5),
        )

        # Store all context
        article.project_context_json = project_context
        article.category_strategy_json = category_strategy
        article.idea_discovery_json = idea_discovery
        article.cannibalization_check_json = cannibalization
        article.cannibalization_outline_json = cannibalization_outline
        article.intent_analysis_json = intent_analysis
        article.research_brief_json = research_brief
        article.keyword_brief_json = keyword_brief
        article.editorial_angle_json = editorial_angle
        article.outline_json = safe_json_dump(outline)
        article.image_plan_json = safe_json_dump(image_plan_result.get("image_plan", {}))
        article.image_sources_json = safe_json_dump(image_plan_result.get("image_sources", []))
        article.callout_plan_json = safe_json_dump(callout_plan)
        article.internal_links_json = safe_json_dump(internal_links)
        article.external_links_json = safe_json_dump(external_links)

        # Infer content_format from target_word_count if not already set
        if not getattr(article, "content_format", None):
            from app.services.seo.format_expectations import infer_format
            target_wc = getattr(article, "target_word_count", None)
            article.content_format = infer_format(target_wc)
            self._log(
                f"content_format inféré : {article.content_format} (target_word_count={target_wc})",
                step="content_format_init",
            )

        self.db.add(article)
        self.db.flush()

        self._log(f"Draft article created: {article.id}", level="info", step="create_article", article_id=article.id)
        self._step("DraftWriting")

        # 14b. Pre-writing context validation
        ctx_ready, ctx_missing = self._validate_writing_context(article)
        if not ctx_ready:
            self._log(
                f"Context incomplet avant rédaction — champs manquants : {', '.join(ctx_missing)}",
                level="warning", step="PreWritingContextCheck",
            )
            self.limitations.append(f"incomplete_context: {', '.join(ctx_missing)}")

        # 15. Writing
        try:
            self._generate_content(article, outline, keyword_brief, include_callouts, include_faq)
        except Exception as exc:
            self._error("Writing", str(exc))
            article.status = "failed"
            article.updated_at = datetime.now(timezone.utc)
            self.db.flush()
            self._finalize_report(article, category_name, intent_analysis, research_brief, keyword_brief, outline, faq_plan, callout_plan, image_plan_result)
            return article

        # 16. LanguageQualityPass
        try:
            language_quality = check_language_quality_dict(article.content)
            article.language_quality_report_json = language_quality
            self.tools_used.append("languagetool" if language_quality.get("external_tool_used") else "language_heuristic")
            self._step("LanguageQualityPass")
        except Exception as exc:
            self._error("LanguageQualityPass", str(exc))
            language_quality = None

        # 17. OriginalityPass
        try:
            sources_list = [
                s.get("snippet", "") or s.get("text", "") or str(s)
                for s in research_brief.get("sources_consulted", [])
            ]
            originality = check_originality_dict(article.content, sources_list)
            article.originality_report_json = originality
            self.tools_used.append("ngram_heuristic")
            self._step("OriginalityPass")
        except Exception as exc:
            self._error("OriginalityPass", str(exc))
            originality = None

        # 18. HumanizationPass
        try:
            humanization = check_humanization_dict(article.content)
            article.humanization_report_json = humanization
            self._step("HumanizationPass")
        except Exception as exc:
            self._error("HumanizationPass", str(exc))
            humanization = None

        # 18b. ReadabilityV2
        try:
            from app.services.seo.readability_service import compute_readability_score
            readability_result = compute_readability_score(article)
            article.readability_report_json = readability_result
            if readability_result.get("score") is not None:
                article.readability_score = float(readability_result["score"])
            self._step("ReadabilityV2")
        except Exception as exc:
            self._error("ReadabilityV2", str(exc))

        # 19. EEATPass
        try:
            eeat = check_eeat_dict(article.content, sources_list, article.author_name)
            article.eeat_checklist_json = eeat
            self._step("EEATPass")
        except Exception as exc:
            self._error("EEATPass", str(exc))
            eeat = None

        # 20. EditorialQualityGate
        try:
            editorial_quality = check_editorial_quality_dict(article.content)
            article.editorial_quality_report_json = editorial_quality
            self._step("EditorialQualityGate")
        except Exception as exc:
            self._error("EditorialQualityGate", str(exc))
            editorial_quality = None

        # 21. SEOFinalChecklist
        try:
            try:
                from app.services.structured_data_builder import build_structured_data
                structured_data = build_structured_data(
                    title=article.title,
                    slug=article.slug,
                    meta_title=article.meta_title,
                    meta_description=article.meta_description,
                    excerpt=article.excerpt,
                    author=article.author_name,
                    published_at=article.published_at,
                    updated_at=article.updated_at,
                    category=category_name,
                    content=article.content,
                    faq_json=article.faq_json,
                    cover_image_url=article.cover_image_url,
                    site_name=self.project.name if self.project else None,
                    organization_name=self.project.name if self.project else None,
                )
                article.structured_data_json = structured_data
                self._step("StructuredDataBuilder")
            except Exception as exc:
                self._error("StructuredDataBuilder", str(exc))

            try:
                from app.services.seo.geo_expert_service import compute_geo_score
                article.geo_optimization_json = compute_geo_score(article)
                self._step("GEOOptimizer")
            except Exception as exc:
                self._error("GEOOptimizer", str(exc))

            faq_count = 0
            if article.faq_json:
                try:
                    faq_items = json.loads(article.faq_json) if isinstance(article.faq_json, str) else article.faq_json
                    faq_count = len(faq_items) if isinstance(faq_items, list) else 0
                except (json.JSONDecodeError, TypeError):
                    faq_count = 0

            internal_links_list = safe_json_load(article.internal_links_json, [])
            external_links_list = safe_json_load(article.external_links_json, [])
            images_list = safe_json_load(article.image_sources_json, [])

            has_sd = bool(article.structured_data_json)
            seo_final = check_seo_final_dict(
                content=article.content,
                title=article.title,
                slug=article.slug,
                meta_title=article.meta_title,
                meta_description=article.meta_description,
                keyword=article.keyword,
                faq_count=faq_count,
                internal_links=internal_links_list if isinstance(internal_links_list, list) else [],
                external_links=external_links_list if isinstance(external_links_list, list) else [],
                images=images_list if isinstance(images_list, list) else [],
                has_structured_data=has_sd,
            )
            article.seo_final_checklist_json = seo_final
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
            article.seo_review_json = seo_review
            self._step("SEOReview")
        except Exception as exc:
            self._error("SEOReview", str(exc))
            article.seo_review_json = build_review_error_report(str(exc))

        # 20b. FactCheckPass (LLM-based)
        try:
            if self.agent_router is not None:
                from app.services.agents.agent_services import fact_check_article
                fact_check = fact_check_article(article.content or "", article.title, article.keyword, db=self.db)
                article.fact_check_report_json = fact_check
                self._step("FactCheckPass")
        except Exception as exc:
            self._error("FactCheckPass", str(exc))

        # 20c. EditorialReview (LLM-based)
        try:
            if self.agent_router is not None:
                from app.services.agents.agent_services import editorial_review
                review_data = editorial_review(article.content or "", article.title, article.keyword, db=self.db)
                if not article.editorial_quality_report_json or not isinstance(article.editorial_quality_report_json, dict):
                    article.editorial_quality_report_json = {}
                if isinstance(article.editorial_quality_report_json, dict):
                    article.editorial_quality_report_json["llm_review"] = review_data
                self._step("EditorialReview")
        except Exception as exc:
            self._error("EditorialReview", str(exc))

        # 20d. SEOOptimizerPass (LLM-based)
        try:
            if self.agent_router is not None:
                from app.services.agents.agent_services import seo_optimize_content
                seo_opt = seo_optimize_content(
                    article.content or "", article.title, article.keyword,
                    meta_title=article.meta_title, meta_description=article.meta_description,
                    db=self.db,
                )
                if not article.seo_final_checklist_json or not isinstance(article.seo_final_checklist_json, dict):
                    article.seo_final_checklist_json = {}
                if isinstance(article.seo_final_checklist_json, dict):
                    article.seo_final_checklist_json["llm_optimizations"] = seo_opt
                self._step("SEOOptimizerPass")
        except Exception as exc:
            self._error("SEOOptimizerPass", str(exc))

        # 20e. QualityRating (LLM-based)
        try:
            if self.agent_router is not None:
                from app.services.agents.agent_services import quality_rate_article
                quality = quality_rate_article(article.content or "", article.title, article.keyword, db=self.db)
                if not article.eeat_checklist_json or not isinstance(article.eeat_checklist_json, dict):
                    article.eeat_checklist_json = {}
                if isinstance(article.eeat_checklist_json, dict):
                    article.eeat_checklist_json["llm_quality_rating"] = quality
                self._step("QualityRatingPass")
        except Exception as exc:
            self._error("QualityRatingPass", str(exc))

        # 23. GenerationReport
        self._finalize_report(article, category_name, intent_analysis, research_brief, keyword_brief, outline, faq_plan, callout_plan, image_plan_result)

        self._log(f"Article generation completed in {int((perf_counter() - self.started_at) * 1000)}ms", level="info", step="orchestrator", article_id=article.id)

        return article

    def _validate_writing_context(self, article: Article) -> tuple[bool, list[str]]:
        """Check that critical fields are populated before launching the writer."""
        required = [
            ("outline_json", "Plan de l'article"),
            ("keyword_brief_json", "Brief mots-clés"),
            ("intent_analysis_json", "Analyse d'intention"),
            ("editorial_angle_json", "Angle éditorial"),
        ]
        missing = []
        for field, label in required:
            value = getattr(article, field, None)
            if not value or value in ({}, "{}"):
                missing.append(label)
        return len(missing) == 0, missing

    def _get_agent_provider(self, agent_id: str, fallback: LLMProvider | None = None) -> LLMProvider:
        if self.agent_router is not None:
            try:
                return self.agent_router.get_provider(agent_id)
            except Exception:
                pass
        return fallback or self.llm

    def _write_through_agent(self, prompt: str, agent_id: str, **kwargs) -> str:
        provider = self._get_agent_provider(agent_id)
        return provider.generate_text(prompt, **kwargs)

    def _generate_content(self, article: Article, outline: dict, keyword_brief: dict, include_callouts: bool | None, include_faq: bool | None = None):
        writer_llm = self._get_agent_provider("content_writer", self.llm)
        if writer_llm.is_mock:
            article.content = f"<h1>{article.title}</h1><p>Contenu mock pour {article.keyword}</p>"
            article.word_count = calculate_word_count(article.content)
            article.reading_time_minutes = calculate_reading_time_minutes(article.word_count)
            self._ensure_slug(article)
            article.status = "draft_ready"
            article.updated_at = datetime.now(timezone.utc)
            self.db.flush()
            return

        outline_sections = outline.get("sections", [])

        prompt_parts = [
            f"Rédige un article de blog SEO en français, complet et utile.",
            f"Titre : {article.title}",
            f"Mot-clé principal : {article.keyword}",
            f"Mot(s)-clé(s) secondaire(s) : {', '.join(keyword_brief.get('secondary_keywords', []))}",
            f"Intention de recherche : {article.search_intent or 'informational'}",
            f"Angle éditorial : {article.angle or 'Informatif et pratique'}",
            f"Audience : {article.audience or 'Grand public'}",
            "",
            "Règles strictes :",
            "- Rédige en HTML compatible TipTap : <h1>, <h2>, <h3>, <p>, <ul>, <ol>, <li>, <blockquote>, <table>, <strong>, <em>",
            "- Pas de Markdown brut visible, pas de ## visibles, pas de [Mock]",
            "- Pas de H5/H6",
            "- Pas de H2 suivi directement par H3 (mets une phrase entre les deux)",
            "- Introduction courte et efficace (2-3 phrases max)",
            "- Après l'introduction, insère un callout résumé (blockquote HTML) récapitulant les 2-3 points clés en 1-2 phrases",
            "- Début qui satisfait rapidement l'intention du lecteur",
            "- Ton humain, direct, concret — pas de texte robotique",
            "- Pas de paraphrase faible",
            "- Inclus une liste à puces si pertinent",
            "- Tableau seulement si utile pour comparer ou résumer",
            "- Ne crée PAS de section 'Conclusion', 'En résumé' ou 'Pour conclure' séparée",
            "- Termine l'article dans la dernière section du plan sans H2 supplémentaire",
            "- Si un résumé est utile, intègre-le dans la dernière section existante",
            "",
            "Plan à suivre :",
        ]

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
        prompt_parts.append("La FAQ sera générée séparément — ne l'inclus pas dans le contenu principal.")
        prompt_parts.append("Sois précis, original et utile.")

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

        article.content = content
        article.word_count = calculate_word_count(content)
        article.reading_time_minutes = calculate_reading_time_minutes(article.word_count)
        self._ensure_slug(article)

        if not article.meta_title:
            meta_prompt = f"Écris un meta title SEO (max 60 car.) pour : {article.title}. Mot-clé : {article.keyword}"
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
                article.meta_title = ((meta_title if result.status == "success" else article.title) or article.title)[:255]
            else:
                title_llm = self._get_agent_provider("title_generator", writer_llm)
                article.meta_title = (title_llm.generate_text(meta_prompt, temperature=0.3) or article.title)[:255]

        if not article.meta_description:
            desc_prompt = f"Écris une meta description SEO (140-160 car.) pour : {article.title}. Mot-clé : {article.keyword}"
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
                article.meta_description = (meta_description if result.status == "success" else "")[:500]
            else:
                desc_llm = self._get_agent_provider("meta_description_writer", writer_llm)
                article.meta_description = (desc_llm.generate_text(desc_prompt, temperature=0.3) or "")[:500]

        article.excerpt = self._extract_excerpt(content)

        # FAQ
        if include_faq is not False:
            self._generate_faq(article)

        article.status = "draft_ready"
        article.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        # AutoScoring post-génération
        try:
            from app.services.seo.seo_review_service import run_and_store_seo_review
            run_and_store_seo_review(article)
            from app.services.scoring_service import compute_global_score
            scoring = compute_global_score(article)
            article.global_score = scoring.get("global_score")
            article.global_score_valid = bool(scoring.get("global_score_valid", False))
            self.db.flush()
            self._step("AutoScoring")
        except Exception as exc:
            self._error("AutoScoring", str(exc))

    def _generate_faq(self, article: Article):
        faq_llm = self._get_agent_provider("faq_generator", self.llm)
        if faq_llm.is_mock:
            return
        faq_prompt = (
            f"Génère 3 à 5 questions fréquentes (FAQ) à partir de cet article.\n"
            f"Titre : {article.title}\n"
            f"Mot-clé principal : {article.keyword}\n"
            f"Extrait du contenu :\n{article.content[:1500]}\n\n"
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
                    article.faq_json = json.dumps(normalized)
        except Exception:
            pass

    def _extract_excerpt(self, content: str, max_length: int = 300) -> str:
        text = content
        if text.startswith("<"):
            text = __import__("re").sub(r"<[^>]+>", " ", text)
            text = __import__("re").sub(r"\s+", " ", text).strip()
        return text[:max_length]

    def _get_article_cost_data(self, article_id: str) -> dict:
        """Aggregate cost data from AiUsageLog for this article."""
        try:
            from app.models.ai_usage_log import AiUsageLog
            logs = (
                self.db.query(AiUsageLog)
                .filter(AiUsageLog.article_id == article_id)
                .all()
            )
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
        has_unknown = False
        breakdown = []
        warnings = []

        for log in logs:
            est = log.estimated_cost
            act = log.actual_cost
            if est is not None:
                total_estimated += est
            else:
                has_unknown = True
            if act is not None:
                total_actual += act
            else:
                has_unknown = True

            breakdown.append({
                "agent_key": log.agent_id,
                "provider": log.provider_name or "",
                "model": log.model_name or "",
                "input_tokens": log.prompt_tokens or 0,
                "output_tokens": log.completion_tokens or 0,
                "estimated_cost_eur": est,
                "actual_cost_eur": act,
                "cost_status": "tracked" if est is not None else "unknown_price",
            })

        if has_unknown:
            warnings.append("Certains modèles n'ont pas de prix configuré.")

        cost_limit_eur = None
        try:
            from app.models.pipeline import ProjectPipeline
            pipeline = (
                self.db.query(ProjectPipeline)
                .filter(ProjectPipeline.project_id == self.project_id)
                .first()
            )
            if pipeline and hasattr(pipeline, "cost_limit_per_article_eur") and pipeline.cost_limit_per_article_eur:
                cost_limit_eur = float(pipeline.cost_limit_per_article_eur)
        except Exception:
            pass

        total_estimated = round(total_estimated, 6) if not has_unknown else None
        total_actual = round(total_actual, 6) if not has_unknown else None

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
            content_extraction_adapter, orig_adapter, readability_adapter, google_watch_adapter,
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
                title_requested=article.title,
                title_final=article.title,
                category_id=article.category_id,
                category_name=category_name,
                main_keyword=article.keyword or "",
                secondary_keywords=keyword_brief.get("secondary_keywords", []),
                detected_intent=intent_analysis.get("explicit_intent", ""),
                expected_answer=intent_analysis.get("expected_answer", ""),
                article_type=intent_analysis.get("article_type", "evergreen_information"),
                outline_used=bool(outline.get("sections")),
                faq_generated=bool(article.faq_json),
                callouts_proposed=len(callout_plan.get("callouts", [])),
                images_proposed=len(image_plan_result.get("image_plan", {}).get("images", [])),
                internal_links_proposed=len(self.context.get("internal_links", {}).get("links", [])),
                external_links_proposed=len(self.context.get("external_links", {}).get("links", [])),
                research_status=research_brief.get("research_status", "not_available"),
                sources_used=[s.get("url", "") for s in research_brief.get("sources_consulted", []) if isinstance(s, dict)],
                tools_used=self.tools_used,
                tools_not_configured=self.tools_not_configured,
                adapters_status=adapters_status,
                word_count=article.word_count,
                reading_time_minutes=article.reading_time_minutes or 1,
                steps_completed=self.steps_completed,
                errors=self.errors,
                limitations=self.limitations,
                final_status=article.status,
                **cost_data,
            )
            article.generation_report_json = report
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
    )
