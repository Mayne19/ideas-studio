from __future__ import annotations

import json
import re
from html import unescape
from typing import Any

from app.models.article import Article

from app.services.seo.seo_knowledge_pack_service import (
    get_article_review_rules,
    get_content_quality_checklist,
    get_eeat_checklist,
    get_google_seo_basics,
    get_humanization_rules,
)


def _get_value(article: Any, field: str, default: Any = None) -> Any:
    if isinstance(article, dict):
        return article.get(field, default)
    return getattr(article, field, default)


def _strip_html(content: str) -> str:
    with_breaks = re.sub(r"</(p|div|li|h[1-6]|blockquote|tr|table|ul|ol)>", "\n", content, flags=re.IGNORECASE)
    return unescape(re.sub(r"<[^>]+>", " ", with_breaks))


def _html_heading_texts(content: str, level: int) -> list[str]:
    pattern = rf"<h{level}[^>]*>(.*?)</h{level}>"
    return [
        _strip_html(match).strip()
        for match in re.findall(pattern, content, flags=re.IGNORECASE | re.DOTALL)
        if _strip_html(match).strip()
    ]


def _extract_headings(content: str) -> list[dict]:
    if re.search(r"<[a-z][\s\S]*>", content, flags=re.IGNORECASE):
        headings: list[dict] = []
        for match in re.finditer(r"<h([2-4])[^>]*>(.*?)</h\1>", content, flags=re.IGNORECASE | re.DOTALL):
            headings.append(
                {
                    "level": int(match.group(1)),
                    "text": _strip_html(match.group(2)).strip(),
                }
            )
        return headings

    headings = []
    for line in content.splitlines():
        match = re.match(r"^(#{2,4})\s+(.+?)\s*$", line.strip())
        if match:
            headings.append({"level": len(match.group(1)), "text": match.group(2).strip()})
    return headings


def _first_h2_text(content: str) -> str:
    html_h2 = _html_heading_texts(content, 2)
    if html_h2:
        return html_h2[0]
    for line in content.splitlines():
        if re.match(r"^##\s+.+", line.strip()):
            return re.sub(r"^##\s+", "", line.strip())
    return ""


def _count_words(content: str) -> int:
    text = _strip_html(content) if re.search(r"<[a-z][\s\S]*>", content, flags=re.IGNORECASE) else content
    return len(re.findall(r"\b\w+\b", text))


def _sentence_stats(content: str) -> tuple[int, float]:
    text = _strip_html(content) if re.search(r"<[a-z][\s\S]*>", content, flags=re.IGNORECASE) else content
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    word_count = _count_words(content)
    avg = word_count / len(sentences) if sentences else float(word_count)
    return len(sentences), avg


def _parse_faq(faq_json: Any) -> list[dict]:
    if faq_json in (None, "", []):
        return []
    if isinstance(faq_json, list):
        return faq_json
    if isinstance(faq_json, str):
        try:
            data = json.loads(faq_json)
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []
    return []


def _is_sensitive_or_factual(topic: str, content: str) -> bool:
    haystack = f"{topic} {content}".lower()
    markers = (
        "study",
        "research",
        "statistics",
        "statistique",
        "finance",
        "financial",
        "medical",
        "health",
        "legal",
        "law",
        "safety",
        "tax",
        "security",
    )
    return any(marker in haystack for marker in markers)


def _has_sources(content: str) -> bool:
    if re.search(r'https?://', content, flags=re.IGNORECASE):
        return True
    if re.search(r"\baccording to\b|\bsource\b|\bselon\b|\bd'apres\b|\bd'après\b", content, flags=re.IGNORECASE):
        return True
    return False


def _has_isolated_h3(content: str) -> bool:
    headings = _extract_headings(content)
    i = 0
    while i < len(headings):
        heading = headings[i]
        if heading["level"] != 2:
            i += 1
            continue
        h3_count = 0
        j = i + 1
        while j < len(headings) and headings[j]["level"] > 2:
            if headings[j]["level"] == 3:
                h3_count += 1
            j += 1
        if h3_count == 1:
            return True
        i = j
    return False


def _looks_generic_or_ai_sounding(content: str) -> bool:
    haystack = content.lower()
    suspicious_patterns = (
        "[mock]",
        "lorem ipsum",
        "i hope this helps",
        "let's dive in",
        "in conclusion, the future looks bright",
        "pivotal moment",
        "digital landscape",
        "testament to",
    )
    return any(pattern in haystack for pattern in suspicious_patterns)


def _keyword_stuffing(keyword: str, content: str) -> bool:
    keyword = (keyword or "").strip().lower()
    if not keyword:
        return False
    word_count = _count_words(content)
    if word_count == 0:
        return False
    direct = len(re.findall(re.escape(keyword), content.lower()))
    density = direct / word_count * 100
    return density > 3.0


def _first_h2_answers_intent(title: str, first_h2: str) -> bool:
    if not first_h2:
        return False
    title_tokens = {token for token in re.findall(r"[a-zA-ZÀ-ÿ0-9]{4,}", title.lower())}
    h2_tokens = {token for token in re.findall(r"[a-zA-ZÀ-ÿ0-9]{4,}", first_h2.lower())}
    if not title_tokens:
        return bool(h2_tokens)
    overlap = len(title_tokens & h2_tokens)
    direct_markers = (
        "comment",
        "why",
        "what",
        "pourquoi",
        "quand",
        "ce qu",
        "réponse",
        "answer",
    )
    return overlap >= max(1, min(2, len(title_tokens) // 3)) or any(marker in first_h2.lower() for marker in direct_markers)


def review_article_with_knowledge_pack(article: Any) -> dict:
    title = (_get_value(article, "title", "") or "").strip()
    slug = (_get_value(article, "slug", "") or "").strip()
    meta_description = (_get_value(article, "meta_description", "") or "").strip()
    content = (_get_value(article, "content", "") or "").strip()
    keyword = (_get_value(article, "keyword", "") or "").strip()
    faq_items = _parse_faq(_get_value(article, "faq_json"))
    author_name = (_get_value(article, "author_name", "") or "").strip()

    google_basics = get_google_seo_basics()
    eeat_rules = get_eeat_checklist()
    quality_rules = get_content_quality_checklist()
    humanization_rules = get_humanization_rules()
    review_rules = get_article_review_rules()

    issues: list[dict] = []
    passed_checks: list[str] = []
    failed_checks: list[str] = []
    recommendations: list[str] = []

    def pass_check(name: str) -> None:
        passed_checks.append(name)

    def fail_check(name: str, severity: str, message: str, recommendation: str) -> None:
        failed_checks.append(name)
        issues.append(
            {
                "check": name,
                "severity": severity,
                "message": message,
            }
        )
        if recommendation and recommendation not in recommendations:
            recommendations.append(recommendation)

    if title:
        pass_check("title_present")
    else:
        fail_check("title_present", "critical", "Le titre est absent.", "Ajoutez un titre clair aligné avec l'intention de recherche.")

    if slug:
        pass_check("slug_present")
    else:
        fail_check("slug_present", "critical", "Le slug est absent.", "Ajoutez un slug stable et descriptif.")

    if meta_description:
        pass_check("meta_description_present")
    else:
        fail_check("meta_description_present", "warning", "La meta description est absente.", "Ajoutez une meta description utile et orientée clic.")

    word_count = _count_words(content)
    if word_count >= 800:
        pass_check("content_depth")
    else:
        fail_check("content_depth", "critical", f"Le contenu est trop court ({word_count} mots).", "Développez le brouillon pour atteindre une couverture utile du sujet.")

    first_h2 = _first_h2_text(content)
    if _first_h2_answers_intent(title, first_h2):
        pass_check("first_h2_answers_intent")
    else:
        fail_check(
            "first_h2_answers_intent",
            "warning",
            "Le premier H2 ne répond pas assez vite à l'intention principale.",
            "Réécrivez le premier H2 pour donner une réponse directe dès le début.",
        )

    if _has_isolated_h3(content):
        fail_check("no_isolated_h3", "warning", "Un H3 isolé a été détecté sous un H2.", "Ajoutez un second H3 ou remontez la section au niveau H2.")
    else:
        pass_check("no_isolated_h3")

    if faq_items:
        if 2 <= len(faq_items) <= 6:
            pass_check("faq_count_valid")
        else:
            fail_check("faq_count_valid", "warning", f"La FAQ contient {len(faq_items)} question(s).", "Gardez entre 2 et 6 questions utiles dans la FAQ.")
    else:
        pass_check("faq_count_valid")

    if _is_sensitive_or_factual(title, content):
        if _has_sources(content):
            pass_check("sources_for_sensitive_topics")
        else:
            fail_check(
                "sources_for_sensitive_topics",
                "warning",
                "Le sujet semble factuel ou sensible mais aucune source claire n'est visible.",
                "Ajoutez des sources crédibles ou des références explicites pour les affirmations importantes.",
            )
    else:
        pass_check("sources_for_sensitive_topics")

    if _keyword_stuffing(keyword, content):
        fail_check("no_keyword_stuffing", "warning", "Le contenu semble sur-optimisé pour le mot-clé principal.", "Réduisez les répétitions exactes du mot-clé et utilisez plus de variations naturelles.")
    else:
        pass_check("no_keyword_stuffing")

    sentence_count, average_sentence_length = _sentence_stats(content)
    if sentence_count and average_sentence_length <= 24:
        pass_check("readability_ok")
    else:
        fail_check(
            "readability_ok",
            "warning",
            "La lisibilité semble faible, avec des phrases trop longues ou trop compactes.",
            "Raccourcissez les phrases et aérez davantage les paragraphes.",
        )

    eeat_signals = 0
    if author_name:
        eeat_signals += 1
    if _has_sources(content):
        eeat_signals += 1
    if word_count >= 1000:
        eeat_signals += 1
    if "for example" in content.lower() or "par exemple" in content.lower():
        eeat_signals += 1
    if eeat_signals >= 2:
        pass_check("basic_eeat_signals")
    else:
        fail_check(
            "basic_eeat_signals",
            "warning",
            "Les signaux EEAT de base sont trop faibles.",
            "Ajoutez un auteur, des sources, des exemples concrets ou davantage de profondeur éditoriale.",
        )

    if _looks_generic_or_ai_sounding(content):
        fail_check(
            "not_too_generic_or_ai_sounding",
            "warning",
            "Le texte contient des marqueurs génériques ou des formulations trop IA.",
            "Passez une relecture de humanization pour retirer les formulations trop génériques.",
        )
    else:
        pass_check("not_too_generic_or_ai_sounding")

    total_checks = max(1, len(passed_checks) + len(failed_checks))
    severity_penalty = {"critical": 18, "warning": 8, "info": 3}
    penalty = sum(severity_penalty.get(issue["severity"], 0) for issue in issues)
    score_global = max(0, min(100, round(100 - penalty + (len(passed_checks) / total_checks) * 10)))

    seo_related = {"title_present", "slug_present", "meta_description_present", "content_depth", "first_h2_answers_intent", "no_keyword_stuffing"}
    eeat_related = {"sources_for_sensitive_topics", "basic_eeat_signals", "not_too_generic_or_ai_sounding"}
    readability_related = {"readability_ok", "no_isolated_h3", "faq_count_valid"}

    def _score_for(checks: set[str]) -> int:
        passed = sum(1 for check in passed_checks if check in checks)
        failed = sum(1 for check in failed_checks if check in checks)
        total = max(1, passed + failed)
        return max(0, min(100, round((passed / total) * 100)))

    return {
        "score_global": score_global,
        "seo_score": _score_for(seo_related),
        "eeat_score": _score_for(eeat_related),
        "readability_score": _score_for(readability_related),
        "issues": issues,
        "recommendations": recommendations,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "knowledge_pack_sources": {
            "google": google_basics["sources"],
            "eeat": eeat_rules["source"],
            "content_quality": quality_rules["source"],
            "humanization": humanization_rules["source"],
            "review_rules": review_rules["source"],
        },
        "diagnostics": {
            "word_count": word_count,
            "first_h2": first_h2,
            "faq_count": len(faq_items),
            "average_sentence_length": average_sentence_length,
        },
    }


def build_review_error_report(message: str) -> dict:
    return {
        "score_global": 0,
        "seo_score": 0,
        "eeat_score": 0,
        "readability_score": 0,
        "issues": [
            {
                "check": "seo_expert_runtime",
                "severity": "critical",
                "message": message,
            }
        ],
        "recommendations": [
            "Relancez l'audit SEO Expert apres verification du brouillon et des services internes."
        ],
        "passed_checks": [],
        "failed_checks": ["seo_expert_runtime"],
        "knowledge_pack_sources": {},
        "diagnostics": {},
    }


def run_and_store_seo_review(article: Article) -> dict:
    review = review_article_with_knowledge_pack(article)
    article.seo_review_json = review
    return review
