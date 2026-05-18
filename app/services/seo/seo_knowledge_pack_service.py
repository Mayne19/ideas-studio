from __future__ import annotations

from copy import deepcopy


_GOOGLE_SEO_BASICS = {
    "source_priority": "official_google",
    "sources": [
        {
            "name": "Google Search Central",
            "url": "https://developers.google.com/search/",
            "role": "official documentation baseline",
        },
        {
            "name": "Google SEO Starter Guide",
            "url": "https://developers.google.com/search/docs/fundamentals/seo-starter-guide",
            "role": "starter rules and best practices",
        },
        {
            "name": "Google Search Status Dashboard",
            "url": "https://status.search.google.com/",
            "role": "status and incident monitoring",
        },
    ],
    "rules": [
        "Create people-first, useful content before optimizing for ranking surfaces.",
        "Make pages crawlable and understandable with clear HTML structure.",
        "Use descriptive titles, meta descriptions, and stable URLs.",
        "Avoid deceptive or manipulative tactics such as keyword stuffing.",
        "Keep important content visible without requiring aggressive client-side execution.",
        "Use internal linking and clear hierarchy to help users and search engines navigate.",
        "Support factual or sensitive claims with trustworthy sources and transparent authorship.",
        "Treat freshness as topic-dependent: update when the topic or facts actually change.",
    ],
}

_EEAT_CHECKLIST = {
    "source": "internalized_from_google_and_seo_geo_audit",
    "dimensions": [
        {
            "name": "experience",
            "checks": [
                "Includes practical examples, process details, or real-world observations when relevant.",
                "Avoids fake first-hand claims or invented personal experience.",
                "Shows concrete reader value beyond generic summaries.",
            ],
        },
        {
            "name": "expertise",
            "checks": [
                "Explains the topic accurately and at an appropriate depth.",
                "Uses precise terminology without unnecessary jargon.",
                "Avoids vague factual claims without support.",
            ],
        },
        {
            "name": "authoritativeness",
            "checks": [
                "References reliable sources for factual or sensitive topics.",
                "Keeps the angle aligned with the site's editorial positioning.",
                "Shows why this article is a credible answer for the target reader.",
            ],
        },
        {
            "name": "trustworthiness",
            "checks": [
                "No misleading claims, invented numbers, or fake citations.",
                "Keeps limitations and nuance where certainty would be misleading.",
                "Uses a clear title, metadata, and transparent structure.",
            ],
        },
    ],
}

_CONTENT_QUALITY_CHECKLIST = {
    "source": "internalized_from_seo_geo_and_claude_seo_audits",
    "checks": [
        "Title is clear and aligned with search intent.",
        "First H2 answers the main question quickly.",
        "The article has enough depth for the topic and audience.",
        "Each H2 has a clear role; no isolated H3 sits under a single H2.",
        "Paragraphs are readable and not excessively long.",
        "Lists, tables, and blockquotes are used only when they help comprehension.",
        "FAQ is included only when there are at least 2 strong questions.",
        "The draft avoids placeholders, lorem ipsum, or obvious AI filler.",
    ],
}

_HUMANIZATION_RULES = {
    "source": "internalized_from_humanizer_and_claude_seo_ivan",
    "anti_patterns": [
        "inflated significance language",
        "generic promotional phrasing",
        "vague attributions such as 'experts say' without sources",
        "overused AI vocabulary like 'additionally', 'landscape', 'delve'",
        "em dash overuse",
        "formulaic signposting like 'let's dive in'",
        "chatbot artifacts like 'I hope this helps'",
        "generic conclusions without specific takeaways",
        "keyword repetition that sounds mechanical",
    ],
    "rewrite_principles": [
        "Prefer specific facts and examples over generic praise.",
        "Keep the meaning but simplify inflated language.",
        "Use natural rhythm with a mix of short and medium sentences.",
        "Preserve brand voice and audience level.",
        "Do not fake personality, experience, or certainty.",
    ],
}

_ARTICLE_GENERATION_RULES = {
    "source": "internalized_from_google_official_claude_seo_ivan_claude_seo_agrici",
    "workflow": [
        "research",
        "write",
        "humanize",
        "fact_check",
        "optimize",
    ],
    "rules": [
        "Respect the preferred title unless there is a clear editorial reason to adjust it.",
        "Keep the chosen category when the user provides one.",
        "Generate a real draft, not a stub or mock article.",
        "Store content as HTML compatible with the editor.",
        "Keep the article unpublished after generation.",
        "Generate metadata and reading time automatically.",
        "Create FAQ only when at least 2 useful questions exist.",
        "Use callouts only when they add real value and match project templates.",
    ],
}

_ARTICLE_REVIEW_RULES = {
    "source": "internalized_from_google_official_seo_geo_humanizer",
    "checks": [
        "title_present",
        "slug_present",
        "meta_description_present",
        "content_depth",
        "first_h2_answers_intent",
        "no_isolated_h3",
        "faq_count_valid",
        "sources_for_sensitive_topics",
        "no_keyword_stuffing",
        "readability_ok",
        "basic_eeat_signals",
        "not_too_generic_or_ai_sounding",
    ],
}


def _copy(data: dict) -> dict:
    return deepcopy(data)


def get_google_seo_basics() -> dict:
    return _copy(_GOOGLE_SEO_BASICS)


def get_eeat_checklist() -> dict:
    return _copy(_EEAT_CHECKLIST)


def get_content_quality_checklist() -> dict:
    return _copy(_CONTENT_QUALITY_CHECKLIST)


def get_humanization_rules() -> dict:
    return _copy(_HUMANIZATION_RULES)


def get_article_generation_rules() -> dict:
    return _copy(_ARTICLE_GENERATION_RULES)


def get_article_review_rules() -> dict:
    return _copy(_ARTICLE_REVIEW_RULES)
