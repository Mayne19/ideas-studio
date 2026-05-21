from __future__ import annotations

from app.schemas.seo_workflow import GenerationReport, asdict


def build_generation_report(
    provider: str = "",
    model: str = "",
    title_requested: str = "",
    title_final: str = "",
    category_id: str | None = None,
    category_name: str = "",
    main_keyword: str = "",
    secondary_keywords: list[str] | None = None,
    detected_intent: str = "",
    expected_answer: str = "",
    article_type: str = "",
    outline_used: bool = False,
    faq_generated: bool = False,
    callouts_proposed: int = 0,
    images_proposed: int = 0,
    internal_links_proposed: int = 0,
    external_links_proposed: int = 0,
    research_status: str = "not_available",
    sources_used: list[str] | None = None,
    tools_used: list[str] | None = None,
    tools_not_configured: list[str] | None = None,
    word_count: int = 0,
    reading_time_minutes: int = 0,
    steps_completed: list[str] | None = None,
    errors: list[str] | None = None,
    limitations: list[str] | None = None,
    final_status: str = "draft_ready",
) -> GenerationReport:
    report = GenerationReport(
        provider=provider,
        model=model,
        title_requested=title_requested,
        title_final=title_final,
        title_modified=(title_requested != title_final) if title_requested else False,
        category_id=category_id,
        category_name=category_name,
        main_keyword=main_keyword,
        secondary_keywords=secondary_keywords or [],
        detected_intent=detected_intent,
        expected_answer=expected_answer,
        article_type=article_type,
        outline_used=outline_used,
        faq_generated=faq_generated,
        callouts_proposed=callouts_proposed,
        images_proposed=images_proposed,
        internal_links_proposed=internal_links_proposed,
        external_links_proposed=external_links_proposed,
        research_status=research_status,
        sources_used=sources_used or [],
        tools_used=tools_used or [],
        tools_not_configured=tools_not_configured or [],
        word_count=word_count,
        reading_time_minutes=reading_time_minutes,
        steps_completed=steps_completed or [],
        errors=errors or [],
        limitations=limitations or [],
        final_status=final_status,
    )
    return report


def build_generation_report_dict(**kwargs) -> dict:
    return asdict(build_generation_report(**kwargs))
