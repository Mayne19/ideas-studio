from types import SimpleNamespace

from app.routers import articles as articles_router
from app.services.seo.google_watch_service import (
    build_action_recommendations,
    classify_update_impact,
    list_google_watch_sources,
    normalize_update_item,
)
from app.services.seo.seo_knowledge_pack_service import (
    get_article_generation_rules,
    get_article_review_rules,
    get_content_quality_checklist,
    get_eeat_checklist,
    get_google_seo_basics,
    get_humanization_rules,
)
from app.services.seo.seo_review_service import review_article_with_knowledge_pack
from tests.conftest import register_and_login


def test_knowledge_pack_returns_rules():
    assert get_google_seo_basics()["rules"]
    assert get_eeat_checklist()["dimensions"]
    assert get_content_quality_checklist()["checks"]
    assert get_humanization_rules()["anti_patterns"]
    assert get_article_generation_rules()["workflow"]
    assert get_article_review_rules()["checks"]


def test_google_watch_sources_exist():
    sources = list_google_watch_sources()
    assert len(sources) >= 4
    assert any(source["key"] == "search_status_dashboard" for source in sources)
    assert all(source["official"] for source in sources)


def test_normalize_update_item_builds_fingerprint():
    item = normalize_update_item(
        {
            "source_key": "search_status_dashboard",
            "title": "Ranking issue detected",
            "summary": "A ranking issue affects some sites.",
            "url": "https://status.search.google.com/",
        }
    )
    assert item["fingerprint"]
    assert item["title"] == "Ranking issue detected"


def test_classify_update_impact():
    assert classify_update_impact({"title": "Google core update rolling out"}) == "important"
    assert classify_update_impact({"title": "Search serving outage"}) == "critical"
    assert classify_update_impact({"title": "Documentation update for starter guide"}) == "medium"


def test_build_action_recommendations():
    recommendations = build_action_recommendations({"title": "Google core update rolling out"}, "important")
    assert recommendations
    assert any("review" in recommendation.lower() for recommendation in recommendations)


def test_review_detects_missing_meta():
    article = SimpleNamespace(
        title="How to improve technical SEO",
        slug="improve-technical-seo",
        meta_description="",
        keyword="technical seo",
        author_name="Alex",
        faq_json=None,
        content="""
        <h2>How to improve technical SEO quickly</h2>
        <p>Start by fixing crawl issues, indexing blockers, and important page signals.</p>
        <h2>What to check first</h2>
        <p>Check robots, canonicals, sitemaps, and page speed. According to Google Search Central, crawlability matters.</p>
        <p>For example, broken canonicals can waste internal authority and indexing budget.</p>
        <p>This section is extended with enough words to avoid being flagged as too short. </p>
        """ + ("<p>Useful technical SEO advice with source support and practical examples.</p>" * 80),
    )
    review = review_article_with_knowledge_pack(article)
    assert "meta_description_present" in review["failed_checks"]


def test_review_detects_content_too_short():
    article = SimpleNamespace(
        title="SEO basics",
        slug="seo-basics",
        meta_description="A short meta description.",
        keyword="seo basics",
        author_name="Alex",
        faq_json=None,
        content="<h2>SEO basics explained</h2><p>Short content only.</p>",
    )
    review = review_article_with_knowledge_pack(article)
    assert "content_depth" in review["failed_checks"]


def test_review_detects_faq_with_one_question():
    article = SimpleNamespace(
        title="How to write an SEO brief",
        slug="write-seo-brief",
        meta_description="Learn how to write a clear SEO brief.",
        keyword="seo brief",
        author_name="Alex",
        faq_json=[{"question": "What is an SEO brief?", "answer": "A planning document."}],
        content=(
            "<h2>How to write an SEO brief</h2>"
            + "<p>According to a documented workflow, you should define intent, audience, sections, and proof requirements.</p>" * 90
        ),
    )
    review = review_article_with_knowledge_pack(article)
    assert "faq_count_valid" in review["failed_checks"]


def test_review_detects_isolated_h3():
    article = SimpleNamespace(
        title="How to build a content outline",
        slug="build-content-outline",
        meta_description="Build a better content outline.",
        keyword="content outline",
        author_name="Alex",
        faq_json=None,
        content=(
            "<h2>How to build a content outline</h2>"
            + "<p>This first section gives a direct answer and enough context for the reader.</p>" * 20
            + "<h2>Outline structure</h2>"
            + "<h3>Only subsection</h3>"
            + "<p>One isolated subsection should be detected here.</p>" * 70
        ),
    )
    review = review_article_with_knowledge_pack(article)
    assert "no_isolated_h3" in review["failed_checks"]


def test_seo_expert_review_endpoint_returns_and_saves_report(client):
    headers = register_and_login(client, email="seo_expert_review_endpoint@test.com")
    project = client.post("/projects", json={"name": "SEO Project"}, headers=headers).json()
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={
            "title": "How to improve technical SEO",
            "slug": "improve-technical-seo",
            "meta_description": "A practical guide to improving technical SEO.",
            "content": "<h2>How to improve technical SEO</h2>" + "<p>According to Google Search Central, fixing crawl and indexing basics matters.</p>" * 120,
        },
        headers=headers,
    ).json()

    response = client.post(f"/projects/{project['id']}/articles/{article['id']}/seo-expert-review", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "score_global" in data
    assert "issues" in data

    editor = client.get(f"/articles/{article['id']}/editor", headers=headers)
    assert editor.status_code == 200
    assert editor.json()["seo_review_json"] is not None
    assert "score_global" in editor.json()["seo_review_json"]


def test_editor_article_without_seo_review_json_is_safe(client):
    headers = register_and_login(client, email="seo_review_missing@test.com")
    project = client.post("/projects", json={"name": "SEO Project"}, headers=headers).json()
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Draft without review", "slug": "draft-without-review", "content": "<p>Draft body.</p>"},
        headers=headers,
    ).json()

    editor = client.get(f"/articles/{article['id']}/editor", headers=headers)
    assert editor.status_code == 200
    assert editor.json()["seo_review_json"] is None


def test_seo_expert_review_rejects_wrong_project_id(client):
    headers = register_and_login(client, email="seo_review_project_mismatch@test.com")
    project_a = client.post("/projects", json={"name": "Project A"}, headers=headers).json()
    project_b = client.post("/projects", json={"name": "Project B"}, headers=headers).json()
    article = client.post(
        f"/projects/{project_a['id']}/articles",
        json={"title": "Article A", "slug": "article-a", "content": "<p>Body</p>"},
        headers=headers,
    ).json()

    response = client.post(
        f"/projects/{project_b['id']}/articles/{article['id']}/seo-expert-review",
        headers=headers,
    )
    assert response.status_code == 404


def test_seo_expert_review_stores_error_report_when_runtime_fails(client, monkeypatch):
    headers = register_and_login(client, email="seo_review_runtime_error@test.com")
    project = client.post("/projects", json={"name": "SEO Project"}, headers=headers).json()
    article = client.post(
        f"/projects/{project['id']}/articles",
        json={"title": "Runtime Review", "slug": "runtime-review", "content": "<p>Body</p>"},
        headers=headers,
    ).json()

    def fail_review(_article):
        raise RuntimeError("boom")

    monkeypatch.setattr(articles_router, "run_and_store_seo_review", fail_review)

    response = client.post(f"/projects/{project['id']}/articles/{article['id']}/seo-expert-review", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "seo_expert_runtime" in data["failed_checks"]

    editor = client.get(f"/articles/{article['id']}/editor", headers=headers)
    assert editor.status_code == 200
    assert "seo_expert_runtime" in editor.json()["seo_review_json"]["failed_checks"]
