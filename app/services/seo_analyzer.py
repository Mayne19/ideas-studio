import json
import re
from html import unescape
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.seo_analysis import SeoAnalysis
from app.services.seo.eeat_service import compute_eeat_score
from app.services.seo.geo_expert_service import compute_geo_score
from app.services.seo.originality_service import compute_originality_score
from app.services.seo.readability_service import compute_readability_score
from app.services.scoring_service import compute_global_score


def _strip_html(value: str) -> str:
    with_breaks = re.sub(r"</(p|div|li|h[1-6]|blockquote|tr)>", "\n", value, flags=re.IGNORECASE)
    return unescape(re.sub(r"<[^>]+>", " ", with_breaks))


def _html_heading_texts(content: str, level: int) -> list[str]:
    pattern = rf"<h{level}[^>]*>(.*?)</h{level}>"
    return [
        _strip_html(match).strip()
        for match in re.findall(pattern, content, flags=re.IGNORECASE | re.DOTALL)
        if _strip_html(match).strip()
    ]


def _parse_markdown(content: str, title: str = "") -> dict:
    has_html = bool(re.search(r"<[a-z][\s\S]*>", content, flags=re.IGNORECASE))
    if has_html:
        h1_texts = _html_heading_texts(content, 1)
        h2_texts = _html_heading_texts(content, 2)
        h3_texts = _html_heading_texts(content, 3)
        text_content = _strip_html(content)
        lines = [line.strip() for line in text_content.splitlines() if line.strip()]
        h1_count = len(h1_texts) or (1 if title.strip() else 0)
        h2_count = len(h2_texts)
        h3_count = len(h3_texts)
        h1_text = h1_texts[0] if h1_texts else title.strip()
    else:
        lines = content.splitlines()
        text_content = content
        h1_count = sum(1 for l in lines if re.match(r"^# [^#]", l)) or (1 if title.strip() else 0)
        h2_count = sum(1 for l in lines if re.match(r"^## [^#]", l))
        h3_count = sum(1 for l in lines if re.match(r"^### [^#]", l))
        h1_text = next((l[2:].strip() for l in lines if re.match(r"^# [^#]", l)), title.strip())

    paragraphs = []
    current = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            current.append(stripped)
        else:
            if current:
                paragraphs.append(" ".join(current))
                current = []
    if current:
        paragraphs.append(" ".join(current))

    intro = ""
    for p in paragraphs:
        if not p.startswith("#"):
            intro = p
            break

    sentences = re.split(r"[.!?]+", text_content)
    sentences = [s.strip() for s in sentences if s.strip() and not s.strip().startswith("#")]

    words = text_content.split()
    word_count = len(words)

    conclusion_patterns = r"(conclusion|en résumé|résumé|summary|wrap.?up|final|récapitulatif|synthèse|à retenir|pour conclure|en bref)"
    has_conclusion = any(
        re.match(r"^#{1,3}\s*" + conclusion_patterns, l, re.IGNORECASE)
        for l in lines
    )
    if not has_conclusion and has_html:
        has_conclusion = bool(
            re.search(rf"<h[23][^>]*>[^<]*{conclusion_patterns}[^<]*</h[23]>", content, re.IGNORECASE)
        )
    if not has_conclusion:
        h2_texts = _html_heading_texts(content, 2) if has_html else []
        h3_texts = _html_heading_texts(content, 3) if has_html else []
        all_headings = h2_texts + h3_texts
        if len(all_headings) >= 2:
            last = _normalize(all_headings[-1])
            if any(word in last for word in ("conclu", "récap", "résumé", "synthèse", "retenir", "bilan", "final")):
                has_conclusion = True

    return {
        "h1_count": h1_count,
        "h2_count": h2_count,
        "h3_count": h3_count,
        "h1_text": h1_text,
        "paragraphs": paragraphs,
        "intro": intro,
        "sentences": sentences,
        "word_count": word_count,
        "has_conclusion": has_conclusion,
        "lines": lines,
    }


def _issue(type_: str, category: str, severity: str, message: str, suggestion: str, section: str, auto_fix: bool = False) -> dict:
    return {
        "type": type_,
        "category": category,
        "severity": severity,
        "message": message,
        "suggestion": suggestion,
        "section": section,
        "auto_fix_available": auto_fix,
    }


_NORMALIZE_ACCENTS = str.maketrans({
    "à": "a", "â": "a", "ä": "a",
    "é": "e", "è": "e", "ê": "e", "ë": "e",
    "î": "i", "ï": "i",
    "ô": "o", "ö": "o",
    "ù": "u", "û": "u", "ü": "u",
    "ç": "c",
})

_STOP_WORDS = {"un", "une", "le", "la", "les", "de", "du", "des", "d", "pour", "à", "au", "aux", "sur", "dans", "en", "par", "avec", "est", "sont", "ce", "cet", "cette", "ces", "et", "ou", "mais", "donc"}


def _normalize(text: str) -> str:
    text = text.lower()
    text = text.translate(_NORMALIZE_ACCENTS)
    text = text.replace("'", " ").replace("`", " ").replace("’", " ").replace("-", " ")
    return text


def _keyword_in_text(keyword: str, text: str) -> bool:
    if not keyword:
        return True
    kw = _normalize(keyword)
    txt = _normalize(text)
    if kw in txt:
        return True
    kw_tokens = [t for t in kw.split() if len(t) > 2 and t not in _STOP_WORDS]
    txt_tokens = set(t for t in txt.split() if len(t) > 2 and t not in _STOP_WORDS)
    if not kw_tokens:
        return True
    matches = sum(1 for t in kw_tokens if t in txt_tokens)
    return matches >= max(1, len(kw_tokens) - 1)


def _important_keyword_tokens(keyword: str) -> list[str]:
    normalized = _normalize(keyword)
    return [t for t in re.split(r"[^a-z0-9]+", normalized) if len(t) > 2 and t not in _STOP_WORDS]


def _slug_tokens(slug: str) -> list[str]:
    normalized = _normalize(slug)
    return [t for t in re.split(r"[^a-z0-9]+", normalized) if t]


def _tokens_match(keyword_token: str, slug_token: str) -> bool:
    if keyword_token == slug_token:
        return True
    if len(keyword_token) >= 4 and keyword_token in slug_token:
        return True
    if len(slug_token) >= 4 and slug_token in keyword_token:
        return True
    return False


def _keyword_in_slug(keyword: str, slug: str) -> bool:
    if not keyword:
        return True

    normalized_slug = _normalize(slug)
    flat_slug = re.sub(r"[^a-z0-9]+", "", normalized_slug)
    normalized_keyword = _normalize(keyword)
    flat_keyword = re.sub(r"[^a-z0-9]+", "", normalized_keyword)
    if flat_keyword and flat_keyword in flat_slug:
        return True

    keyword_tokens = _important_keyword_tokens(keyword)
    slug_tokens = _slug_tokens(slug)
    if not keyword_tokens:
        return True
    if not slug_tokens:
        return False

    matched = sum(
        1 for kw_token in keyword_tokens
        if any(_tokens_match(kw_token, slug_token) for slug_token in slug_tokens)
    )
    required = len(keyword_tokens) if len(keyword_tokens) <= 2 else max(2, (len(keyword_tokens) * 3 + 4) // 5)
    return matched >= required


def _run_seo_checks(article: Article, parsed: dict) -> list[dict]:
    issues = []
    keyword = (article.keyword or "").lower().strip()
    content_lower = (article.content or "").lower()
    title_lower = (article.title or "").lower()

    # Keyword in title
    if keyword and not _keyword_in_text(keyword, title_lower):
        issues.append(_issue(
            "keyword_in_title", "seo", "critical",
            "Le mot-clé principal n'est pas dans le titre.",
            f"Ajoutez « {article.keyword} » dans le titre.",
            "title",
        ))

    # Keyword in H1
    if keyword and parsed["h1_text"] and not _keyword_in_text(keyword, parsed["h1_text"]):
        issues.append(_issue(
            "keyword_in_h1", "seo", "warning",
            "Le mot-clé principal n'est pas dans le H1.",
            f"Intégrez « {article.keyword} » dans le H1.",
            "h1",
        ))

    # Keyword in intro
    if keyword and parsed["intro"] and not _keyword_in_text(keyword, parsed["intro"]):
        issues.append(_issue(
            "keyword_in_intro", "seo", "warning",
            "Le mot-clé principal n'apparaît pas dans l'introduction.",
            "Placez le mot-clé dans les 100 premiers mots.",
            "introduction",
        ))

    # Keyword density (0.5% – 3%)
    if keyword and parsed["word_count"] > 0:
        kw_tokens = [t for t in _normalize(keyword).split() if len(t) > 2 and t not in _STOP_WORDS]
        count = content_lower.count(keyword)
        if count == 0 and len(kw_tokens) > 1:
            count = sum(content_lower.count(t) for t in kw_tokens)
        density = count / parsed["word_count"] * 100
        if density < 0.5:
            issues.append(_issue(
                "keyword_density_low", "seo", "warning",
                f"Densité du mot-clé trop faible ({density:.1f}%).",
                "Utilisez le mot-clé plus fréquemment dans le contenu.",
                "content",
            ))
        elif density > 3.0:
            issues.append(_issue(
                "keyword_density_high", "seo", "warning",
                f"Densité du mot-clé trop élevée ({density:.1f}%) — risque de sur-optimisation.",
                "Réduisez la répétition du mot-clé.",
                "content",
            ))

    # H1 uniqueness
    if parsed["h1_count"] == 0:
        issues.append(_issue(
            "missing_h1", "seo", "critical",
            "L'article n'a pas de H1.",
            "Ajoutez un titre H1 au début du contenu.",
            "structure",
        ))
    elif parsed["h1_count"] > 1:
        issues.append(_issue(
            "multiple_h1", "seo", "warning",
            f"L'article contient {parsed['h1_count']} H1.",
            "Un seul H1 par article est recommandé.",
            "structure",
        ))

    # Meta title (fallback to article title)
    meta_title = article.meta_title or article.title or ""
    if not meta_title:
        issues.append(_issue(
            "missing_meta_title", "seo", "critical",
            "Le meta title est absent.",
            "Ajoutez un meta title entre 30 et 60 caractères.",
            "meta",
            auto_fix=True,
        ))
    elif len(meta_title) < 30:
        issues.append(_issue(
            "meta_title_too_short", "seo", "warning",
            f"Le meta title est trop court ({len(meta_title)} caractères).",
            "Visez entre 30 et 60 caractères pour le meta title.",
            "meta",
        ))
    elif len(meta_title) > 60:
        issues.append(_issue(
            "meta_title_too_long", "seo", "warning",
            f"Le meta title est trop long ({len(meta_title)} caractères).",
            "Réduisez le meta title à 60 caractères maximum.",
            "meta",
        ))

    # Meta description
    meta_desc = article.meta_description or ""
    if not meta_desc:
        issues.append(_issue(
            "missing_meta_description", "seo", "critical",
            "La meta description est absente.",
            "Ajoutez une meta description entre 120 et 160 caractères.",
            "meta",
            auto_fix=True,
        ))
    elif len(meta_desc) < 120:
        issues.append(_issue(
            "meta_description_too_short", "seo", "warning",
            f"La meta description est trop courte ({len(meta_desc)} caractères).",
            "Visez entre 120 et 160 caractères.",
            "meta",
        ))
    elif len(meta_desc) > 160:
        issues.append(_issue(
            "meta_description_too_long", "seo", "warning",
            f"La meta description est trop longue ({len(meta_desc)} caractères).",
            "Réduisez la meta description à 160 caractères maximum.",
            "meta",
        ))

    # Keyword in meta title
    if keyword and meta_title and not _keyword_in_text(keyword, meta_title):
        issues.append(_issue(
            "keyword_in_meta_title", "seo", "warning",
            "Le mot-clé principal n'est pas dans le meta title.",
            f"Intégrez « {article.keyword} » dans le meta title.",
            "meta",
        ))

    # Slug
    slug = article.slug or ""
    if not slug:
        issues.append(_issue(
            "missing_slug", "seo", "critical",
            "Le slug est absent.",
            "Ajoutez un slug URL-friendly.",
            "meta",
        ))
    elif keyword:
        kw_slug = re.sub(r"[^a-z0-9]+", "-", _normalize(keyword)).strip("-")
        if not _keyword_in_slug(keyword, slug):
            issues.append(_issue(
                "keyword_in_slug", "seo", "info",
                "Le mot-clé n'est pas dans le slug.",
                f"Envisagez un slug contenant « {kw_slug} ».",
                "meta",
            ))

    # H2 structure
    if parsed["h2_count"] < 2:
        issues.append(_issue(
            "few_h2", "seo", "info",
            f"L'article n'a que {parsed['h2_count']} H2.",
            "Structurez le contenu avec au moins 2 sections H2.",
            "structure",
        ))

    # Topic angle coverage v2.1 — replaces word-count signal
    # Checks that H2 headings cover distinct angles beyond just repeating the keyword
    h2_headings = re.findall(r"<h2[^>]*>(.*?)</h2>", article.content or "", re.IGNORECASE | re.DOTALL)
    h2_texts = [re.sub(r"<[^>]+>", "", h).strip().lower() for h in h2_headings]
    if len(h2_texts) >= 2 and keyword:
        kw_words = set(keyword.split())
        unique_angles = [
            h for h in h2_texts
            if not all(w in h for w in kw_words)  # not just the keyword repeated
        ]
        if len(unique_angles) < max(1, len(h2_texts) // 2):
            issues.append(_issue(
                "low_topic_angle_coverage", "seo", "info",
                "Les sections H2 répètent trop le mot-clé sans couvrir des angles distincts.",
                "Diversifiez les titres H2 pour couvrir différents aspects du sujet (bénéfices, méthodes, exemples, FAQ).",
                "structure",
            ))

    # Image alt text — signal SEO v2.1
    content_html = article.content or ""
    img_tags = re.findall(r"<img[^>]+>", content_html, re.IGNORECASE)
    if img_tags:
        imgs_without_alt = [
            tag for tag in img_tags
            if not re.search(r'alt=["\'][^"\']+["\']', tag, re.IGNORECASE)
        ]
        if imgs_without_alt:
            issues.append(_issue(
                "images_missing_alt", "seo", "warning",
                f"{len(imgs_without_alt)} image(s) sans attribut alt.",
                "Ajoutez un alt descriptif contenant le mot-clé sur les images principales.",
                "media",
            ))

    return issues


def _run_readability_checks(parsed: dict) -> list[dict]:
    issues = []

    # Long sentences (> 25 words)
    long_sentences = [s for s in parsed["sentences"] if len(s.split()) > 25]
    if len(long_sentences) > 3:
        issues.append(_issue(
            "long_sentences", "readability", "warning",
            f"{len(long_sentences)} phrases dépassent 25 mots.",
            "Découpez les phrases longues pour améliorer la lisibilité.",
            "content",
        ))
    elif len(long_sentences) > 0:
        issues.append(_issue(
            "some_long_sentences", "readability", "info",
            f"{len(long_sentences)} phrase(s) dépassent 25 mots.",
            "Envisagez de raccourcir les phrases les plus longues.",
            "content",
        ))

    # Long paragraphs (> 150 words)
    long_paragraphs = [(i, p) for i, p in enumerate(parsed["paragraphs"])
                       if len(p.split()) > 150 and not p.startswith("#")]
    if long_paragraphs:
        previews = []
        for idx, para in long_paragraphs[:3]:
            preview = para[:80] + "..." if len(para) > 80 else para
            previews.append(f"§{idx + 1}: « {preview} »")
        detail = " ; ".join(previews)
        if len(long_paragraphs) > 3:
            detail += f" et {len(long_paragraphs) - 3} autre(s)"
        issues.append(_issue(
            "long_paragraphs", "readability", "warning",
            f"{len(long_paragraphs)} paragraphe(s) dépassent 150 mots.",
            f"Subdivisez les longs paragraphes : {detail}",
            "content",
        ))

    # Intro length
    intro_words = len(parsed["intro"].split()) if parsed["intro"] else 0
    if intro_words == 0:
        issues.append(_issue(
            "missing_intro", "readability", "critical",
            "L'introduction est absente.",
            "Commencez l'article avec un paragraphe d'introduction.",
            "introduction",
        ))
    elif intro_words < 50:
        issues.append(_issue(
            "short_intro", "readability", "warning",
            f"L'introduction est trop courte ({intro_words} mots).",
            "Développez l'introduction pour accrocher le lecteur (50+ mots).",
            "introduction",
        ))

    # Subheading frequency: one H2/H3 per ~300 words
    total_headers = parsed["h2_count"] + parsed["h3_count"]
    if parsed["word_count"] > 600 and total_headers < 2:
        issues.append(_issue(
            "low_subheading_density", "readability", "warning",
            "Trop peu de sous-titres pour la longueur de l'article.",
            "Ajoutez des H2/H3 toutes les 300 mots environ.",
            "structure",
        ))

    return issues


def _run_quality_checks(article: Article, parsed: dict) -> list[dict]:
    issues = []
    content = article.content or ""

    # Mock content detection
    if "[Mock]" in content or "[mock]" in content:
        issues.append(_issue(
            "mock_content", "quality", "critical",
            "Le contenu contient du texte mock/placeholder.",
            "Remplacez tout le contenu mock par du contenu réel.",
            "content",
        ))

    # Word count: info only — scoring v2.1 does not penalize volume
    # (format-relative scoring via content_format/target_word_count)
    if parsed["word_count"] < 100:
        issues.append(_issue(
            "too_short", "quality", "info",
            f"L'article contient peu de contenu ({parsed['word_count']} mots).",
            "Enrichissez le contenu pour que les experts de scoring puissent l'évaluer.",
            "content",
        ))

    # Conclusion
    if not parsed["has_conclusion"]:
        issues.append(_issue(
            "missing_conclusion", "quality", "warning",
            "L'article n'a pas de section de conclusion.",
            "Ajoutez une conclusion pour récapituler les points clés.",
            "structure",
        ))

    # Cover image
    if not article.cover_image_url:
        issues.append(_issue(
            "missing_cover_image", "quality", "info",
            "L'article n'a pas d'image de couverture.",
            "Ajoutez une image de couverture attrayante.",
            "media",
        ))

    # Excerpt (fallback to meta_description or first content paragraph)
    effective_excerpt = article.excerpt or article.meta_description or (parsed["intro"] if parsed.get("intro") else "")
    if not effective_excerpt:
        issues.append(_issue(
            "missing_excerpt", "quality", "info",
            "L'extrait (excerpt) est absent.",
            "Ajoutez un extrait de 1-2 phrases pour les aperçus.",
            "meta",
            auto_fix=True,
        ))

    return issues


def _find_external_links(content: str) -> list[str]:
    links = []
    # Markdown links [text](url)
    for match in re.findall(r"\[([^\]]*)\]\((https?://[^\)]+)\)", content):
        links.append(match[1])
    # HTML links <a href="url">
    for match in re.findall(r'''<a\s[^>]*href=["'](https?://[^"']+)["']''', content, re.IGNORECASE):
        links.append(match)
    return links


def _run_eeat_checks(article: Article, parsed: dict) -> list[dict]:
    issues = []
    content = article.content or ""

    # External links
    external_links = _find_external_links(content)
    if len(external_links) == 0:
        issues.append(_issue(
            "no_external_links", "eeat", "warning",
            "Aucun lien externe vers des sources fiables.",
            "Ajoutez 2-3 liens vers des sources d'autorité.",
            "content",
        ))
    elif len(external_links) < 2:
        issues.append(_issue(
            "few_external_links", "eeat", "info",
            "Seulement 1 lien externe — en ajoutez d'autres.",
            "Visez 2-3 liens externes vers des sources fiables.",
            "content",
        ))

    # Examples/data/stats
    has_examples = bool(re.search(r"\b(par exemple|exemple|e\.g\.|for example|such as|comme|notably|notamment)\b", content, re.IGNORECASE))
    has_stats = bool(re.search(r"\b(\d+[\s%]|selon|d'après|study|étude|research|recherche|statistics?|statistiques?)\b", content, re.IGNORECASE))
    if not has_examples and not has_stats:
        issues.append(_issue(
            "no_examples_or_data", "eeat", "warning",
            "L'article manque d'exemples concrets ou de données.",
            "Illustrez vos points avec des exemples, chiffres ou études.",
            "content",
        ))

    # Actionable advice (numbered lists or action verbs)
    has_actionable = bool(re.search(r"^\d+\.\s", content, re.MULTILINE)) or \
                     bool(re.search(r"\b(étape|step|action|faites|do|utilisez|use|appliquez|apply|commencez|start)\b", content, re.IGNORECASE))
    if not has_actionable:
        issues.append(_issue(
            "low_actionability", "eeat", "info",
            "Le contenu pourrait être plus actionnable.",
            "Ajoutez des listes numérotées ou des étapes concrètes.",
            "content",
        ))

    return issues


def _compute_score(issues: list[dict]) -> float:
    deductions = sum(
        20 if i["severity"] == "critical" else
        10 if i["severity"] == "warning" else
        3
        for i in issues
    )
    return max(0.0, min(100.0, 100.0 - deductions))


def _compute_readiness(issues: list[dict]) -> str:
    severities = {i["severity"] for i in issues}
    if "critical" in severities:
        return "blocked"
    if "warning" in severities:
        return "needs_improvement"
    return "ready"


def _generate_suggestions(article: Article, parsed: dict, issues: list[dict]) -> list[str]:
    suggestions = []
    issue_types = {i["type"] for i in issues}

    if "keyword_in_title" in issue_types or "keyword_in_h1" in issue_types:
        suggestions.append(f"Intégrez le mot-clé « {article.keyword} » dans le titre et le H1.")
    if "missing_meta_title" in issue_types or "missing_meta_description" in issue_types:
        suggestions.append("Complétez les métadonnées SEO (title + description).")
    if "too_short" in issue_types:
        suggestions.append("Enrichissez le contenu pour permettre une évaluation complète par les experts de scoring.")
    if "mock_content" in issue_types:
        suggestions.append("Remplacez tout le contenu [Mock] par du contenu réel avant publication.")
    if "no_external_links" in issue_types:
        suggestions.append("Ajoutez des liens vers des sources externes fiables pour renforcer l'autorité.")
    if "missing_conclusion" in issue_types:
        suggestions.append("Ajoutez une section Conclusion pour clôturer l'article.")
    if "long_sentences" in issue_types or "long_paragraphs" in issue_types:
        suggestions.append("Améliorez la lisibilité en raccourcissant phrases et paragraphes.")

    return suggestions


def analyze_article(db: Session, article_id: str) -> SeoAnalysis:
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise ValueError(f"Article {article_id} not found")

    content = article.content or ""
    parsed = _parse_markdown(content, article.title or "")

    seo_issues = _run_seo_checks(article, parsed)
    readability_issues = _run_readability_checks(parsed)
    quality_issues = _run_quality_checks(article, parsed)
    eeat_issues = _run_eeat_checks(article, parsed)

    all_issues = seo_issues + readability_issues + quality_issues + eeat_issues

    seo_score = _compute_score(seo_issues)
    readability_score = _compute_score(readability_issues)
    quality_score = _compute_score(quality_issues)
    eeat_score = _compute_score(eeat_issues)
    readiness_status = _compute_readiness(all_issues)
    suggestions = _generate_suggestions(article, parsed, all_issues)

    # Run v2.1 expert scoring
    eeat_v2 = compute_eeat_score(article)
    readability_v2 = compute_readability_score(article)
    geo_v2 = compute_geo_score(article)

    # Originality requires other project articles for internal uniqueness
    project_articles = (
        db.query(Article)
        .filter(Article.project_id == article.project_id, Article.id != article.id)
        .limit(50)
        .all()
    )
    originality_v2 = compute_originality_score(article, project_articles)

    eeat_score_final = eeat_v2["score"] if eeat_v2["confidence"] != "low" else eeat_score
    readability_score_final = readability_v2["score"] if readability_v2.get("score") is not None else readability_score

    existing_eeat_json = article.eeat_checklist_json or {}
    if isinstance(existing_eeat_json, str):
        try:
            existing_eeat_json = json.loads(existing_eeat_json)
        except Exception:
            existing_eeat_json = {}
    existing_eeat_json["v2"] = eeat_v2

    existing_geo_json = article.geo_optimization_json or {}
    if isinstance(existing_geo_json, str):
        try:
            existing_geo_json = json.loads(existing_geo_json)
        except Exception:
            existing_geo_json = {}
    existing_geo_json.update({"geo_score": geo_v2["score"], "v2": geo_v2})

    analysis = SeoAnalysis(
        project_id=article.project_id,
        article_id=article.id,
        seo_score=seo_score,
        readability_score=readability_score_final,
        quality_score=quality_score,
        eeat_score=eeat_score_final,
        readiness_status=readiness_status,
        issues_json=json.dumps(all_issues),
        suggestions_json=json.dumps(suggestions),
        created_at=datetime.now(timezone.utc),
    )
    db.add(analysis)

    article.seo_score = seo_score
    article.readability_score = readability_score_final
    article.quality_score = quality_score
    article.eeat_score = eeat_score_final
    article.eeat_checklist_json = existing_eeat_json
    article.geo_optimization_json = existing_geo_json

    # Originality: merge with existing report if any
    existing_orig_json = article.originality_report_json or {}
    if isinstance(existing_orig_json, str):
        try:
            existing_orig_json = json.loads(existing_orig_json)
        except Exception:
            existing_orig_json = {}
    existing_orig_json["v2"] = originality_v2
    article.originality_report_json = existing_orig_json

    article.readiness_status = readiness_status
    article.updated_at = datetime.now(timezone.utc)

    # Compute global score v2.1 now that all 4 experts are stored on the article
    global_result = compute_global_score(article)
    global_score_v2 = global_result["global_score"]
    if global_score_v2 is not None:
        article.global_score = global_score_v2
    if hasattr(article, "global_score_valid"):
        article.global_score_valid = global_result["global_score_valid"]

    db.flush()
    return analysis
