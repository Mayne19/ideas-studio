"""Contrats de données du laboratoire éditorial."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class PublishedArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: HttpUrl
    summary: str = ""


class SiteContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_name: str
    domain: str
    language: str = "fr"
    country: str = "FR"
    editorial_rules: list[str] = Field(default_factory=list)
    published_articles: list[PublishedArticle] = Field(default_factory=list)


class ArticleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keyword: str
    category: str = ""
    editor_instructions: list[str] = Field(default_factory=list)


class CompetitorPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl
    title: str
    content: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missing_topics: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)


class ReaderIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    real_question: str
    reader_level: str
    main_problem: str
    likely_trap: str
    concrete_gain: str


class FactRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    definition: str
    unit: str = ""
    source_url: HttpUrl
    source_title: str = ""
    source_kind: Literal["official", "institutional", "study", "specialist", "other"]
    verified: bool = False


class SectionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str
    promise: str
    reader_question: str
    facts_to_use: list[str] = Field(default_factory=list)
    examples_to_use: list[str] = Field(default_factory=list)
    h3_sections: list[str] = Field(default_factory=list)
    information_not_to_repeat: list[str] = Field(default_factory=list)


class FaqPlanItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    reason_not_in_article: str
    facts_to_use: list[str] = Field(default_factory=list)


class ArticlePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intro_purpose: str
    summary_callout: str
    sections: list[SectionPlan] = Field(min_length=1)
    conclusion_heading: str
    faq: list[FaqPlanItem] = Field(min_length=1)


class ArticleDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    meta_title: str
    meta_description: str
    slug: str
    content_html: str
    faq: list[dict[str, str]] = Field(default_factory=list)
    sources: list[dict[str, str]] = Field(default_factory=list)
    facts: list[dict[str, str]] = Field(default_factory=list)
    competitors: list[dict[str, object]] = Field(default_factory=list)
    self_review: dict[str, object] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    blocking: bool
    location: str = ""


class SimilarityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentence: str
    source_url: HttpUrl
    matched_text: str
    similarity: float = Field(ge=0, le=1)
    suggested_reformulation: str = ""


class GenerationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keyword: str
    searches: int = 0
    pages_read: int = 0
    blocking_issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    similarity_findings: list[SimilarityFinding] = Field(default_factory=list)
    correction_rounds: int = 0
    selected_version: int = 1


class GenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan: ArticlePlan
    draft: ArticleDraft
    report: GenerationReport
