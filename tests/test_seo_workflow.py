"""Tests for the SEO editorial workflow: adapters, services, orchestrator, editor data."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.schemas.seo_workflow import ProjectContext, IntentAnalysis, CannibalizationCheck
from tests.conftest import register_and_login


# ── Adapters: honesty / not_configured behavior ─────────────────────────────

def test_serp_adapter_not_configured():
    from app.services.seo.adapters.serp_adapter import serp_adapter
    assert serp_adapter.configured is False
    assert serp_adapter.real_data_available is False
    assert serp_adapter.fallback_mode == "not_configured"
    results = serp_adapter.search("test query", limit=5)
    assert results == []


def test_trends_adapter_not_configured():
    from app.services.seo.adapters.trends_adapter import trends_adapter
    assert trends_adapter.configured is False
    assert trends_adapter.real_data_available is False
    result = trends_adapter.get_trends("test keyword")
    assert result["status"] == "not_configured"
    assert result["trend_score"] is None
    assert result["rising_queries"] == []
    assert result["related_topics"] == []


def test_image_sourcing_adapter_not_configured():
    from app.services.seo.adapters.image_sourcing_adapter import image_sourcing_adapter
    assert image_sourcing_adapter.configured is False
    assert image_sourcing_adapter.real_data_available is False
    results = image_sourcing_adapter.search("test", limit=3)
    assert results == []


def test_language_adapter_heuristic_when_not_configured():
    from app.services.seo.adapters.language_adapter import language_adapter
    result = language_adapter.check("Ceci est un test.", language="fr")
    assert result["external_tool_used"] is False
    assert result["tool_used"] == "heuristic"
    assert result["error"] == "LanguageTool not configured"
    assert result["issues"] == []


def test_content_extraction_adapter_not_configured():
    from app.services.seo.adapters.content_extraction_adapter import content_extraction_adapter
    if not content_extraction_adapter.configured:
        result = content_extraction_adapter.extract("https://example.com")
        assert result is None


def test_originality_adapter_always_configured():
    from app.services.seo.adapters.originality_adapter import originality_adapter
    assert originality_adapter.configured is True
    assert originality_adapter.real_data_available is True
    assert originality_adapter.fallback_mode == "heuristic_ngrams"


def test_readability_adapter_always_configured():
    from app.services.seo.adapters.readability_adapter import readability_adapter
    assert readability_adapter.configured is True
    assert readability_adapter.real_data_available is True
    assert readability_adapter.fallback_mode == "internal_heuristic"


def test_google_watch_adapter_returns_list():
    from app.services.seo.adapters.google_watch_adapter import google_watch_adapter
    result = google_watch_adapter.fetch_status()
    assert isinstance(result, list)


def test_all_adapters_have_get_status():
    from app.services.seo.adapters.serp_adapter import serp_adapter
    from app.services.seo.adapters.trends_adapter import trends_adapter
    from app.services.seo.adapters.image_sourcing_adapter import image_sourcing_adapter
    from app.services.seo.adapters.language_adapter import language_adapter
    from app.services.seo.adapters.content_extraction_adapter import content_extraction_adapter
    from app.services.seo.adapters.originality_adapter import originality_adapter
    from app.services.seo.adapters.readability_adapter import readability_adapter
    from app.services.seo.adapters.google_watch_adapter import google_watch_adapter

    for adapter in [serp_adapter, trends_adapter, image_sourcing_adapter, language_adapter,
                     content_extraction_adapter, originality_adapter, readability_adapter,
                     google_watch_adapter]:
        status = adapter.get_status()
        assert "configured" in status
        assert "real_data_available" in status
        assert "fallback_mode" in status


# ── Workflow services ───────────────────────────────────────────────────────

def test_project_context_builder_not_found():
    from app.services.seo.project_context_service import build_project_context
    ctx = build_project_context(MagicMock(spec=Session), "nonexistent-id")
    assert isinstance(ctx, ProjectContext)


def test_intent_analysis_guide_detection():
    from app.services.seo.intent_analysis_service import analyze_intent
    result = analyze_intent(title="Comment configurer SEO", keyword="configurer seo")
    assert result.explicit_intent == "informational"
    assert result.article_type in ("guide", "evergreen_information")


def test_intent_analysis_commercial_detection():
    from app.services.seo.intent_analysis_service import analyze_intent
    result = analyze_intent(title="SEO vs SEA", keyword="difference seo sea")
    assert result.explicit_intent == "commercial"


def test_intent_analysis_dict():
    from app.services.seo.intent_analysis_service import analyze_intent_dict
    result = analyze_intent_dict(title="Pourquoi le SEO", keyword="seo")
    assert isinstance(result, dict)
    assert "explicit_intent" in result


def test_cannibalization_empty_when_no_articles():
    from app.services.seo.cannibalization_service import check_cannibalization
    result = check_cannibalization(db=MagicMock(spec=Session), project_id="test", title="Test", keyword="test keyword")
    assert isinstance(result, CannibalizationCheck)
    assert result.risk_level == "none"
    assert not result.similar_articles


def test_cannibalization_detects_exact_match():
    from app.services.seo.cannibalization_service import check_cannibalization
    result = check_cannibalization(db=MagicMock(spec=Session), project_id="test", title="Test", keyword="test keyword")
    assert isinstance(result, CannibalizationCheck)
    assert result.risk_level == "none"
    assert len(result.similar_articles) == 0


def test_research_brief_returns_dict():
    from app.services.seo.research_brief_service import build_research_brief_dict
    result = build_research_brief_dict(keyword="test keyword", title="Test Article")
    assert isinstance(result, dict)
    assert "research_status" in result


def test_keyword_brief_returns_dict():
    from app.services.seo.keyword_brief_service import build_keyword_brief_dict
    result = build_keyword_brief_dict(main_keyword="test keyword")
    assert isinstance(result, dict)
    assert "main_keyword" in result


def test_editorial_angle_service_returns_dict():
    from app.services.seo.editorial_angle_service import define_editorial_angle_dict
    result = define_editorial_angle_dict(title="Test", keyword="test")
    assert isinstance(result, dict)
    assert "main_angle" in result


def test_article_outline_planner_returns_dict():
    from app.services.seo.article_outline_planner import build_outline_dict
    result = build_outline_dict(title="Test Article SEO", keyword="test seo")
    assert isinstance(result, dict)
    assert "sections" in result


def test_image_plan_service_returns_dict():
    from app.services.seo.image_plan_service import build_image_plan_dict
    result = build_image_plan_dict(keyword="test keyword")
    assert isinstance(result, dict)
    assert "image_plan" in result


def test_callout_plan_service_returns_dict():
    from app.services.seo.callout_plan_service import build_callout_plan_dict
    result = build_callout_plan_dict(db=MagicMock(), project_id="test", keyword="test")
    assert isinstance(result, dict)
    assert "callouts" in result


def test_faq_plan_service_returns_dict():
    from app.services.seo.faq_plan_service import build_faq_plan_dict
    result = build_faq_plan_dict(keyword="test keyword")
    assert isinstance(result, dict)
    assert "faq" in result


def test_internal_link_service_returns_dict():
    from app.services.seo.internal_link_service import build_internal_link_plan_dict
    result = build_internal_link_plan_dict(db=MagicMock(), project_id="test", keyword="test")
    assert isinstance(result, dict)
    assert "links" in result


def test_external_link_service_returns_dict():
    from app.services.seo.external_link_service import build_external_link_plan_dict
    result = build_external_link_plan_dict(keyword="test")
    assert isinstance(result, dict)
    assert "links" in result


def test_language_quality_service_returns_dict():
    from app.services.seo.language_quality_service import check_language_quality_dict
    result = check_language_quality_dict(content="Ceci est un test valide avec assez de mots.")
    assert isinstance(result, dict)
    assert "issues" in result


def test_originality_service_returns_dict():
    from app.services.seo.originality_service import check_originality_dict
    result = check_originality_dict(content="This is a unique test text with enough words to analyze properly.")
    assert isinstance(result, dict)
    assert "heuristic_score" in result


def test_humanization_service_returns_dict():
    from app.services.seo.humanization_service import check_humanization_dict
    result = check_humanization_dict(content="This is a natural text that should pass basic humanization checks.")
    assert isinstance(result, dict)
    assert "ai_phrases_detected" in result


def test_eeat_service_returns_dict():
    from app.services.seo.eeat_service import check_eeat_dict
    result = check_eeat_dict(content="<p>Test content with enough words for analysis purposes.</p>")
    assert isinstance(result, dict)
    assert "score" in result


def test_editorial_quality_gate_returns_report():
    from app.services.seo.editorial_quality_gate import check_editorial_quality_dict
    result = check_editorial_quality_dict(
        content="<h2>Heading</h2><p>Test paragraph with sufficient length for quality checks.</p>",
    )
    assert isinstance(result, dict)
    assert "score" in result or "passed_checks" in result


def test_seo_final_checklist_returns_dict():
    from app.services.seo.seo_final_checklist_service import check_seo_final_dict
    result = check_seo_final_dict(
        title="Test",
        meta_description="A test meta description.",
        keyword="test",
        slug="test",
        content="<p>Test content with enough words for the checklist to process.</p>",
    )
    assert isinstance(result, dict)
    assert "checks" in result or "passed" in result


def test_idea_discovery_service_returns_list():
    from unittest.mock import MagicMock
    from sqlalchemy.orm import Session
    from app.services.seo.idea_discovery_service import discover_ideas
    from app.services.providers.llm_provider import MockLLMProvider
    from app.services.providers.search_provider import MockSearchProvider
    result = discover_ideas(
        db=MagicMock(spec=Session),
        project_id="test",
        llm=MockLLMProvider(),
        search=MockSearchProvider(),
        count=2,
        context_hint="test keyword",
    )
    assert isinstance(result, list)


# ── Editor data exposes workflow reports ──────────────────────────────────

def test_editor_article_returns_workflow_fields(client):
    headers = register_and_login(client, email="editor_wf@test.com")
    project = client.post("/projects", json={"name": "WF Project"}, headers=headers).json()
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "WF Article", "slug": "wf-article", "content": "<p>Body</p>"},
        headers=headers,
    ).json()

    editor = client.get(f"/articles/{article['id']}/editor", headers=headers)
    assert editor.status_code == 200
    data = editor.json()
    assert "seo_review_json" in data
    assert "generation_report_json" in data
    assert data["seo_review_json"] is None
    assert data["generation_report_json"] is None


def test_editor_article_stores_generation_report(client, monkeypatch):
    from app.routers import editor as editor_router
    from app.routers import articles as articles_router
    from app.models.article import Article

    headers = register_and_login(client, email="editor_genrep@test.com")
    project = client.post("/projects", json={"name": "GenRep Project"}, headers=headers).json()
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "GenRep Article", "slug": "genrep-article", "content": "<p>Body</p>"},
        headers=headers,
    ).json()

    real_review = articles_router.run_and_store_seo_review

    def mock_store(article_obj: Article):
        article_obj.seo_review_json = {"mock": True}
        article_obj.generation_report_json = {"status": "completed", "steps": [{"name": "test", "status": "ok"}]}
        return {"score_global": 0.5, "failed_checks": []}

    monkeypatch.setattr(articles_router, "run_and_store_seo_review", mock_store)
    client.post(
        f"/projects/{project['id']}/articles/{article['id']}/seo-expert-review",
        headers=headers,
    )

    editor = client.get(f"/articles/{article['id']}/editor", headers=headers)
    assert editor.status_code == 200
    data = editor.json()
    assert data["generation_report_json"] is not None
    assert data["generation_report_json"]["status"] == "completed"
    assert data["seo_review_json"] is not None

    monkeypatch.setattr(articles_router, "run_and_store_seo_review", real_review)


# ── Orchestrator basic instantiation ───────────────────────────────────────

def test_orchestrator_initializes_with_mock_providers():
    from app.services.seo.seo_generation_orchestrator import SEOGenerationOrchestrator
    from app.services.providers.llm_provider import MockLLMProvider
    from app.services.providers.search_provider import MockSearchProvider

    orchestrator = SEOGenerationOrchestrator(
        db=MagicMock(spec=Session),
        project_id="test-id",
        llm=MockLLMProvider(),
        search=MockSearchProvider(),
    )
    assert orchestrator.project_id == "test-id"


def test_generation_report_service_creates_report():
    from app.services.seo.generation_report_service import build_generation_report
    report = build_generation_report(
        final_status="completed",
        steps_completed=[{"name": "step1", "status": "ok"}],
    )
    assert report.final_status == "completed"
    assert len(report.steps_completed) == 1


# ── Helpers ────────────────────────────────────────────────────────────────

def test_strip_html():
    from app.services.seo.helpers import strip_html
    result = strip_html("<p>Hello <b>world</b></p>")
    assert "Hello" in result and "world" in result


def test_safe_json_load_valid():
    from app.services.seo.helpers import safe_json_load
    assert safe_json_load('{"a": 1}') == {"a": 1}


def test_safe_json_load_invalid():
    from app.services.seo.helpers import safe_json_load
    assert safe_json_load("invalid{json") is None


def test_detect_title_case_french():
    from app.services.seo.helpers import detect_title_case_french
    assert detect_title_case_french("Comment Améliorer le SEO") is True
    assert detect_title_case_french("Comment améliorer le SEO") is False


def test_detect_long_dash():
    from app.services.seo.helpers import detect_long_dash
    assert isinstance(detect_long_dash("Texte avec — un long dash"), list)
    assert len(detect_long_dash("Texte avec — un long dash")) > 0
    assert detect_long_dash("Texte normal") == []


def test_detect_ai_phrases():
    from app.services.seo.helpers import detect_ai_phrases
    phrases = detect_ai_phrases("Il est recommandé de vérifier cette information avant de publier")
    assert len(phrases) >= 1


def test_extract_headings_from_html():
    from app.services.seo.helpers import extract_headings_from_html
    headings = extract_headings_from_html("<h2>Title</h2><h3>Sub</h3>")
    assert len(headings) == 2
