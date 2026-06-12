from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class AgentCategory(str, Enum):
    research = "research"
    strategy = "strategy"
    creation = "creation"
    review = "review"


@dataclass
class AgentDef:
    agent_id: str
    name: str
    description: str
    category: AgentCategory
    requires_llm: bool = True
    requires_search: bool = False
    icon: str = "robot"
    # Which existing service function implements this agent (or None if not implemented)
    # This links to the heuristic/LLM call currently used
    implementation_ref: str | None = None


AGENTS: list[AgentDef] = [
    # ── Research ──────────────────────────────────────────────────────
    AgentDef(
        agent_id="keyword_researcher",
        name="Recherche de mots-clés",
        description="Analyse et suggère des mots-clés SEO pertinents",
        category=AgentCategory.research,
        requires_search=True,
        icon="search",
        implementation_ref="keyword_brief_service",
    ),
    AgentDef(
        agent_id="serp_analyzer",
        name="Analyse SERP",
        description="Analyse les pages de résultats des moteurs de recherche",
        category=AgentCategory.research,
        requires_search=True,
        icon="chart-bar",
        implementation_ref="serp_adapter",
    ),
    AgentDef(
        agent_id="trend_detector",
        name="Détection de tendances",
        description="Identifie les sujets émergents dans le secteur",
        category=AgentCategory.research,
        requires_search=True,
        icon="trending-up",
        implementation_ref="trends_adapter",
    ),
    AgentDef(
        agent_id="competitor_analyzer",
        name="Analyse concurrents",
        description="Examine le contenu des concurrents pour trouver des opportunités",
        category=AgentCategory.research,
        requires_search=True,
        icon="users",
        implementation_ref="research_brief_service",
    ),
    AgentDef(
        agent_id="fact_checker",
        name="Vérification des faits",
        description="Vérifie l'exactitude des affirmations et données dans l'article",
        category=AgentCategory.research,
        requires_search=True,
        icon="check-circle",
        implementation_ref=None,
    ),
    AgentDef(
        agent_id="researcher",
        name="Recherche approfondie",
        description="Effectue des recherches détaillées sur un sujet donné",
        category=AgentCategory.research,
        requires_search=False,
        icon="book-open",
        implementation_ref="content_extraction_adapter",
    ),
    # ── Strategy ──────────────────────────────────────────────────────
    AgentDef(
        agent_id="intent_analyzer",
        name="Analyse d'intention",
        description="Détermine l'intention de recherche derrière un mot-clé",
        category=AgentCategory.strategy,
        icon="target",
        implementation_ref="intent_analysis_service",
    ),
    AgentDef(
        agent_id="cannibalization_checker",
        name="Vérification cannibalisation",
        description="Détecte les risques de cannibalisation entre articles",
        category=AgentCategory.strategy,
        icon="alert-triangle",
        implementation_ref="cannibalization_service",
    ),
    AgentDef(
        agent_id="idea_generator",
        name="Génération d'idées",
        description="Propose des idées d'articles basées sur le contexte du projet",
        category=AgentCategory.strategy,
        icon="lightbulb",
        implementation_ref="idea_engine",
    ),
    AgentDef(
        agent_id="editorial_strategist",
        name="Stratégie éditoriale",
        description="Définit la stratégie éditoriale par catégorie",
        category=AgentCategory.strategy,
        icon="map",
        implementation_ref="category_strategy_service",
    ),
    AgentDef(
        agent_id="content_planner",
        name="Planification contenu",
        description="Planifie la structure et le format de l'article",
        category=AgentCategory.strategy,
        icon="file-text",
        implementation_ref="editorial_angle_service",
    ),
    AgentDef(
        agent_id="brief_writer",
        name="Rédaction de brief",
        description="Rédige le brief éditorial complet pour un article",
        category=AgentCategory.strategy,
        icon="clipboard",
        implementation_ref="project_context_service",
    ),
    # ── Creation ──────────────────────────────────────────────────────
    AgentDef(
        agent_id="content_writer",
        name="Rédacteur",
        description="Rédige le contenu de l'article en HTML/TipTap",
        category=AgentCategory.creation,
        icon="pen-tool",
        implementation_ref="writing_engine",
    ),
    AgentDef(
        agent_id="title_generator",
        name="Génération de titres",
        description="Génère des titres SEO optimisés",
        category=AgentCategory.creation,
        icon="type",
        implementation_ref="writing_engine",
    ),
    AgentDef(
        agent_id="meta_description_writer",
        name="Rédaction meta descriptions",
        description="Rédige des meta descriptions accrocheuses",
        category=AgentCategory.creation,
        icon="align-left",
        implementation_ref="writing_engine",
    ),
    AgentDef(
        agent_id="image_selector",
        name="Sélection d'images",
        description="Sélectionne des images pertinentes via Unsplash",
        category=AgentCategory.creation,
        icon="image",
        implementation_ref="image_sourcing_adapter",
    ),
    AgentDef(
        agent_id="internal_link_builder",
        name="Liens internes",
        description="Construit un plan de maillage interne pertinent",
        category=AgentCategory.creation,
        icon="link",
        implementation_ref="internal_link_service",
    ),
    AgentDef(
        agent_id="external_link_finder",
        name="Liens externes",
        description="Trouve des sources externes de qualité",
        category=AgentCategory.creation,
        requires_search=True,
        icon="external-link",
        implementation_ref="external_link_service",
    ),
    AgentDef(
        agent_id="faq_generator",
        name="Génération FAQ",
        description="Génère des FAQ structurées à partir du contenu",
        category=AgentCategory.creation,
        icon="help-circle",
        implementation_ref="faq_plan_service",
    ),
    AgentDef(
        agent_id="callout_planner",
        name="Plans callout",
        description="Planifie des encadrés callout dans l'article",
        category=AgentCategory.creation,
        icon="quote",
        implementation_ref="callout_plan_service",
    ),
    # ── Review ────────────────────────────────────────────────────────
    AgentDef(
        agent_id="editor_revisor",
        name="Révision éditoriale",
        description="Révise le contenu pour la qualité éditoriale",
        category=AgentCategory.review,
        icon="edit",
        implementation_ref=None,
    ),
    AgentDef(
        agent_id="quality_rater",
        name="Évaluation qualité",
        description="Évalue la qualité globale de l'article",
        category=AgentCategory.review,
        icon="star",
        implementation_ref="editorial_quality_gate",
    ),
    AgentDef(
        agent_id="seo_optimizer",
        name="Optimisation SEO",
        description="Optimise le contenu pour les moteurs de recherche",
        category=AgentCategory.review,
        icon="search",
        implementation_ref=None,
    ),
    AgentDef(
        agent_id="readability_analyzer",
        name="Analyse lisibilité",
        description="Analyse la lisibilité du contenu",
        category=AgentCategory.review,
        icon="book",
        implementation_ref="language_quality_service",
    ),
    AgentDef(
        agent_id="originality_checker",
        name="Vérification originalité",
        description="Vérifie l'originalité du contenu par rapport aux sources",
        category=AgentCategory.review,
        icon="copy",
        implementation_ref="originality_service",
    ),
    AgentDef(
        agent_id="eeat_checker",
        name="Vérification EEAT",
        description="Vérifie la conformité EEAT (Experience, Expertise, Authoritativeness, Trust)",
        category=AgentCategory.review,
        icon="shield",
        implementation_ref="eeat_service",
    ),
    AgentDef(
        agent_id="humanization_engine",
        name="Humanisation",
        description="Vérifie et améliore le ton humain du contenu",
        category=AgentCategory.review,
        icon="smile",
        implementation_ref="humanization_service",
    ),
]

AGENTS_BY_ID = {a.agent_id: a for a in AGENTS}
AGENTS_BY_CATEGORY: dict[str, list[AgentDef]] = {}
for a in AGENTS:
    AGENTS_BY_CATEGORY.setdefault(a.category.value, []).append(a)


def get_agent(agent_id: str) -> AgentDef | None:
    return AGENTS_BY_ID.get(agent_id)


def list_agents(category: str | None = None) -> list[AgentDef]:
    if category:
        return AGENTS_BY_CATEGORY.get(category, [])
    return list(AGENTS)


def serialize_agent(a: AgentDef) -> dict:
    return {
        "agent_id": a.agent_id,
        "name": a.name,
        "description": a.description,
        "category": a.category.value,
        "requires_llm": a.requires_llm,
        "requires_search": a.requires_search,
        "icon": a.icon,
        "has_implementation": a.implementation_ref is not None,
    }
