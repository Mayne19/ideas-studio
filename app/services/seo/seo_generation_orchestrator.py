from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable, TYPE_CHECKING

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
from app.services.seo.cannibalization_service import check_cannibalization_dict, check_section_cannibalization
from app.services.seo.intent_analysis_service import analyze_intent_dict, refine_intent_with_research
from app.services.seo.research_brief_service import build_research_brief_dict
from app.services.seo.source_quality_service import validate_sources
from app.services.seo.keyword_brief_service import build_keyword_brief_dict, refine_keyword_brief_with_research
from app.services.seo.editorial_angle_service import define_editorial_angle_dict
from app.services.seo.article_outline_planner import build_outline_dict
from app.services.seo.image_plan_service import build_image_plan_dict
from app.services.seo.writing_reference_examples import build_reference_examples_block
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
from app.services.seo.error_manager_service import analyze_generation_errors
from app.services.seo.adapters.serp_adapter import get_serp_adapter
from app.services.seo.adapters.trends_adapter import trends_adapter
from app.services.seo.adapters.image_sourcing_adapter import get_image_sourcing_adapter
from app.services.seo.adapters.language_adapter import language_adapter
from app.services.seo.adapters.content_extraction_adapter import content_extraction_adapter
from app.services.seo.adapters.scrapling_adapter import scrapling_adapter
from app.services.seo.adapters.originality_adapter import originality_adapter as orig_adapter
from app.services.seo.adapters.readability_adapter import readability_adapter
from app.services.seo.adapters.google_watch_adapter import google_watch_adapter


class WritingCancelledError(RuntimeError):
    """Levée quand l'utilisateur demande l'annulation d'une rédaction en cours."""


# Checks du checklist seo_final_checklist (seo_final_checklist_service.check_seo_final)
# considérés comme bloquants pour le référencement de base — le reste dégrade
# le score mais n'empêche pas l'article d'être fondamentalement indexable.
_SEO_FINAL_CRITICAL_CHECKS = {"title_present", "meta_title_present", "meta_description_present", "content_depth"}


def _seo_final_checklist_to_issues(seo_final: dict) -> list[dict]:
    """Convertit les checks échoués de seo_final_checklist (calculé sur le
    contenu réel du brouillon, cf. étape 21 de generate_full_article) en
    SeoIssue affichables. Sans ça, l'ArticleScore créé ici après génération
    porte un seo_score < 100 réel et détaillé (14 checks nommés) mais avec
    `issues` vide : l'éditeur affiche un score imparfait sans jamais dire
    lequel des 14 checks a échoué ni quoi corriger."""
    issues = []
    for check in seo_final.get("checks", []):
        if check.get("pass"):
            continue
        name = check.get("name", "")
        label = check.get("label", name)
        issues.append({
            "type": name,
            "category": "seo",
            "severity": "critical" if name in _SEO_FINAL_CRITICAL_CHECKS else "warning",
            "message": f"{label} — non validé.",
            "suggestion": f"Ajoutez/améliorez : {label}.",
            "section": "",
            "auto_fix_available": False,
        })
    return issues


_EDITORIAL_QUALITY_SEVERITY_MAP = {"error": "critical", "critical": "critical", "warning": "warning", "info": "info"}


def _editorial_quality_report_to_issues(quality_report: dict) -> list[dict]:
    """Même logique que _seo_final_checklist_to_issues, pour editorial_quality_gate
    (checks de forme éditoriale : H5/H6, gras abusif, traces IA, etc.), dont le
    score alimente aussi l'ArticleScore créé ici sans jamais exposer le détail."""
    issues = []
    for item in quality_report.get("issues", []):
        message = item.get("message", "")
        issues.append({
            "type": item.get("check", ""),
            "category": "quality",
            "severity": _EDITORIAL_QUALITY_SEVERITY_MAP.get(item.get("severity"), "warning"),
            "message": message,
            "suggestion": message.replace("Échec : ", "Corriger : ") if message else "",
            "section": "",
            "auto_fix_available": False,
        })
    return issues


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
        progress_cb: Callable[[str, int], None] | None = None,
    ):
        self.db = db
        # Appelé à chaque étape terminée (nom, nombre d'étapes) : suivi de
        # progression d'un job de génération en tâche de fond.
        self.progress_cb = progress_cb
        self.project_id = project_id
        self.llm = llm
        self.search = search
        self.agent_router = agent_router
        self.project = db.get(Project, project_id)
        # Clés résolues pour CE projet (Paramètres → Services externes, puis
        # config globale, puis env) — plus de singleton figé à l'import.
        self.serp_adapter = get_serp_adapter(project_id)
        self.image_sourcing_adapter = get_image_sourcing_adapter(project_id)
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
        if self.progress_cb is not None:
            try:
                self.progress_cb(name, len(self.steps_completed))
            except Exception:
                # La progression est informative : ne jamais casser la génération.
                pass

    def _error(self, step: str, message: str):
        self.errors.append(f"[{step}] {message}")
        self._log(message, level="error", step=step)

    def _check_tools(self):
        if self.serp_adapter.configured:
            self.tools_used.append("serpapi")
        else:
            self.tools_not_configured.append("serpapi")
            self.limitations.append("SERP provider not configured (Paramètres → Services externes, or SERPER_API_KEY env)")

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

    def _get_project_articles_for_originality(self, exclude_article_id: str | None) -> list[dict]:
        """Fournit à originality_service.score_internal_uniqueness() de quoi
        comparer réellement l'article contre les autres du projet — sans
        cette liste, ce signal (25% du score Originalité) retombait toujours
        sur son repli neutre 75/100, incapable de détecter un vrai doublon
        interne. Statuts alignés sur cannibalization_service (articles
        publiés ou en file, jamais archivés/rejetés), limité à 50 pour
        borner le coût de la comparaison n-gram."""
        rows = self.db.execute(
            select(Article, ArticleRevision.title, ArticleRevision.body)
            .join(ArticleRevision, ArticleRevision.id == Article.current_revision_id)
            .where(
                Article.project_id == self.project_id,
                Article.status_reason_id.in_((
                    ArticleStatus.PUBLISHED, ArticleStatus.DRAFT,
                    ArticleStatus.DRAFT_READY, ArticleStatus.IDEA_PROPOSED,
                    ArticleStatus.IDEA_PRIORITY,
                )),
            )
            .order_by(Article.updated_at.desc())
            .limit(50)
        ).all()
        return [
            {"id": article.id, "title": title or "", "content": body or ""}
            for article, title, body in rows
            if article.id != exclude_article_id
        ]

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
            "angle": angle or "",
            "source": "manual" if preferred_title else "category_strategy",
            "real_research_used": False,
            "opportunity_score": 0.7,
            "confidence_score": 0.5,
            "limitations": self.limitations.copy(),
        }
        # 3b. IdeaGenerator — sans titre ni mot-clé fournis, on tente une vraie
        # découverte d'idée (LLM + SERP + tendances, idea_discovery_service) au
        # lieu de rédiger sur un dict statique. Le repli reste le dict ci-dessus
        # si le provider ou la recherche sont indisponibles (point 10 du
        # pipeline : idea_generator réel).
        if not preferred_title and not keyword:
            try:
                from app.services.seo.idea_discovery_service import discover_ideas_dict
                # Une seule idée : seule ideas[0] est utilisée, en demander
                # davantage gaspillait un appel LLM par idée supplémentaire.
                ideas = discover_ideas_dict(
                    self.db, self.project_id, self.llm, self.search, count=1,
                    context_hint=context_hint,
                    project_audience=audience or project_context.get("target_audience"),
                    project_language=getattr(self.project, "language", "fr") or "fr",
                    category_strategy=category_strategy,
                )
                if ideas:
                    idea_discovery = dict(ideas[0])
                    idea_discovery.setdefault("limitations", self.limitations.copy())
                    if idea_discovery.get("real_research_used"):
                        self.tools_used.append("idea_research")
                else:
                    self.limitations.append("IdeaGenerator: aucune idée générée, repli statique")
            except Exception as exc:
                self._error("IdeaGenerator", str(exc))
        self.context["idea_discovery"] = idea_discovery
        self._step("IdeaDiscovery")

        final_title = preferred_title or idea_discovery.get("title", "Article")
        final_keyword = keyword or idea_discovery.get("main_keyword", "")

        if not final_keyword:
            # Repli slugify(titre) pollue tout le pipeline en aval (recherche
            # d'images, brief SEO, densité de mot-clé) avec une chaîne de
            # 100+ caractères au lieu d'un vrai mot-clé — on tente d'abord
            # une extraction LLM courte, le slug du titre reste le tout
            # dernier recours si le provider est indisponible.
            from app.services.agents.agent_services import extract_main_keyword
            keyword_extraction = extract_main_keyword(final_title, db=self.db, project_id=self.project_id)
            extracted = keyword_extraction.get("keyword")
            final_keyword = extracted if extracted else slugify(final_title)

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
        research_brief = build_research_brief_dict(
            final_keyword, final_title, category_name, project_id=self.project_id, serp_adapter=self.serp_adapter,
        )
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
            if not human_insights.get("total_insights", 0):
                from app.services.human_insights_lite_service import extract_human_insights_lite
                human_insights = extract_human_insights_lite(
                    keyword=final_keyword,
                    serp_results=serp_sources,
                    language=getattr(self.project, "language", "fr") or "fr",
                )
                if human_insights.get("total_insights", 0):
                    self.tools_used.append("human_insights_lite")
            self.context["human_insights"] = human_insights
            self._step(
                f"HumanInsights — {human_insights.get('total_insights', 0)} insights "
                f"depuis {len(human_insights.get('sources_scraped', []))} sources"
            )
        except Exception as exc:
            self._error("HumanInsights", str(exc))
            try:
                from app.services.human_insights_lite_service import extract_human_insights_lite
                human_insights = extract_human_insights_lite(
                    keyword=final_keyword,
                    serp_results=research_brief.get("sources_consulted", []),
                    language=getattr(self.project, "language", "fr") or "fr",
                )
                self.context["human_insights"] = human_insights
                self.tools_used.append("human_insights_lite")
                self._step(f"HumanInsightsLite — {human_insights.get('total_insights', 0)} insights")
            except Exception as lite_exc:
                self._error("HumanInsightsLite", str(lite_exc))
                self.context["human_insights"] = {}

        # 6d. ContentGap — manques éditoriaux détectés en croisant insights
        # humains, angles concurrents et articles déjà publiés par le projet
        try:
            from app.services.seo.content_gap_service import identify_content_gaps
            content_gaps = identify_content_gaps(
                final_keyword,
                final_title,
                research_brief=research_brief,
                human_insights=self.context.get("human_insights"),
                db=self.db,
                project_id=self.project_id,
                exclude_article_id=existing_article_id,
            )
            self.context["content_gaps"] = content_gaps
            self._step(
                f"ContentGap — {content_gaps.get('total_gaps', 0)} manques détectés "
                f"({content_gaps.get('status', 'unknown')})"
            )
        except Exception as exc:
            self._error("ContentGap", str(exc))
            self.context["content_gaps"] = {}

        # 6e. IntentAnalysisRefine — brief d'intention LLM (question réelle,
        # réponse attendue, must_include / must_avoid, format) appuyé sur la
        # SERP réelle. Il pilote l'angle, le plan et le writer ; un repli sur
        # l'heuristique est journalisé en warning, jamais silencieux.
        try:
            intent_analysis = refine_intent_with_research(
                intent_analysis, final_title, final_keyword, research_brief,
                db=self.db, project_id=self.project_id, idea_discovery=idea_discovery,
            )
            self.context["intent_analysis"] = intent_analysis
            refine_status = intent_analysis.get("intent_refine_status", "unknown")
            if refine_status != "ok":
                self.limitations.append(f"IntentAnalysisRefine: brief LLM indisponible ({refine_status}), repli heuristique")
                self._log(
                    f"Intent brief LLM unavailable ({refine_status}) — heuristic fallback, "
                    "no expected answer for the writer",
                    level="warning", step="IntentAnalysisRefine",
                )
            self._step(f"IntentAnalysisRefine ({refine_status}, format={intent_analysis.get('recommended_format')})")
        except Exception as exc:
            self._error("IntentAnalysisRefine", str(exc))

        # 6f. TitleGeneration — un article lancé avec un simple mot-clé
        # recevait ce mot-clé brut (en minuscules) comme titre publié.
        if not preferred_title and final_title.strip().lower() == final_keyword.strip().lower():
            from app.services.agents.agent_services import generate_article_title
            title_result = generate_article_title(
                final_keyword,
                reader_question=intent_analysis.get("reader_real_question"),
                expected_answer=intent_analysis.get("expected_answer"),
                competitor_titles=[s.get("title", "") for s in research_brief.get("sources_consulted", []) if isinstance(s, dict)],
                db=self.db,
                project_id=self.project_id,
            )
            if title_result.get("title"):
                final_title = title_result["title"]
                self._step("TitleGeneration")
            else:
                self.limitations.append(f"TitleGeneration: {title_result.get('message', 'échec')}")

        # L'agent d'intention peut avoir corrigé le type d'article : le plan
        # (étape 9) et la FAQ doivent lire la version affinée, pas l'ancienne.
        article_type = intent_analysis.get("article_type", "evergreen_information")

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

        # 7a. KeywordResearch — vrai enrichissement LLM du brief à partir des
        # résultats SERP réels : mots-clés secondaires, variantes longue traîne,
        # questions et entités réellement présents dans les pages classées
        # (point 8 du pipeline : keyword_research réel, remplace les variantes
        # stéréotypées de l'heuristique).
        try:
            keyword_brief = refine_keyword_brief_with_research(
                keyword_brief, final_keyword, research_brief, intent_analysis,
                db=self.db, project_id=self.project_id,
            )
            self.context["keyword_brief"] = keyword_brief
            self._step("KeywordResearch")
        except Exception as exc:
            self._error("KeywordResearch", str(exc))

        # 7b. EvidencePack — sélection des faits/sources les plus fiables parmi
        # ceux déjà trouvés par ResearchBrief, pour guider la rédaction
        try:
            from app.services.agents.agent_services import build_evidence_pack
            evidence_pack = build_evidence_pack(
                final_keyword, final_title, research_brief, db=self.db, project_id=self.project_id,
            )
            self.context["evidence_pack"] = evidence_pack
            self._step("EvidencePack")
        except Exception as exc:
            self._error("EvidencePack", str(exc))
            self.context["evidence_pack"] = {}

        # 8. EditorialAngle
        editorial_angle = define_editorial_angle_dict(
            final_title, final_keyword, intent_analysis, research_brief, category_name
        )
        self.context["editorial_angle"] = editorial_angle
        self._step("EditorialAngle")

        # 9. ArticleOutline
        from app.core.config import settings as app_settings
        outline = build_outline_dict(
            final_title, final_keyword, intent_analysis, research_brief,
            keyword_brief, editorial_angle, article_type,
            outline_planner_mode=app_settings.OUTLINE_PLANNER_MODE,
            db=self.db,
            project_id=self.project_id,
        )
        self.context["outline"] = outline
        self.context["outline_planner_mode"] = app_settings.OUTLINE_PLANNER_MODE
        self._step(f"ArticleOutline ({app_settings.OUTLINE_PLANNER_MODE})")

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

        # 9c. Cannibalisation au niveau des sections (H2/H3) — deux articles
        # peuvent avoir des titres/mots-clés différents tout en traitant les
        # mêmes sous-sujets ; check_cannibalization_dict seul ne le détecte pas.
        section_cannibalization = check_section_cannibalization(
            self.db, self.project_id, outline, exclude_article_id=existing_article_id
        )
        self.context["section_cannibalization"] = section_cannibalization
        if section_cannibalization.get("risk_level") != "none":
            self._log(
                f"Section overlap detected : {len(section_cannibalization.get('overlapping_sections', []))} "
                f"article(s) partagent des sous-thèmes avec ce plan",
                level="warning", step="CannibalizationCheckOutline",
            )

        # 10. ImagePlan
        image_plan_result = self._plan_images(final_keyword, outline)
        self._step("ImagePlan")

        # 11. CalloutPlan
        callout_plan = build_callout_plan_dict(self.db, self.project_id, final_keyword, outline)
        self.context["callout_plan"] = callout_plan
        self._step("CalloutPlan")

        # 12. FAQPlan
        faq_plan = build_faq_plan_dict(final_keyword, intent_analysis)
        self.context["faq_plan"] = faq_plan
        self._step("FAQPlan")

        # 13. InternalLinkPlan
        from app.services.seo.article_editorial_tier_service import resolve_editorial_tier
        editorial_tier = resolve_editorial_tier(self.db, self.project_id, chosen_category, existing_article_id)
        self.context["editorial_tier"] = editorial_tier
        internal_links = build_internal_link_plan_dict(
            self.db, self.project_id, final_keyword, chosen_category,
            cannibalization_hints=cannibalization_hints,
            editorial_tier=editorial_tier,
        )
        self.context["internal_links"] = internal_links
        self._step("InternalLinkPlan")

        # 14. ExternalLinkPlan
        external_links = build_external_link_plan_dict(final_keyword, research_brief, project_id=self.project_id, db=self.db)
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
            if not article.editorial_tier:
                article.editorial_tier = editorial_tier
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
                editorial_tier=editorial_tier,
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
        self._save(article.id, "section_cannibalization", section_cannibalization)
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
        self._save(article.id, "content_gaps", self.context.get("content_gaps") or {})

        # Plage de mots : catégorie (prioritaire) puis profil éditorial projet
        wc_min, wc_max = None, None
        editorial_profile = self.project.active_editorial_profile if self.project else None
        if article.category_id:
            cat = self.db.get(Category, article.category_id)
            if cat:
                overrides = cat.overrides or {}
                wc_min = overrides.get("word_count_min")
                wc_max = overrides.get("word_count_max")
        if not wc_min and not wc_max:
            if editorial_profile:
                wc_min = editorial_profile.word_count_min
                wc_max = editorial_profile.word_count_max

        if editorial_profile and (editorial_profile.tone or editorial_profile.reader_level or editorial_profile.writing_style):
            from app.services.agents.agent_services import adapt_editorial_style
            style_adaptation = adapt_editorial_style(
                editorial_profile.tone, editorial_profile.reader_level, editorial_profile.writing_style,
                final_title, final_keyword, angle=editorial_angle.get("main_angle"),
                db=self.db, project_id=self.project_id,
            )
            self.context["style_adaptation"] = style_adaptation
            self._save(article.id, "style_adaptation", style_adaptation)
            self.context["tone"] = style_adaptation.get("tone") or editorial_profile.tone
            self.context["reader_level"] = style_adaptation.get("reader_level") or editorial_profile.reader_level
            self.context["writing_style"] = style_adaptation.get("writing_style") or editorial_profile.writing_style

        # Passer la plage au prompt du writer
        if wc_min or wc_max:
            wc_instruction = []
            if wc_min:
                wc_instruction.append(f"minimum {wc_min} mots")
            if wc_max:
                wc_instruction.append(f"maximum {wc_max} mots")
            self.context["word_count_range"] = " et ".join(wc_instruction)
            self.context["word_count_min"] = wc_min
            self.context["word_count_max"] = wc_max

        # 14c. ProductionBrief — verrouille le brief consolidé du writer
        try:
            from app.services.production_brief_service import build_production_brief
            production_brief = build_production_brief(
                keyword=final_keyword,
                title=final_title,
                category_name=category_name,
                project_context=self.context.get("project_context"),
                intent_analysis=intent_analysis,
                keyword_brief=keyword_brief,
                research_brief=research_brief,
                evidence_pack=self.context.get("evidence_pack"),
                editorial_angle=editorial_angle,
                outline=outline,
                human_insights=self.context.get("human_insights"),
                content_gaps=self.context.get("content_gaps"),
                word_count_range=self.context.get("word_count_range"),
                audience=audience,
                tone=self.context.get("tone"),
                reader_level=self.context.get("reader_level"),
                writing_style=self.context.get("writing_style"),
            )
            self.context["production_brief"] = production_brief
            self._save(article.id, "production_brief", production_brief)
            self._step("ProductionBrief")
        except Exception as exc:
            self._error("ProductionBrief", str(exc))
            self.context["production_brief"] = None

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

        # 15b. HumanInsightsUsageGuard — vérifie que la matière humaine réelle
        # a effectivement nourri le contenu (pas seulement été incluse dans le
        # prompt). Non bloquant : avertit si le writer l'a ignorée.
        try:
            self._verify_human_insights_usage(draft.content)
        except Exception as exc:
            self._error("HumanInsightsUsageGuard", str(exc))

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
            project_articles = self._get_project_articles_for_originality(article.id)
            originality = check_originality_dict(draft.content, sources_list, project_articles, draft.title)
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
                    cover_image_url=self.context.get("cover_image_url"),
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
                geo_result = compute_geo_score(draft, evidence_pack=self.context.get("evidence_pack"))
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
                min_word_count=self.context.get("word_count_min"),
            )
            self._save(article.id, "seo_final_checklist", seo_final)
            self._step("SEOFinalChecklist")
        except Exception as exc:
            self._error("SEOFinalChecklist", str(exc))
            seo_final = None

        # 21b. AutoScoring — seulement maintenant que eeat_checklist,
        # readability_report, originality_report et seo_final_checklist existent tous
        # (étapes 16-21 ci-dessus). Score informatif : aucune réécriture déclenchée.
        self._score_article(article, draft)

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

        # 19d. ClaimExtraction — isole les affirmations vérifiables avant le
        # fact-check complet (donne au fact-checker une base déjà identifiée)
        try:
            if self.agent_router is not None:
                from app.services.agents.agent_services import extract_claims
                claims = extract_claims(draft.content or "", draft.title, db=self.db, project_id=self.project_id)
                self._save(article.id, "extracted_claims", claims)
                self._step("ClaimExtraction")
        except Exception as exc:
            self._error("ClaimExtraction", str(exc))

        # 20b. FactCheckPass (LLM-based)
        try:
            if self.agent_router is not None:
                from app.services.agents.agent_services import fact_check_article
                fact_check = fact_check_article(draft.content or "", draft.title, draft.keyword, db=self.db, project_id=self.project_id)
                self._save(article.id, "fact_check_report", fact_check)
                self._step("FactCheckPass")
        except Exception as exc:
            self._error("FactCheckPass", str(exc))

        # 20c. QualityGate (LLM-based) — UN SEUL juge consolide la revue
        # éditoriale, la rétention, l'engagement et la notation qualité en une
        # seule décision (quality_grade). Évite les avis contradictoires de
        # juges séparés évaluant le même texte.
        try:
            if self.agent_router is not None:
                from app.services.agents.agent_services import run_quality_gate
                gate = run_quality_gate(
                    draft.content or "", draft.title, draft.keyword,
                    db=self.db, project_id=self.project_id,
                )
                editorial_quality_report = self._get(article.id, "editorial_quality_report") or {}
                editorial_quality_report["llm_review"] = gate
                if gate.get("quality_grade") and gate["quality_grade"] != "unknown":
                    editorial_quality_report["quality_grade"] = gate["quality_grade"]
                self._save(article.id, "editorial_quality_report", editorial_quality_report)
                self._step(f"QualityGate — grade {gate.get('quality_grade', 'unknown')}")
        except Exception as exc:
            self._error("QualityGate", str(exc))

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
        from app.services.agents.agent_router import AgentProviderAssignmentError
        if self.agent_router is not None:
            try:
                return self.agent_router.get_provider(agent_id, project_id=self.project_id)
            except AgentProviderAssignmentError:
                # Un provider est explicitement assigné à cet agent mais sa
                # construction a échoué (clé invalide/indéchiffrable) : ne
                # jamais basculer silencieusement sur le fallback global,
                # l'erreur doit être visible telle quelle pour cet agent.
                raise
            except Exception:
                pass
        return fallback or self.llm

    def _write_through_agent(self, prompt: str, agent_id: str, **kwargs) -> str:
        provider = self._get_agent_provider(agent_id)
        return provider.generate_text(prompt, **kwargs)

    def _write_pass(self, prompt: str, agent_id: str, article, temperature: float, step: str,
                    system: str | None = None) -> str:
        """Une passe d'écriture/révision via le provider d'un agent donné.
        Retourne le texte brut ; lève GenerationFailedError si le provider
        est mock ou ne produit rien (chaque passe est bloquante)."""
        if self.agent_router is not None:
            from app.services.agents.agent_router import call_agent
            content, result = call_agent(
                agent_id,
                "generate_text",
                prompt,
                db=self.db,
                project_id=self.project_id,
                article_id=article.id,
                system=system,
                temperature=temperature,
            )
            if result.status != "success":
                raise GenerationFailedError(result.error or f"L'agent {agent_id} a échoué.")
        else:
            provider = self._get_agent_provider(agent_id, self.llm)
            if provider.is_mock:
                raise GenerationFailedError(f"Provider non configuré pour l'agent {agent_id}.")
            content = provider.generate_text(prompt, system=system, temperature=temperature)
        if not content or not content.strip():
            raise GenerationFailedError(f"L'agent {agent_id} n'a pas retourné de contenu exploitable.")
        self._step(step)
        return content

    def _guarded_rewrite_pass(self, content: str, prompt: str, agent_id: str, article, temperature: float, step: str,
                              system: str | None = None) -> str:
        """Passe de réécriture d'un article complet qui ne peut jamais remplacer
        l'article par une sortie tronquée : en cas d'échec de l'appel (dont
        finish_reason == "length") ou si la réponse perd plus de 25 % des mots
        (au-delà de la réduction attendue vers le maximum de mots), l'article
        d'entrée est conservé tel quel."""
        try:
            rewritten = self._write_pass(prompt, agent_id, article, temperature, step, system=system)
        except GenerationFailedError as exc:
            self._error(step, f"Passe ignorée, contenu précédent conservé : {exc}")
            return content
        original_words = calculate_word_count(content)
        try:
            wc_max = int(self.context.get("word_count_max") or 0)
        except (TypeError, ValueError):
            wc_max = 0
        reference = min(original_words, wc_max) if wc_max > 0 else original_words
        rewritten_words = calculate_word_count(rewritten)
        if rewritten_words < reference * 0.75:
            self._error(
                step,
                f"Réponse rejetée : {rewritten_words} mots contre {original_words} avant la passe "
                "(troncature probable) — contenu précédent conservé.",
            )
            return content
        return rewritten

    def _build_checklist_verification_block(self) -> str:
        """Checklist de vérification mécanique pour la passe QualityGate (Pass 2,
        gate_prompt) : conformité aux exigences mécaniques (plage de mots).
        Les liens et statistiques ne sont volontairement plus imposés ici : les
        forcer poussait le modèle à inventer des chiffres et à placer des liens
        sans rapport avec le texte. Construite dynamiquement depuis self.context ; ne plante
        jamais sur un contexte incomplet (chaîne vide si rien de pertinent)."""
        checklist: list[str] = []

        wc_max = self.context.get("word_count_max")
        if wc_max:
            # Seul le maximum est vérifié : demander de « développer » sous le
            # minimum poussait le modèle à délayer la réponse.
            checklist.append(
                f"Ne dépasse pas {wc_max} mots ; si c'est le cas, coupe les passages les moins utiles. "
                "N'ajoute jamais de texte pour allonger l'article."
            )

        if not checklist:
            return ""
        # "Vérifie ces points" seul laisse le modèle survoler la liste sans
        # vraiment statuer sur chacun — demander un oui/non explicite par point
        # (en interne, avant la réponse finale) force un vrai passage en revue
        # plutôt qu'une lecture en diagonale. Le raisonnement lui-même n'est
        # jamais retourné : seule la consigne de sortie (HTML uniquement)
        # compte pour le parsing en aval, inchangée.
        lines = [
            "",
            "Avant de répondre, vérifie ce texte point par point ci-dessous. Pour "
            "chaque point, détermine mentalement s'il est déjà respecté (oui/non) "
            "dans le texte que tu vas renvoyer. Pour chaque point répondu \"non\", "
            "corrige-le silencieusement avant de produire ta réponse finale. Ne "
            "montre jamais ce raisonnement point par point dans ta réponse — "
            "uniquement le HTML final corrigé.",
            "",
            "Points à vérifier un par un :",
        ]
        lines += [f"- {item}" for item in checklist]
        return "\n".join(lines)

    def _verify_human_insights_usage(self, content: str) -> None:
        """Garde-fou non bloquant : si des insights humains réels étaient
        disponibles avant la rédaction, on vérifie que le contenu généré les
        réutilise effectivement (source URL ou fragment textuel). Un article
        qui ignore totalement cette matière retombe dans du générique."""
        insights = self.context.get("human_insights") or {}
        if not insights or insights.get("total_insights", 0) == 0:
            return

        content_lower = (content or "").lower()
        sourced = [
            i for i in insights.get("all_insights", [])
            if isinstance(i, dict) and i.get("source_url")
        ]
        source_urls = {str(i.get("source_url", "")).lower() for i in sourced}
        questions = insights.get("questions") or []
        pain_points = insights.get("pain_points") or []

        def _fragment_used(fragment: str) -> bool:
            fragment = fragment.strip().lower()
            if len(fragment) < 20:
                return False
            for token in fragment.split()[:5]:
                if token not in content_lower:
                    return False
            return True

        used_url = any(url in content_lower for url in source_urls if url)
        used_text = any(_fragment_used(q) for q in questions[:15]) or any(
            _fragment_used(p) for p in pain_points[:15]
        )

        if not used_url and not used_text:
            self._log(
                f"{len(insights.get('all_insights', []))} insights humains étaient disponibles "
                f"mais aucun n'a été intégré au contenu (ni URL source, ni reformulation visible).",
                level="warning",
                step="HumanInsightsUsageGuard",
            )
            self.limitations.append("human_insights_ignored: insights humains non réutilisés dans le contenu")
        else:
            self._step("HumanInsightsUsageGuard")
            self.tools_used.append("human_insights_usage")

    def _build_writer_system_prompt(self) -> str:
        """Règles de voix et de style, envoyées en prompt système pour rester
        séparées du brief et des consignes de la tâche. La liste des connecteurs
        bannis est la même que celle des contrôles de style (TRANSITION_BLACKLIST)."""
        from app.services.seo.content_structure_guard import TRANSITION_BLACKLIST
        rules = [
            "Tu es un rédacteur spécialisé qui écrit en français pour des lecteurs pressés. "
            "Tu réponds précisément à leur question, sans remplissage.",
            "Style :",
            "- Chaque phrase apporte une information concrète ; supprime celles qui n'apportent rien.",
            "- Paragraphes courts (1 à 4 phrases), rythme varié.",
            "- Ton direct et naturel, comme un expert qui explique à quelqu'un qu'il respecte.",
            "- Pas d'ouverture générique (« Dans un monde où », « Il est important de », « Dans cet article »).",
            "- Pas de superlatifs vides (ultime, incontournable, révolutionnaire) ni de jargon "
            "(synergie, levier, écosystème, booster, holistique).",
            "- Pas de connecteur de remplissage en début de phrase : "
            + ", ".join(c.capitalize() for c in TRANSITION_BLACKLIST) + ".",
            "- Jamais de tiret cadratin (—) : utilise une virgule, deux-points ou une nouvelle phrase.",
            "- Appelle un produit, une marque, un outil ou une personne par son nom (« Webflow », pas "
            "« cet outil » ni « la plateforme »). Répéter un nom propre est normal ; une périphrase "
            "n'est utile que si le nom vient d'être cité dans la même phrase.",
        ]
        style_bits = [
            f"{label} : {self.context[key]}"
            for label, key in (("Ton", "tone"), ("Niveau du lecteur", "reader_level"), ("Style", "writing_style"))
            if self.context.get(key)
        ]
        if style_bits:
            rules.append("Profil éditorial du projet : " + " ; ".join(style_bits) + ".")
        style_guide = (self.context.get("style_adaptation") or {}).get("style_guide")
        if isinstance(style_guide, dict) and style_guide.get("rules"):
            rules.append("Guide de style du projet :")
            rules.extend(f"- {rule}" for rule in style_guide["rules"][:8])
        return "\n".join(rules)

    def _build_section_writer(self, draft: _DraftArticle, production_brief: dict, outline: dict,
                              include_callouts: bool | None, writer_system: str):
        """Prépare le rédacteur section par section : brief compact commun à
        tous les appels, plan regroupé (H3 sous leur H2), budget de mots par
        section et sources citables."""
        from app.services.seo.article_outline_planner import resolve_outline_format
        from app.services.seo.section_writer import (
            OutlineSection, SectionWriter, build_section_brief, compute_words_per_section,
            group_outline_sections,
        )
        article = draft.article
        sections = group_outline_sections(outline)
        if not sections:
            sections = [OutlineSection(
                heading=production_brief.get("reader_real_question") or draft.title or draft.keyword or "",
            )]
        fmt = resolve_outline_format(self.context.get("intent_analysis"), production_brief.get("article_type"))

        brief_parts = [build_section_brief(production_brief)]
        used_angles = (self.context.get("project_context") or {}).get("used_angles") or []
        if used_angles:
            brief_parts.append("Angles déjà publiés sur ce projet (ne les répète pas) : " + "; ".join(used_angles[:6]))
        insights = self.context.get("human_insights") or {}
        if insights.get("total_insights", 0) > 0:
            for label, key, limit in (
                ("Questions réelles de lecteurs", "questions", 4),
                ("Difficultés rencontrées", "pain_points", 4),
                ("Exemples réels", "real_examples", 3),
            ):
                if insights.get(key):
                    brief_parts.append(f"{label} (si utile) : " + " ; ".join(str(x) for x in insights[key][:limit]))
        if include_callouts:
            brief_parts.append(
                "Un encadré <blockquote> est permis si une mise en garde ou une astuce le mérite vraiment."
            )
        brief_parts.append("Pas de FAQ : elle est générée séparément.")

        def write_fn(prompt: str, step: str, temperature: float) -> str:
            self._raise_if_cancelled(article)
            return self._write_pass(prompt, "writer", article, temperature, step, system=writer_system)

        def _links(key: str) -> list:
            plan = self.context.get(key) or {}
            return plan.get("links") or [] if isinstance(plan, dict) else []

        return SectionWriter(
            write_fn,
            "\n".join(brief_parts),
            sections,
            fmt=fmt,
            words_per_section=compute_words_per_section(
                len(sections), self.context.get("word_count_min"), self.context.get("word_count_max"),
            ),
            external_links=_links("external_links"),
            internal_links=_links("internal_links"),
            conclusion_title=(outline or {}).get("conclusion_title") or "",
            style_example=build_reference_examples_block(),
            fatal_exceptions=(WritingCancelledError,),
        )

    def _ensure_outline_complete(self, section_writer, content: str, step: str) -> str:
        """Garde-fou de complétude : chaque H2 du plan doit être présent ;
        seules les sections absentes sont régénérées."""
        if not section_writer.missing_sections(content):
            return content
        content, regenerated, still_missing = section_writer.ensure_complete(content)
        if regenerated:
            self._log(
                f"{len(regenerated)} section(s) absente(s) régénérée(s) : {', '.join(regenerated)}",
                level="warning", step=step,
            )
        if still_missing:
            self._error(step, f"Section(s) toujours absente(s) : {', '.join(still_missing)}")
            self.limitations.append(f"missing_sections: {', '.join(still_missing)}")
        return content

    def _polish_call_fn(self, article: Article):
        """Appel court via l'agent writer (même modèle bon marché que la
        rédaction) pour les passes de finition."""
        def call(prompt: str, step: str, temperature: float) -> str:
            self._raise_if_cancelled(article)
            return self._write_pass(prompt, "writer", article, temperature, step)
        return call

    def _keep_if_h2_lost(self, before: str, after: str, step: str) -> str:
        """Garde-fou commun des passes de finition : une passe qui fait
        disparaître un H2 est annulée."""
        from app.services.seo.section_writer import lost_h2s
        dropped = lost_h2s(before, after)
        if dropped:
            self._error(step, f"Passe annulée : section(s) H2 perdue(s) ({', '.join(dropped[:3])}).")
            return before
        return after

    def _proper_nouns(self, draft: _DraftArticle) -> list[str]:
        import re as _re
        sources = [draft.title or "", draft.keyword or ""]
        sources += [s.get("heading", "") for s in (self.context.get("outline") or {}).get("sections") or [] if isinstance(s, dict)]
        nouns: list[str] = []
        for text in sources:
            # Mots capitalisés hors premier mot : noms propres probables.
            for word in _re.findall(r"\w[\w'-]*", text)[1:]:
                if word[:1].isupper() and len(word) >= 3 and word not in nouns:
                    nouns.append(word)
        known = {n.lower() for n in nouns}
        for token in (draft.keyword or "").split():
            if len(token) >= 4 and token.lower() not in known and token.lower() not in {"pour", "avec", "dans", "comment"}:
                nouns.append(token.capitalize())
                known.add(token.lower())
        return nouns[:12]

    def _proofread_pass(self, article: Article, draft: _DraftArticle, content: str) -> str:
        """Relecture orthographique par section (jetons corrompus, accords),
        sortie rejetée si la structure, les chiffres ou les liens changent."""
        from app.services.seo.section_proofreader import proofread_article
        try:
            proofread, report = proofread_article(
                content, self._polish_call_fn(article),
                proper_nouns=self._proper_nouns(draft),
                fatal_exceptions=(WritingCancelledError,),
            )
        except WritingCancelledError:
            raise
        except Exception as exc:
            self._error("ProofreadingPass", f"Relecture ignorée : {exc}")
            return content
        proofread = self._keep_if_h2_lost(content, proofread, "ProofreadingPass")
        self._save(article.id, "proofreading_report", report)
        self._step(f"ProofreadingPass ({report['corrected']} corrigée(s), {report['rejected']} rejetée(s))")
        return proofread

    def _consistency_pass(self, article: Article, content: str) -> str:
        """Contradictions chiffrées et phrases répétées entre l'introduction
        et les sections : un appel de détection, corrections phrase par
        phrase appliquées par le code, tracées dans l'artefact
        consistency_report."""
        from app.services.seo.consistency_checker import check_and_fix_consistency
        brief = self.context.get("production_brief") or {}
        facts = []
        for item in brief.get("evidence_items") or []:
            if isinstance(item, dict) and item.get("fact"):
                fact = str(item["fact"])
                if item.get("figure"):
                    fact += f" [{item['figure']}]"
                facts.append(fact)
        try:
            fixed, report = check_and_fix_consistency(
                content, self._polish_call_fn(article),
                verified_facts=facts, fatal_exceptions=(WritingCancelledError,),
            )
        except WritingCancelledError:
            raise
        except Exception as exc:
            self._error("ConsistencyPass", f"Contrôle de cohérence ignoré : {exc}")
            return content
        fixed = self._keep_if_h2_lost(content, fixed, "ConsistencyPass")
        self._save(article.id, "consistency_report", report)
        if report.get("applied"):
            self._log(
                f"Cohérence : {len(report['applied'])} phrase(s) corrigée(s) ou supprimée(s) "
                f"sur {report.get('issues_found', 0)} problème(s) signalé(s).",
                level="info", step="ConsistencyPass", article_id=article.id,
            )
        self._step(f"ConsistencyPass ({len(report.get('applied') or [])} correction(s))")
        return fixed

    def _citation_pass(self, article: Article, draft: _DraftArticle, content: str) -> str:
        """1 à 3 citations externes (sources fiables avec extrait) et jusqu'à
        2 liens internes, posés par le code sur des phrases choisies par le
        modèle ; une source sans phrase qui lui corresponde est ignorée."""
        from app.services.seo.citation_inserter import insert_citations

        def _links(key: str) -> list:
            plan = self.context.get(key) or {}
            return (plan.get("links") or []) if isinstance(plan, dict) else []

        try:
            linked, report = insert_citations(
                content, self._polish_call_fn(article),
                _links("external_links"), _links("internal_links"),
                keyword=draft.keyword or "",
                fatal_exceptions=(WritingCancelledError,),
            )
        except WritingCancelledError:
            raise
        except Exception as exc:
            self._error("CitationPass", f"Insertion des liens ignorée : {exc}")
            return content
        linked = self._keep_if_h2_lost(content, linked, "CitationPass")
        self._save(article.id, "citation_report", report)
        inserted = report.get("inserted") or []
        external = sum(1 for i in inserted if i.get("type") == "external")
        if report.get("candidates_external") and not external and not report.get("existing_external"):
            self.limitations.append("no_external_citation: aucune phrase ne correspond aux sources fiables")
        self._step(f"CitationPass ({external} externe(s), {len(inserted) - external} interne(s))")
        return linked

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

        production_brief = self.context.get("production_brief")
        if not production_brief:
            from app.services.production_brief_service import build_production_brief
            production_brief = build_production_brief(
                keyword=draft.keyword or "", title=draft.title or "",
                intent_analysis=self.context.get("intent_analysis"),
                keyword_brief=keyword_brief, outline=outline,
                editorial_angle=self.context.get("editorial_angle"),
                audience=draft.audience,
            )
        # ── Pass 1 — Rédaction section par section (temp 0.7) ──────────────
        # Introduction, puis un appel par H2 du plan, puis une fin si le format
        # la justifie, assemblés par le code. Un seul appel pour l'article
        # entier faisait sauter des sections sur les modèles bon marché
        # (3 sections sur 5, sans fin, sans que rien ne le détecte).
        from app.services.seo.section_writer import SectionWritingError
        writer_system = self._build_writer_system_prompt()
        section_writer = self._build_section_writer(
            draft, production_brief, outline, include_callouts, writer_system,
        )
        try:
            content = section_writer.write_article()
        except SectionWritingError as exc:
            raise GenerationFailedError(str(exc)) from exc
        content = self._ensure_outline_complete(section_writer, content, "SectionCompleteness_Draft")

        self._raise_if_cancelled(article)

        # ── Pass 2 — QualityGate (temp 0.3) ────────────────────────────────
        # Unique passe d'édition après le premier jet (les anciennes passes de
        # cohérence et de style réécrivaient tout l'article et diluaient le fond).
        # Passe froide : suppression des redondances, des phrases creuses,
        # vérification de la densité du mot-clé et de la conformité aux règles.
        gate_prompt = (
            "Passe de contrôle qualité finale sur cet article. Corrige : les phrases "
            "redondantes ou creuses, les mots courants répétés de près, les ouvertures "
            "génériques, les superlatifs vides, l'expression-clé complète répétée mécaniquement. "
            "Ne remplace jamais un nom propre (produit, marque, outil) par « cet outil », "
            "« la plateforme » ou un pronom : le nom reste. "
            "Ne change ni le plan (garde chaque titre <h2> et <h3> mot pour mot), ni les faits, "
            "ni les données, ni les liens. "
            "Garde la réponse directe des premières phrases intacte. "
            "Règle absolue : pas de tiret cadratin (—), remplace-le par une virgule, "
            "un point-virgule ou une reformulation."
            + self._build_checklist_verification_block()
            + "\n\nRetourne UNIQUEMENT le HTML complet nettoyé, sans explication, sans backticks.\n\n"
            f"Contenu :\n{content}"
        )
        gated = self._guarded_rewrite_pass(
            content, gate_prompt, "writer", article, 0.3, "WritingPass_QualityGate", system=writer_system,
        )
        # La passe d'édition réécrit l'article entier en un appel : si elle
        # perd un H2, on garde le premier jet plutôt qu'un article amputé.
        from app.services.seo.section_writer import lost_h2s
        dropped_h2 = lost_h2s(content, gated)
        if dropped_h2:
            self._error(
                "WritingPass_QualityGate",
                f"Réponse rejetée : {len(dropped_h2)} section(s) H2 perdue(s) "
                f"({', '.join(dropped_h2[:3])}) — contenu précédent conservé.",
            )
        else:
            content = gated
        content = self._ensure_outline_complete(section_writer, content, "SectionCompleteness_Final")

        # ── Finition — appels courts et ciblés, jamais de réécriture libre ──
        content = self._proofread_pass(article, draft, content)
        content = self._consistency_pass(article, content)
        content = self._citation_pass(article, draft, content)
        # Chaque passe de finition annule déjà sa sortie si un H2 disparaît ;
        # le garde-fou de complétude du plan reste le dernier filet.
        content = self._ensure_outline_complete(section_writer, content, "SectionCompleteness_Polish")
        self._save(article.id, "section_writing_report", section_writer.report)

        self._raise_if_cancelled(article)

        from app.services.seo.content_structure_guard import (
            apply_structure_guards, check_style_compliance, check_word_count_compliance,
        )
        content = apply_structure_guards(content, draft.title)

        illustration_cfg = self.context.get("illustration_config")
        if illustration_cfg is not None and illustration_cfg.mode == "ai":
            self.context["image_sources"] = self._generate_illustrations(article, draft, outline, content, illustration_cfg)

        image_sources = self.context.get("image_sources") or []
        if image_sources:
            from app.services.seo.image_plan_service import (
                insert_images_in_content, localize_image_alts, pick_cover_source, track_unsplash_downloads,
            )
            # Alt dans la langue de l'article (un seul appel court), jamais
            # l'alt anglais brut d'Unsplash ; repli : titre de section.
            article_language = ((self.project.locale if self.project else None) or "fr").split("-")[0]
            localize_image_alts(
                content, image_sources, article_language, draft.keyword,
                db=self.db, project_id=self.project_id,
            )
            content = insert_images_in_content(content, image_sources)
            # Trace des alts localisés et des images réellement insérées.
            self._save(article.id, "image_sources", {"items": image_sources})
            try:
                track_unsplash_downloads(image_sources, self.image_sourcing_adapter)
            except Exception as exc:
                self._error("ImageDownloadTracking", str(exc))
            try:
                from app.services.cover_image_service import set_cover_image_if_missing
                cover_url = set_cover_image_if_missing(self.db, article, pick_cover_source(image_sources))
                if cover_url:
                    self.context["cover_image_url"] = cover_url
            except Exception as exc:
                self._error("CoverImage", str(exc))

        draft.content = content
        draft.word_count = calculate_word_count(content)
        draft.reading_time_minutes = calculate_reading_time_minutes(draft.word_count)

        word_count_check = check_word_count_compliance(
            draft.word_count, self.context.get("word_count_min"), self.context.get("word_count_max"),
        )
        self._save(article.id, "word_count_check", word_count_check)
        if word_count_check["status"] in ("under_minimum", "over_maximum"):
            self._log(
                f"Volume hors plage : {draft.word_count} mots ({word_count_check['status']}, "
                f"cible {word_count_check.get('target_min')}-{word_count_check.get('target_max')})",
                level="warning", step="word_count_check",
            )

        style_check = check_style_compliance(content)
        self._save(article.id, "style_check", style_check)
        if style_check.get("issue_count"):
            self._log(
                f"{style_check['issue_count']} signal(aux) de style détecté(s) : "
                f"{', '.join(style_check['issues'][:5])}",
                level="warning", step="style_check",
            )

        from app.services.seo.human_presence_service import compute_human_presence_score
        human_presence_report = compute_human_presence_score(content, draft.word_count)
        self._save(article.id, "human_presence_report", human_presence_report)
        if human_presence_report.get("score") is not None and human_presence_report["score"] < 70:
            self._log(
                f"Présence humaine faible : {human_presence_report['score']}/100 "
                f"({', '.join(human_presence_report['flags'][:5])})",
                level="warning", step="human_presence_check",
            )

        from app.services.seo.article_reviewer_service import review_article
        review_report = review_article(
            content, draft.word_count,
            title=draft.title, keyword=draft.keyword, db=self.db, project_id=self.project_id,
        )
        self._save(article.id, "article_review_report", review_report)
        if review_report.get("decision") in ("REECRITURE", "REVISION_AUTOMATIQUE"):
            self._log(
                f"Agent réviseur : {review_report.get('decision')} "
                f"(score {review_report.get('total_score')}/90, "
                f"bloquants : {review_report.get('blocking_triggered') or 'aucun'})",
                level="warning", step="article_review",
            )

        # Le verdict de l'agent réviseur reste informatif : aucune passe de
        # réécriture n'est déclenchée sur ses critères bloquants (ouverture
        # générique, position tranchée, moment de surprise...). Ces réécritures
        # ciblaient des signaux de surface et dégradaient le fond de l'article.

        from app.services.seo.article_tier_service import compute_volume_tiers
        volume_tiers = compute_volume_tiers(content)
        self._save(article.id, "volume_tiers", volume_tiers)
        self._log(
            f"Volumétrie : tier {volume_tiers['article_tier']} ({volume_tiers['article_words']} mots), "
            f"{sum(1 for s in volume_tiers['sections'] if s['section_tier'] == 'deep')} sections approfondies",
            level="info", step="volume_tiers",
        )

        self._ensure_slug(article, draft.title, draft.keyword)

        from app.services.seo.content_structure_guard import clean_meta_text

        if not draft.meta_title:
            meta_prompt = (
                f"Écris un meta title SEO (max 60 caractères) pour : {draft.title}. Mot-clé : {draft.keyword}\n"
                "Réponds UNIQUEMENT avec le meta title, sans Markdown, sans introduction, "
                "sans analyse, sans note de longueur, une seule ligne de texte brut."
            )
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
                raw_title = meta_title if result.status == "success" else ""
            else:
                title_llm = self._get_agent_provider("meta_writer", writer_llm)
                raw_title = title_llm.generate_text(meta_prompt, temperature=0.3) or ""
            draft.meta_title = clean_meta_text(raw_title, 255) or draft.title[:255]

        if not draft.meta_description:
            desc_prompt = (
                f"Écris une meta description SEO (140-160 caractères) pour : {draft.title}. Mot-clé : {draft.keyword}\n"
                "Réponds UNIQUEMENT avec la meta description, sans Markdown, sans introduction, "
                "sans analyse, sans note de longueur, un seul paragraphe de texte brut."
            )
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
                raw_desc = meta_description if result.status == "success" else ""
            else:
                desc_llm = self._get_agent_provider("meta_writer", writer_llm)
                raw_desc = desc_llm.generate_text(desc_prompt, temperature=0.3) or ""
            draft.meta_description = clean_meta_text(raw_desc, 500)

        draft.excerpt = self._extract_excerpt(content)

        # FAQ
        if include_faq is not False:
            self._generate_faq(draft)

        self._persist_revision(draft)
        set_article_status(article, ArticleStatus.DRAFT_READY)
        article.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        # AutoScoring : volontairement PAS ici. compute_global_score() a besoin de
        # eeat_checklist/readability_report/originality_report/seo_final_checklist, qui ne
        # sont calculés qu'aux étapes 16-21 de generate_full_article(). Voir _score_article().

    def _plan_images(self, keyword: str, outline: dict) -> dict:
        """Étape ImagePlan selon le mode choisi dans Paramètres → Services
        externes : photos Unsplash (plan par titre de section, dès
        maintenant), illustrations IA (générées après la rédaction, depuis
        le texte réel des sections, cf. _generate_illustrations) ou aucune."""
        from app.services.illustration_settings_service import resolve_config
        cfg = resolve_config(self.db, self.project_id)
        self.context["illustration_config"] = cfg
        if cfg.mode == "unsplash":
            result = build_image_plan_dict(keyword, outline, db=self.db, project_id=self.project_id)
            result.setdefault("image_plan", {})["mode"] = "unsplash"
        else:
            result = {
                "image_plan": {
                    "mode": cfg.mode,
                    "images": [],
                    "provider_configured": cfg.mode == "ai",
                    "limitations": [],
                },
                "image_sources": [],
            }
        self.context["image_plan"] = result.get("image_plan", {})
        self.context["image_sources"] = result.get("image_sources", [])

        if cfg.mode == "ai":
            self.tools_used.append("image_generation")
        elif cfg.mode == "unsplash":
            if result.get("image_plan", {}).get("provider_configured"):
                self.tools_used.append("unsplash")
            else:
                self.tools_not_configured.append("image_sourcing")
                self.limitations.append("Image sourcing provider not configured")
        return result

    def _generate_illustrations(self, article: Article, draft: _DraftArticle, outline: dict, content: str, cfg) -> list[dict]:
        """Mode « Générées par IA » : illustrations planifiées depuis le texte
        rédigé. Repli : photos Unsplash si une clé est configurée, sinon
        aucune image (jamais d'échec de la génération d'article)."""
        sources: list[dict] = []
        try:
            from app.services.seo.illustration_service import generate_illustrations
            language = ((self.project.locale if self.project else None) or "fr").split("-")[0]
            sources, errors = generate_illustrations(
                self.db, article, content, draft.title, draft.keyword, language, cfg,
            )
            for message in errors:
                self._error("ImageGeneration", message)
        except Exception as exc:
            self._error("ImageGeneration", str(exc))
        image_plan = self.context.setdefault("image_plan", {})
        image_plan["images"] = sources
        if sources:
            self._log(f"{len(sources)} illustration(s) générée(s)", step="ImageGeneration", article_id=article.id)
            self._save(article.id, "image_plan", image_plan)
            return sources

        if self.image_sourcing_adapter is not None and self.image_sourcing_adapter.configured:
            self._log("Aucune illustration générée — repli sur les photos Unsplash", level="warning", step="ImageGeneration")
            try:
                fallback = build_image_plan_dict(draft.keyword, outline, db=self.db, project_id=self.project_id)
                fallback.setdefault("image_plan", {})["mode"] = "unsplash_fallback"
                self.context["image_plan"] = fallback.get("image_plan", {})
                self._save(article.id, "image_plan", self.context["image_plan"])
                return fallback.get("image_sources", [])
            except Exception as exc:
                self._error("ImageGenerationFallback", str(exc))
        return []

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

    def _score_article(self, article: Article, draft: _DraftArticle) -> None:
        """Calcule et enregistre le score global (informatif uniquement).

        Doit être appelée seulement une fois que eeat_checklist, readability_report,
        originality_report et seo_final_checklist existent déjà (étapes 16-21 de
        generate_full_article) : compute_global_score() en a besoin pour évaluer
        SEO/EEAT/lisibilité/originalité."""
        final_score = None
        try:
            from app.services.seo.seo_review_service import run_and_store_seo_review
            run_and_store_seo_review(self.db, article)
            from app.services.scoring_service import compute_global_score
            scoring = compute_global_score(self.db, article.id, article=article)
            final_score = scoring.get("global_score")
            quality_report = self._get(article.id, "editorial_quality_report") or {}
            seo_final = self._get(article.id, "seo_final_checklist") or {}
            self.db.add(ArticleScore(
                article_id=article.id,
                revision_id=article.current_revision_id,
                global_score=final_score,
                seo_score=scoring.get("seo_contrib"),
                eeat_score=scoring.get("eeat_contrib"),
                readability_score=scoring.get("readability_contrib"),
                geo_score=scoring.get("geo_contrib"),
                quality_score=quality_report.get("score"),
                issues=_seo_final_checklist_to_issues(seo_final) + _editorial_quality_report_to_issues(quality_report),
            ))
            self.db.flush()
            self._step("AutoScoring")
        except Exception as exc:
            self._error("AutoScoring", str(exc))

        # Le score global reste un signal informatif pour l'éditeur : il ne
        # déclenche plus aucune réécriture automatique. L'ancienne boucle
        # d'auto-amélioration réécrivait l'article jusqu'à 6 fois pour viser un
        # score heuristique (statistiques "sourcées", liens forcés, marqueurs
        # "humains" canoniques) et dégradait le fond au profit de signaux de surface.
        self._raise_if_cancelled(article)

        set_article_status(article, ArticleStatus.DRAFT_READY)
        article.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        try:
            from app.services.notification_service import create_notification
            create_notification(
                db=self.db,
                project_id=article.project_id,
                title="Article prêt à valider",
                message=f'"{draft.title}" a été rédigé. Score indicatif : {final_score if final_score is not None else "—"}.',
                level="success",
                type="article_ready",
                link=f"/projects/{article.project_id}/production?tab=validate",
            )
        except Exception:
            pass

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
                "estimated_cost_eur": float(est) if est is not None else None,
                "actual_cost_eur": float(act) if act is not None else None,
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
            self.serp_adapter, trends_adapter, self.image_sourcing_adapter, language_adapter,
            scrapling_adapter, content_extraction_adapter, orig_adapter, readability_adapter, google_watch_adapter,
        ):
            try:
                adapters_status[adapter.provider_name] = adapter.get_status()
            except Exception:
                adapters_status[adapter.provider_name] = {"error": "status_unavailable"}

        cost_data = self._get_article_cost_data(article.id)

        try:
            error_analysis = analyze_generation_errors(self.errors, self.steps_completed)
            self._save(article.id, "error_analysis", error_analysis)
        except Exception as exc:
            error_analysis = None
            self._error("ErrorManager", str(exc))

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
                reading_time_minutes=draft.reading_time_minutes,
                steps_completed=self.steps_completed,
                errors=self.errors,
                limitations=self.limitations,
                final_status=article.status_reason_id,
                error_analysis=error_analysis,
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
    progress_cb: Callable[[str, int], None] | None = None,
) -> Article:
    orchestrator = SEOGenerationOrchestrator(
        db, project_id, llm, search, agent_router=agent_router, progress_cb=progress_cb,
    )
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
