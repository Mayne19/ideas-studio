"""Rédaction section par section : tests hors ligne avec un faux provider."""
import re

from app.services.seo.article_outline_planner import strip_heading_enumeration
from app.services.seo.external_link_service import is_junk_url
from app.services.seo.research_brief_service import extract_facts_from_snippets
from app.services.seo.section_writer import (
    SectionWriter,
    extract_h2_texts,
    group_outline_sections,
    lost_h2s,
)

OUTLINE = {
    "sections": [
        {"heading": "Webflow ou WordPress : le verdict", "level": 2, "purpose": "Répondre"},
        {"heading": "Les prix réels", "level": 2, "key_points": ["abonnement", "hébergement"]},
        {"heading": "Plans Webflow", "level": 3},
        {"heading": "Coût de WordPress", "level": 3},
        {"heading": "La prise en main", "level": 2},
        {"heading": "Le SEO", "level": 2},
        {"heading": "Les limites de chaque outil", "level": 2},
    ]
}


class FakeProvider:
    """Répond selon l'unité demandée ; peut renvoyer du vide pour une section."""

    def __init__(self, empty_sections: set[str] | None = None):
        self.calls: list[str] = []
        self.empty_sections = empty_sections or set()

    def __call__(self, prompt: str, step: str, temperature: float) -> str:
        self.calls.append(step)
        if step.startswith("WritingPass_Intro"):
            return ("<p>Webflow convient aux sites vitrines soignés, WordPress aux sites qui grossissent. "
                    "Le bon choix dépend surtout du temps que vous voulez passer sur la maintenance "
                    "et du budget mensuel que vous acceptez.</p>")
        if step.startswith("WritingPass_Closing"):
            return ("<p>Si vous démarrez seul avec un site vitrine, prenez Webflow. Si vous prévoyez un blog "
                    "important ou une boutique, partez sur WordPress.</p>")
        match = re.search(r"Rédige uniquement la section \d+ sur \d+ : « (.+?) »", prompt)
        heading = match.group(1)
        if heading in self.empty_sections:
            return ""
        body = " ".join(["Webflow et WordPress se distinguent ici sur un point concret."] * 8)
        return f"<h2>{heading}</h2>\n<p>{body}</p>"


def _writer(provider, fmt="comparison"):
    return SectionWriter(provider, "=== BRIEF ===", group_outline_sections(OUTLINE), fmt=fmt,
                         words_per_section=150)


def test_h3_entries_are_grouped_under_their_h2():
    sections = group_outline_sections(OUTLINE)
    assert [s.heading for s in sections] == [
        "Webflow ou WordPress : le verdict", "Les prix réels", "La prise en main", "Le SEO",
        "Les limites de chaque outil",
    ]
    assert sections[1].subheadings == ["Plans Webflow", "Coût de WordPress"]


def test_every_outline_section_is_written_in_its_own_call():
    provider = FakeProvider()
    writer = _writer(provider)
    content = writer.write_article()

    section_calls = [c for c in provider.calls if c.startswith("WritingPass_Section_")]
    assert len(section_calls) == 5
    assert provider.calls[0] == "WritingPass_Intro"
    assert provider.calls[-1] == "WritingPass_Closing"  # format comparaison
    assert extract_h2_texts(content) == [s.heading for s in writer.sections]
    assert content.startswith("<p>Webflow convient")
    assert writer.missing_sections(content) == []


def test_no_closing_call_for_explainer_format():
    provider = FakeProvider()
    _writer(provider, fmt="explainer").write_article()
    assert "WritingPass_Closing" not in provider.calls


def test_completeness_guard_regenerates_only_the_missing_section():
    provider = FakeProvider(empty_sections={"Le SEO"})
    writer = _writer(provider)
    content = writer.write_article()
    assert "Le SEO" not in extract_h2_texts(content)
    # Deux tentatives pour la section vide pendant la rédaction.
    assert provider.calls.count("WritingPass_Section_4") == 1
    assert provider.calls.count("WritingPass_Section_4#2") == 1

    provider.empty_sections.clear()
    provider.calls.clear()
    content, regenerated, still_missing = writer.ensure_complete(content)

    assert regenerated == ["Le SEO"] and still_missing == []
    assert provider.calls == ["WritingPass_Section_4"]
    headings = extract_h2_texts(content)
    assert headings == [s.heading for s in writer.sections]  # réinsérée à sa place
    assert content.rstrip().endswith("WordPress.</p>")  # la fin reste en dernier


def test_truncated_section_is_retried():
    calls = []

    def provider(prompt, step, temperature):
        calls.append(step)
        if step.startswith("WritingPass_Section_1") and len(calls) == 2:
            return "<h2>X</h2><p>Une phrase complète ici pour commencer. Puis une phrase coupée au mil"
        return FakeProvider()(prompt, step, temperature)

    writer = _writer(provider, fmt="explainer")
    writer.write_article()
    assert "WritingPass_Section_1#2" in calls


def test_lost_h2s_detects_dropped_sections():
    before = "<h2>Les prix réels</h2><p>a</p><h2>Le SEO</h2><p>b</p>"
    after = "<h2>Les prix réels</h2><p>a</p>"
    assert lost_h2s(before, after) == ["Le SEO"]
    assert lost_h2s(before, before.replace("Le SEO", "Le SEO :")) == []


def test_heading_enumeration_stripped_outside_list_formats():
    assert strip_heading_enumeration("1. Webflow ou WordPress : le verdict", "comparison") == \
        "Webflow ou WordPress : le verdict"
    assert strip_heading_enumeration("Étape 2 : publier", "explainer") == "Publier"
    assert strip_heading_enumeration("2. Publier", "how_to") == "2. Publier"
    assert strip_heading_enumeration("3 outils gratuits", "explainer") == "3 outils gratuits"


def test_junk_urls_and_snippet_facts():
    assert is_junk_url("https://www.google.com/preferences/source?q=webflow")
    assert is_junk_url("https://bit.ly/x")
    assert not is_junk_url("https://webflow.com/pricing")
    assert not is_junk_url("https://w3techs.com/technologies/details/cm-wordpress")
    facts = extract_facts_from_snippets([
        {"url": "https://w3techs.com/x", "snippet": "WordPress is used by 43.5% of all the websites. Read more."},
    ])
    assert facts == ["WordPress is used by 43.5% of all the websites (source : w3techs.com)"]
    assert not any(f.startswith("http") for f in facts)


def test_clean_unit_html_converts_markdown_paragraphs_lists_and_headings():
    from app.services.seo.section_writer import clean_unit_html, looks_truncated

    raw = (
        "Un site vitrine coûte entre 1 500 et 5 000 €.\n\n"
        "### Ce qui fait varier le prix\n\n"
        "- le **nombre de pages** ;\n- les fonctionnalités.\n\n"
        "Le budget dépend surtout de vos contenus."
    )
    html = clean_unit_html(raw)
    assert "<p>Un site vitrine" in html
    assert "<h3>Ce qui fait varier le prix</h3>" in html
    assert "<li>le <strong>nombre de pages</strong> ;</li>" in html
    assert not looks_truncated(html)


def test_comparison_table_requested_in_one_section_only():
    from app.services.seo.section_writer import component_section_index

    sections = group_outline_sections(OUTLINE)
    assert component_section_index(sections, "comparison") == 0
    assert component_section_index(sections, "guide") is None
    writer = SectionWriter(FakeProvider(), "=== BRIEF ===", sections, fmt="comparison")
    prompts = [writer._section_prompt(i, "", "") for i in range(len(sections))]
    assert ["<table>" in p and "Obligatoire" in p for p in prompts].count(True) == 1


def test_strip_fact_markers_drops_emptied_inline_tags():
    from app.services.seo.section_writer import strip_fact_markers

    cleaned, markers = strip_fact_markers("<p>Les délais baissent <strong>[F3]</strong>. Fin <em> [F4] </em> :</p>")
    assert cleaned == "<p>Les délais baissent. Fin :</p>"
    assert [m["fact_id"] for m in markers] == ["F3", "F4"]


def test_price_guide_and_list_components():
    from app.services.seo.intent_analysis_service import analyze_intent
    from app.services.seo.section_writer import component_section_index

    assert analyze_intent("combien coûte un site vitrine", "combien coûte un site vitrine").recommended_format == "price_guide"
    assert analyze_intent("webflow ou wordpress", "webflow ou wordpress").recommended_format != "price_guide"
    sections = group_outline_sections(OUTLINE)
    assert component_section_index(sections, "price_guide") == 1  # « Les prix réels »
    assert component_section_index(sections, "list") is None
    writer = SectionWriter(FakeProvider(), "=== BRIEF ===", sections, fmt="list")
    assert all("pour qui il convient" in writer._section_prompt(i, "", "") for i in range(len(sections)))


def test_definition_queries_are_explainers():
    from app.services.seo.intent_analysis_service import analyze_intent

    assert analyze_intent("qu'est-ce qu'un cms headless", "qu'est-ce qu'un cms headless").recommended_format == "explainer"
