"""
HumanInsightsExtractor — Extrait la vraie matière humaine depuis les plateformes publiques.

Sources supportées (HTML-first, pas de dépendance playwright) :
  - Reddit (old.reddit.com — HTML pur)
  - Stack Overflow / Stack Exchange (Q&A tech, HTML pur)
  - Nitter (frontends HTML de Twitter/X — sans JS)
  - Forums détectés dans les SERP (Discourse API JSON, phpBB, vBulletin, XenForo, génériques)
  - Tout contenu HTML servi directement

Sources nécessitant JS (skippées si playwright absent) :
  - Quora (JS lourd)
  - YouTube (JS lourd)

Ce qui est extrait :
  - questions : vraies questions que les gens posent
  - pain_points : frustrations, problèmes, douleurs
  - real_examples : témoignages, expériences terrain
  - objections : scepticismes, contre-arguments
  - positive_experiences : ce qui fonctionne
  - vocabulary : mots exacts des vrais utilisateurs
  - debates : sujets qui divisent

Chaque extracteur est indépendant — échec silencieux si la plateforme est indisponible.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@dataclass
class HumanInsight:
    source_type: str
    source_url: str
    source_name: str
    content: str
    insight_type: str
    author: str | None = None
    engagement: int = 0


@dataclass
class HumanInsightsReport:
    keyword: str
    questions: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)
    real_examples: list[str] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    positive_experiences: list[str] = field(default_factory=list)
    vocabulary: list[str] = field(default_factory=list)
    debates: list[str] = field(default_factory=list)
    all_insights: list[dict] = field(default_factory=list)
    sources_scraped: list[str] = field(default_factory=list)
    sources_failed: list[str] = field(default_factory=list)
    status: str = "pending"


# ─────────────────────────────────────────────────────────
# UTILITAIRE FETCH
# ─────────────────────────────────────────────────────────

def _fetch(url: str, timeout: int = 20):
    """Fetch with httpx + wrap in Scrapling Adaptor."""
    try:
        import httpx
        from scrapling.parser import Adaptor
        resp = httpx.get(url, timeout=timeout, follow_redirects=True, headers=_HEADERS)
        resp.raise_for_status()
        return Adaptor(resp.text, url=url)
    except Exception as exc:
        logger.debug("_fetch failed for %s: %s", url, exc)
        return None


def _safe_int(text: str) -> int:
    try:
        return int(re.sub(r"[^\d]", "", text) or "0")
    except (ValueError, TypeError):
        return 0


# ─────────────────────────────────────────────────────────
# CLASSIFICATION
# ─────────────────────────────────────────────────────────

_QUESTION_MARKS = [
    "?", "comment", "pourquoi", "quand", "où", "qui", "quoi", "quel",
    "how", "why", "when", "where", "what", "which", "who", "can i",
    "is it", "should i", "do i", "does", "help me", "anyone know",
]
_PAIN_MARKS = [
    "problème", "erreur", "impossible", "ne fonctionne pas", "fail",
    "frustrant", "horrible", "worst", "hate", "bug", "issue", "can't",
    "doesn't work", "broken", "terrible", "awful", "struggle",
    "difficulté", "galère", "nul", "mauvais",
]
_POSITIVE_MARKS = [
    "excellent", "parfait", "génial", "super", "great", "amazing",
    "love", "best", "recommend", "works perfectly", "solution",
    "solved", "fixed", "fonctionne", "résolu", "ça marche",
]
_EXAMPLE_MARKS = [
    "j'ai", "i have", "i was", "j'étais", "mon expérience", "my experience",
    "dans mon cas", "in my case", "when i", "quand j'", "chez moi",
    "personnellement", "personally", "for me", "pour moi",
]
_OBJECTION_MARKS = [
    "mais", "cependant", "sauf que", "but", "however", "except",
    "myth", "faux", "wrong", "incorrect", "misleading", "overrated",
    "not true", "pas vrai", "attention", "careful", "warning",
]
_DEBATE_MARKS = [
    " vs ", " versus ", "better", "meilleur", "debate",
    "controversy", "controversial", "avis partagés", "divided",
    "some say", "certains disent", "dépend", "depends",
]


def _classify(text: str) -> str:
    t = text.lower()
    if any(m in t for m in _QUESTION_MARKS):
        return "question"
    if any(m in t for m in _PAIN_MARKS):
        return "pain_point"
    if any(m in t for m in _POSITIVE_MARKS):
        return "positive"
    if any(m in t for m in _EXAMPLE_MARKS):
        return "real_example"
    if any(m in t for m in _OBJECTION_MARKS):
        return "objection"
    if any(m in t for m in _DEBATE_MARKS):
        return "debate"
    return "vocabulary"


# ─────────────────────────────────────────────────────────
# EXTRACTEURS
# ─────────────────────────────────────────────────────────

def _extract_reddit(keyword: str) -> list[HumanInsight]:
    """old.reddit.com — HTML pur, très fiable sans JS."""
    insights: list[HumanInsight] = []
    encoded = urllib.parse.quote(keyword)

    search_urls = [
        f"https://old.reddit.com/search/?q={encoded}&sort=relevance&t=all",
        f"https://old.reddit.com/search/?q={encoded}&sort=top&t=year",
    ]

    scraped_post_urls: list[str] = []

    for search_url in search_urls:
        page = _fetch(search_url)
        if page is None:
            continue

        titles = page.css("a.search-title::text", auto_save=True).getall()
        hrefs = page.css("a.search-title::attr(href)", auto_save=True).getall()
        scores = page.css("span.search-score::text").getall()
        excerpts = page.css("div.search-result-body::text").getall()

        for i, title in enumerate(titles):
            title = title.strip()
            if not title:
                continue
            score = _safe_int(scores[i]) if i < len(scores) else 0
            insights.append(HumanInsight(
                source_type="reddit", source_url=search_url, source_name="Reddit",
                content=title, insight_type=_classify(title), engagement=score,
            ))
            if i < len(hrefs) and hrefs[i]:
                scraped_post_urls.append(hrefs[i])

        for excerpt in excerpts:
            excerpt = excerpt.strip()
            if excerpt and len(excerpt) > 30:
                insights.append(HumanInsight(
                    source_type="reddit", source_url=search_url, source_name="Reddit",
                    content=excerpt, insight_type=_classify(excerpt),
                ))

    # Commentaires des posts les plus pertinents (max 3)
    for post_url in scraped_post_urls[:3]:
        if not post_url.startswith("http"):
            post_url = "https://old.reddit.com" + post_url
        elif "reddit.com" in post_url and "old." not in post_url:
            post_url = post_url.replace("reddit.com", "old.reddit.com")
        post_page = _fetch(post_url)
        if post_page is None:
            continue
        comments = post_page.css("div.usertext-body .md p::text", auto_save=True).getall()
        comment_scores = post_page.css("span.score.unvoted::text").getall()
        for j, comment in enumerate(comments):
            comment = comment.strip()
            if comment and len(comment) > 40:
                score = _safe_int(comment_scores[j]) if j < len(comment_scores) else 0
                insights.append(HumanInsight(
                    source_type="reddit", source_url=post_url, source_name="Reddit comment",
                    content=comment, insight_type=_classify(comment), engagement=score,
                ))

    return insights


def _extract_stackoverflow(keyword: str) -> list[HumanInsight]:
    """Stack Overflow + Stack Exchange — HTML pur."""
    insights: list[HumanInsight] = []
    encoded = urllib.parse.quote(keyword)

    sources = [
        (f"https://stackoverflow.com/search?q={encoded}&tab=votes", "Stack Overflow"),
        (f"https://stackexchange.com/search?q={encoded}", "Stack Exchange"),
    ]

    for url, name in sources:
        page = _fetch(url)
        if page is None:
            continue

        titles = page.css("a.question-hyperlink::text, .s-link::text", auto_save=True).getall()
        votes_raw = page.css(
            "span.vote-count-post::text, .s-post-summary--stats-item-number::text"
        ).getall()
        excerpts = page.css(
            ".excerpt::text, .s-post-summary--content-excerpt::text"
        ).getall()

        for i, title in enumerate(titles):
            title = title.strip()
            if not title:
                continue
            votes = _safe_int(votes_raw[i]) if i < len(votes_raw) else 0
            insights.append(HumanInsight(
                source_type="stackoverflow", source_url=url, source_name=name,
                content=title, insight_type="question", engagement=votes,
            ))

        for excerpt in excerpts:
            excerpt = excerpt.strip()
            if excerpt and len(excerpt) > 40:
                insights.append(HumanInsight(
                    source_type="stackoverflow", source_url=url, source_name=name,
                    content=excerpt, insight_type=_classify(excerpt),
                ))

    return insights


def _extract_nitter(keyword: str) -> list[HumanInsight]:
    """Twitter/X via instances Nitter publiques (HTML pur, sans JS)."""
    insights: list[HumanInsight] = []
    encoded = urllib.parse.quote(keyword)

    INSTANCES = [
        "https://nitter.net",
        "https://nitter.privacydev.net",
        "https://nitter.poast.org",
        "https://nitter.1d4.us",
        "https://nitter.kavin.rocks",
    ]

    for instance in INSTANCES:
        url = f"{instance}/search?q={encoded}&f=tweets"
        page = _fetch(url)
        if page is None:
            continue

        all_text = page.get_all_text() or ""
        if len(all_text.strip()) < 100 or "error" in all_text.lower()[:200]:
            continue

        tweets = page.css(
            ".tweet-content::text, .tweet-text::text, .timeline-item .content p::text",
            auto_save=True
        ).getall()

        for tweet in tweets:
            tweet = tweet.strip()
            if tweet and len(tweet) > 20:
                insights.append(HumanInsight(
                    source_type="twitter",
                    source_url=url,
                    source_name=f"Twitter/X (via Nitter)",
                    content=tweet,
                    insight_type=_classify(tweet),
                ))

        if insights:
            break  # Instance fonctionnelle trouvée

    return insights


def _detect_forum_type(page) -> str:
    generator = page.css("meta[name='generator']::attr(content)").get() or ""
    g = generator.lower()
    text_sample = page.get_all_text()[:500].lower()

    if "discourse" in g or "discourse" in text_sample:
        return "discourse"
    if "phpbb" in g or "phpbb" in text_sample:
        return "phpbb"
    if "vbulletin" in g or "vbulletin" in text_sample:
        return "vbulletin"
    if "xenforo" in g or "xenforo" in text_sample:
        return "xenforo"
    return "generic"


def _extract_google_autocomplete(keyword: str) -> list[HumanInsight]:
    """
    Google Autocomplete — suggestions réelles via l'API JSON publique Google Suggest.
    Ce sont les vraies requêtes tapées par de vraies personnes.
    Pas de Playwright nécessaire — JSON pur via httpx.
    """
    insights: list[HumanInsight] = []
    encoded = urllib.parse.quote(keyword)

    # Variantes : suffixes qui révèlent questions, problèmes, comparaisons
    variants = [
        f"https://suggestqueries.google.com/complete/search?client=firefox&hl=fr&q={encoded}",
        f"https://suggestqueries.google.com/complete/search?client=firefox&hl=fr&q={encoded}+comment",
        f"https://suggestqueries.google.com/complete/search?client=firefox&hl=fr&q={encoded}+pourquoi",
        f"https://suggestqueries.google.com/complete/search?client=firefox&hl=fr&q={encoded}+problème",
        f"https://suggestqueries.google.com/complete/search?client=firefox&hl=fr&q={encoded}+meilleur",
        f"https://suggestqueries.google.com/complete/search?client=firefox&hl=en&q={encoded}",
        f"https://suggestqueries.google.com/complete/search?client=firefox&hl=en&q={encoded}+how",
        f"https://suggestqueries.google.com/complete/search?client=firefox&hl=en&q={encoded}+best",
        f"https://suggestqueries.google.com/complete/search?client=firefox&hl=en&q={encoded}+problem",
    ]

    try:
        import httpx
        seen: set[str] = set()
        for url in variants:
            try:
                resp = httpx.get(url, timeout=10, follow_redirects=True, headers=_HEADERS)
                resp.raise_for_status()
                # Réponse JSON : ["keyword", ["suggestion1", "suggestion2", ...], ...]
                parsed = json.loads(resp.text)
                suggestions = parsed[1] if len(parsed) > 1 and isinstance(parsed[1], list) else []
                for suggestion in suggestions:
                    suggestion = suggestion.strip()
                    if suggestion and suggestion not in seen:
                        seen.add(suggestion)
                        insights.append(HumanInsight(
                            source_type="google_autocomplete",
                            source_url=url,
                            source_name="Google Autocomplete",
                            content=suggestion,
                            insight_type=_classify(suggestion),
                        ))
            except Exception as exc:
                logger.debug("Google Autocomplete URL failed %s: %s", url, exc)
    except Exception as exc:
        logger.warning("Google Autocomplete extractor failed: %s", exc)

    return insights


def _parse_paa_page(page, url: str) -> list[HumanInsight]:
    """Extrait les questions People Also Ask depuis une page de résultats Google."""
    found: list[HumanInsight] = []
    questions: set[str] = set()

    # Sélecteurs stables : data-q est l'attribut le plus pérenne
    for q in page.css("[data-q]::attr(data-q)", auto_save=True).getall():
        q = q.strip()
        if q and "?" in q and len(q) > 10:
            questions.add(q)

    # Sélecteurs CSS des conteneurs PAA (Google les change fréquemment)
    paa_selectors = (
        ".related-question-pair span::text, "
        ".iDjcJe::text, "
        ".CSkcDe::text, "
        ".HwtpBd::text, "
        ".yu3lnd::text, "
        "[jsname] span[role='heading']::text"
    )
    for q in page.css(paa_selectors, auto_save=True).getall():
        q = q.strip()
        if q and "?" in q and len(q) > 10:
            questions.add(q)

    # XPath fallback : texte contenant "?" dans les conteneurs de résultats
    try:
        for q in page.xpath(
            "//*[contains(@class,'related-question') or contains(@data-q,'?')]//text()"
        ).getall():
            q = q.strip()
            if q and "?" in q and len(q) > 10:
                questions.add(q)
    except Exception:
        pass

    # find_by_text : chercher des spans qui contiennent "?"
    try:
        for el in page.find_all("span"):
            text = (el.text or "").strip()
            if text and "?" in text and 10 < len(text) < 200:
                questions.add(text)
    except Exception:
        pass

    for question in questions:
        found.append(HumanInsight(
            source_type="people_also_ask",
            source_url=url,
            source_name="Google — People Also Ask",
            content=question,
            insight_type="question",
        ))
    return found


def _extract_people_also_ask(keyword: str) -> list[HumanInsight]:
    """
    Google People Also Ask — questions les plus fréquentes autour d'un sujet.
    Très précieux pour la FAQ et la structure des articles.

    Utilise StealthyFetcher (playwright) pour contourner la détection bot Google.
    Fallback httpx+Adaptor si playwright absent.
    """
    insights: list[HumanInsight] = []
    encoded = urllib.parse.quote(keyword)
    urls = [
        f"https://www.google.com/search?q={encoded}&hl=fr&gl=fr",
        f"https://www.google.com/search?q={encoded}&hl=en&gl=us",
    ]

    playwright_ok = False
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        playwright_ok = True
    except ImportError:
        pass

    if playwright_ok:
        try:
            from scrapling.fetchers import StealthyFetcher
            for url in urls:
                try:
                    # StealthyFetcher est un classmethod dans scrapling 0.4.9
                    page = StealthyFetcher.fetch(url, headless=True, network_idle=True)
                    insights.extend(_parse_paa_page(page, url))
                except Exception as exc:
                    logger.debug("StealthyFetcher PAA failed %s: %s", url, exc)
            if insights:
                return insights
        except Exception as exc:
            logger.debug("StealthyFetcher PAA overall failed: %s", exc)

    # Fallback : httpx + Adaptor (peut retourner captcha sur Google)
    for url in urls:
        page = _fetch(url)
        if page is None:
            continue
        results = _parse_paa_page(page, url)
        insights.extend(results)

    return insights


def _extract_forums_from_serp(keyword: str, serp_results: list[dict]) -> list[HumanInsight]:
    """Détecte et scrape les forums présents dans les résultats SERP."""
    insights: list[HumanInsight] = []

    FORUM_PATTERNS = [
        "forum", "forums", "community", "discuss", "board", "talk",
        ".io/t/", "/thread/", "/topic/", "/showthread", "/viewtopic",
    ]

    forum_urls = [
        r.get("url", "")
        for r in serp_results
        if any(p in r.get("url", "").lower() for p in FORUM_PATTERNS)
    ]

    for forum_url in forum_urls:
        page = _fetch(forum_url)
        if page is None:
            continue

        text_sample = page.get_all_text()
        if len(text_sample.strip()) < 100:
            continue

        forum_type = _detect_forum_type(page)

        # Discourse : API JSON disponible
        if forum_type == "discourse":
            base = forum_url.split("/t/")[0] if "/t/" in forum_url else forum_url
            api_page = _fetch(f"{base}/search.json?q={urllib.parse.quote(keyword)}")
            if api_page:
                try:
                    data = json.loads(api_page.get_all_text() or "{}")
                    for post in data.get("posts", []):
                        content = post.get("blurb", "").strip()
                        if content and len(content) > 30:
                            insights.append(HumanInsight(
                                source_type="forum_discourse",
                                source_url=forum_url,
                                source_name="Forum (Discourse)",
                                content=content,
                                insight_type=_classify(content),
                                engagement=post.get("like_count", 0),
                            ))
                except Exception:
                    pass

        # Sélecteurs génériques pour posts et threads
        post_selectors = [
            ".post-content::text", ".message-body::text", ".entry-content::text",
            "[class*='post'] p::text", "[class*='message'] p::text",
            ".content p::text", "blockquote::text",
        ]
        for selector in post_selectors:
            posts = page.css(selector, auto_save=True).getall()
            if posts:
                for pt in posts:
                    pt = pt.strip()
                    if pt and len(pt) > 40:
                        insights.append(HumanInsight(
                            source_type=f"forum_{forum_type}",
                            source_url=forum_url,
                            source_name=f"Forum ({forum_type})",
                            content=pt,
                            insight_type=_classify(pt),
                        ))
                break

        for title in page.css(".thread-title::text, .topic-title::text, h2 a::text, h3 a::text", auto_save=True).getall():
            title = title.strip()
            if title and len(title) > 10:
                insights.append(HumanInsight(
                    source_type=f"forum_{forum_type}",
                    source_url=forum_url,
                    source_name="Forum thread",
                    content=title,
                    insight_type=_classify(title),
                ))

    return insights


def _extract_quora(keyword: str) -> list[HumanInsight]:
    """Quora — nécessite playwright (DynamicFetcher). Skip si absent."""
    insights: list[HumanInsight] = []
    encoded = urllib.parse.quote(keyword)
    search_url = f"https://www.quora.com/search?q={encoded}&type=question"

    try:
        from scrapling.fetchers import StealthyFetcher
        page = StealthyFetcher.fetch(search_url, headless=True, network_idle=True)
        for q in page.css("a.q-box span::text, .q-text::text", auto_save=True).getall():
            q = q.strip()
            if q and len(q) > 15 and "?" in q:
                insights.append(HumanInsight(
                    source_type="quora", source_url=search_url, source_name="Quora",
                    content=q, insight_type="question",
                ))
        for ans in page.css("[class*='answer'] p::text", auto_save=True).getall():
            ans = ans.strip()
            if ans and len(ans) > 60:
                insights.append(HumanInsight(
                    source_type="quora", source_url=search_url, source_name="Quora answer",
                    content=ans, insight_type=_classify(ans),
                ))
    except Exception as exc:
        logger.debug("Quora skipped: %s", exc)

    return insights


def _extract_youtube(keyword: str) -> list[HumanInsight]:
    """YouTube — nécessite playwright (DynamicFetcher). Skip si absent."""
    insights: list[HumanInsight] = []
    encoded = urllib.parse.quote(keyword)
    search_url = f"https://www.youtube.com/results?search_query={encoded}"

    try:
        from scrapling.fetchers import DynamicFetcher
        # DynamicFetcher est un classmethod dans scrapling 0.4.9
        page = DynamicFetcher.fetch(search_url, network_idle=True)
        for title in page.css("#video-title::text", auto_save=True).getall():
            title = title.strip()
            if title:
                insights.append(HumanInsight(
                    source_type="youtube", source_url=search_url, source_name="YouTube",
                    content=title, insight_type=_classify(title),
                ))
        for desc in page.css("#description-text::text", auto_save=True).getall():
            desc = desc.strip()
            if desc and len(desc) > 30:
                insights.append(HumanInsight(
                    source_type="youtube", source_url=search_url, source_name="YouTube",
                    content=desc, insight_type=_classify(desc),
                ))
    except Exception as exc:
        logger.debug("YouTube skipped: %s", exc)

    return insights


# ─────────────────────────────────────────────────────────
# MOTEUR PRINCIPAL
# ─────────────────────────────────────────────────────────

def extract_human_insights(
    keyword: str,
    project_id: str | None = None,
    serp_results: list[dict] | None = None,
    language: str = "fr",
) -> dict:
    """
    Lance tous les extracteurs et agrège les insights humains.

    Chaque extracteur est isolé — si l'un échoue, les autres continuent.
    """
    report = HumanInsightsReport(keyword=keyword)
    all_insights: list[HumanInsight] = []

    extractors = [
        ("Google Autocomplete", lambda: _extract_google_autocomplete(keyword)),
        ("People Also Ask", lambda: _extract_people_also_ask(keyword)),
        ("Reddit", lambda: _extract_reddit(keyword)),
        ("StackOverflow", lambda: _extract_stackoverflow(keyword)),
        ("Twitter/Nitter", lambda: _extract_nitter(keyword)),
        ("Quora", lambda: _extract_quora(keyword)),
        ("YouTube", lambda: _extract_youtube(keyword)),
    ]

    if serp_results:
        extractors.append(
            ("Forums SERP", lambda: _extract_forums_from_serp(keyword, serp_results))
        )

    for name, extractor in extractors:
        try:
            results = extractor()
            all_insights.extend(results)
            if results:
                report.sources_scraped.append(f"{name} ({len(results)} insights)")
            else:
                report.sources_failed.append(f"{name} (0 résultats)")
        except Exception as exc:
            logger.warning("%s extractor error: %s", name, exc)
            report.sources_failed.append(f"{name} (erreur: {exc})")

    # Trier par engagement décroissant
    all_insights.sort(key=lambda x: x.engagement, reverse=True)

    # Dédupliquer et agréger par type
    seen: set[str] = set()
    for insight in all_insights:
        content = insight.content.strip()
        if not content or len(content) < 15 or content in seen:
            continue
        seen.add(content)

        t = insight.insight_type
        if t == "question":
            report.questions.append(content)
        elif t == "pain_point":
            report.pain_points.append(content)
        elif t == "real_example":
            report.real_examples.append(content)
        elif t == "objection":
            report.objections.append(content)
        elif t == "positive":
            report.positive_experiences.append(content)
        elif t == "debate":
            report.debates.append(content)
        else:
            report.vocabulary.append(content)

        report.all_insights.append({
            "source_type": insight.source_type,
            "source_name": insight.source_name,
            "source_url": insight.source_url,
            "content": content,
            "insight_type": t,
            "author": insight.author,
            "engagement": insight.engagement,
        })

    report.status = "completed" if all_insights else "no_results"

    return {
        "keyword": keyword,
        "status": report.status,
        "total_insights": len(report.all_insights),
        "questions": report.questions,
        "pain_points": report.pain_points,
        "real_examples": report.real_examples,
        "objections": report.objections,
        "positive_experiences": report.positive_experiences,
        "debates": report.debates,
        "vocabulary": report.vocabulary,
        "all_insights": report.all_insights,
        "sources_scraped": report.sources_scraped,
        "sources_failed": report.sources_failed,
    }
