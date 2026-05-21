from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExternalToolStatus:
    provider_name: str = ""
    enabled: bool = False
    configured: bool = False
    requires_api_key: bool = False
    last_error: str | None = None
    real_data_available: bool = False
    fallback_mode: str = "not_configured"
    trust_level: str = "none"


@dataclass
class ProjectContext:
    project_id: str = ""
    site_url: str = ""
    project_name: str = ""
    categories: list[dict] = field(default_factory=list)
    active_categories: list[dict] = field(default_factory=list)
    published_articles_count: int = 0
    draft_articles_count: int = 0
    recent_topics: list[str] = field(default_factory=list)
    known_keywords: list[str] = field(default_factory=list)
    editorial_notes: str | None = None
    target_audience: str | None = None
    pipeline_settings: dict | None = None
    limitations: list[str] = field(default_factory=list)


@dataclass
class CategoryStrategy:
    chosen_category_id: str | None = None
    chosen_category_name: str = ""
    reason: str = ""
    priority: float = 0.0
    expected_frequency: int = 0
    articles_published_this_month: int = 0
    pending_drafts: int = 0
    saturation_risk: str = "low"
    underfed: bool = False
    saturated: bool = False
    limitations: list[str] = field(default_factory=list)


@dataclass
class IdeaDiscoveryResult:
    title: str = ""
    category_id: str | None = None
    main_keyword: str = ""
    secondary_keywords: list[str] = field(default_factory=list)
    detected_intent: str = ""
    expected_answer: str = ""
    opportunity_score: float = 0.0
    source: str = ""
    real_research_used: bool = False
    confidence_score: float = 0.0
    limitations: list[str] = field(default_factory=list)


@dataclass
class IntentAnalysis:
    explicit_intent: str = ""
    implicit_intent: str = ""
    reader_real_question: str = ""
    expected_answer: str = ""
    sub_questions: list[str] = field(default_factory=list)
    what_to_avoid: list[str] = field(default_factory=list)
    risk_of_wrong_angle: str = ""
    recommended_angle: str = ""
    first_block_goal: str = ""
    article_type: str = "evergreen_information"


@dataclass
class ResearchBrief:
    research_status: str = "not_available"
    sources_consulted: list[dict] = field(default_factory=list)
    competitor_angles: list[str] = field(default_factory=list)
    common_answers: list[str] = field(default_factory=list)
    missing_points: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    field_signals: list[str] = field(default_factory=list)
    practical_examples: list[str] = field(default_factory=list)
    facts_to_include: list[str] = field(default_factory=list)
    risks_or_uncertainties: list[str] = field(default_factory=list)
    source_reliability_notes: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class KeywordBrief:
    main_keyword: str = ""
    secondary_keywords: list[str] = field(default_factory=list)
    long_tail_variants: list[str] = field(default_factory=list)
    related_questions: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    usage_strategy: str = ""
    keyword_risk_notes: list[str] = field(default_factory=list)


@dataclass
class CannibalizationCheck:
    similar_articles: list[dict] = field(default_factory=list)
    similar_ideas: list[dict] = field(default_factory=list)
    similar_keywords: list[str] = field(default_factory=list)
    risk_level: str = "none"
    recommendation: str = "create_new"


@dataclass
class EditorialAngle:
    editorial_promise: str = ""
    main_angle: str = ""
    reader_benefit: str = ""
    differentiation: str = ""
    tone: str = ""
    eeat_opportunities: list[str] = field(default_factory=list)


@dataclass
class ArticleOutline:
    h1: str = ""
    intro_goal: str = ""
    sections: list[dict] = field(default_factory=list)
    first_block_goal: str = ""
    conclusion_title: str = ""
    faq_planned: bool = False
    callouts_planned: bool = False


@dataclass
class ImagePlan:
    provider_configured: bool = False
    images: list[dict] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class CalloutPlan:
    callouts: list[dict] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class FAQPlan:
    faq: list[dict] = field(default_factory=list)
    faq_generated: bool = False
    faq_reason: str = ""


@dataclass
class InternalLinkPlan:
    links: list[dict] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class ExternalLinkPlan:
    links: list[dict] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class LanguageQualityReport:
    tool_used: str = "heuristic"
    external_tool_used: bool = False
    issues: list[dict] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    auto_fixes_applied: list[str] = field(default_factory=list)
    manual_review_needed: bool = False


@dataclass
class OriginalityReport:
    method: str = "heuristic"
    real_plagiarism_tool_used: bool = False
    compared_sources: list[dict] = field(default_factory=list)
    suspicious_passages: list[dict] = field(default_factory=list)
    risk_level: str = "low"
    heuristic_score: float = 0.0
    manual_review_needed: bool = False


@dataclass
class HumanizationReport:
    ai_phrases_detected: list[str] = field(default_factory=list)
    repeated_patterns: list[str] = field(default_factory=list)
    changes_suggested: list[str] = field(default_factory=list)
    auto_fixes_applied: list[str] = field(default_factory=list)
    manual_review_needed: bool = False


@dataclass
class EEATChecklist:
    checks: list[dict] = field(default_factory=list)
    score: float = 0.0
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    manual_review_needed: bool = False


@dataclass
class EditorialQualityReport:
    score: float = 0.0
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    auto_fixes_applied: list[str] = field(default_factory=list)
    manual_review_needed: bool = False


@dataclass
class SEOFinalChecklist:
    checks: list[dict] = field(default_factory=list)
    score: float = 0.0
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    manual_review_needed: bool = False


@dataclass
class SEOReview:
    score_global: float = 0.0
    seo_score: float = 0.0
    eeat_score: float = 0.0
    readability_score: float = 0.0
    editorial_quality_score: float = 0.0
    originality_score: float = 0.0
    issues: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    manual_review_needed: bool = True


@dataclass
class GenerationReport:
    provider: str = ""
    model: str = ""
    title_requested: str = ""
    title_final: str = ""
    title_modified: bool = False
    category_id: str | None = None
    category_name: str = ""
    main_keyword: str = ""
    secondary_keywords: list[str] = field(default_factory=list)
    detected_intent: str = ""
    expected_answer: str = ""
    article_type: str = ""
    outline_used: bool = False
    faq_generated: bool = False
    callouts_proposed: int = 0
    images_proposed: int = 0
    internal_links_proposed: int = 0
    external_links_proposed: int = 0
    research_status: str = "not_available"
    sources_used: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    tools_not_configured: list[str] = field(default_factory=list)
    adapters_status: dict = field(default_factory=dict)
    word_count: int = 0
    reading_time_minutes: int = 0
    steps_completed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    final_status: str = "draft_ready"


def asdict(obj: Any) -> dict:
    """Convert a dataclass to dict, recursively."""
    import dataclasses
    return dataclasses.asdict(obj)
