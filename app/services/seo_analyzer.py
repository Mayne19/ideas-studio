import json
import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.seo_analysis import SeoAnalysis


def _parse_markdown(content: str) -> dict:
    lines = content.splitlines()
    h1_count = sum(1 for l in lines if re.match(r"^# [^#]", l))
    h2_count = sum(1 for l in lines if re.match(r"^## [^#]", l))
    h3_count = sum(1 for l in lines if re.match(r"^### [^#]", l))
    h1_text = next((l[2:].strip() for l in lines if re.match(r"^# [^#]", l)), "")

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

    sentences = re.split(r"[.!?]+", content)
    sentences = [s.strip() for s in sentences if s.strip() and not s.strip().startswith("#")]

    words = content.split()
    word_count = len(words)

    has_conclusion = any(
        re.match(r"^#{1,3}\s*(conclusion|en résumé|résumé|summary|wrap.?up|final)", l, re.IGNORECASE)
        for l in lines
    )

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


def _run_seo_checks(article: Article, parsed: dict) -> list[dict]:
    issues = []
    keyword = (article.keyword or "").lower().strip()
    content_lower = (article.content or "").lower()
    title_lower = (article.title or "").lower()

    # Keyword in title
    if keyword and keyword not in title_lower:
        issues.append(_issue(
            "keyword_in_title", "seo", "critical",
            "Le mot-clé principal n'est pas dans le titre.",
            f"Ajoutez « {article.keyword} » dans le titre.",
            "title",
        ))

    # Keyword in H1
    if keyword and parsed["h1_text"] and keyword not in parsed["h1_text"].lower():
        issues.append(_issue(
            "keyword_in_h1", "seo", "warning",
            "Le mot-clé principal n'est pas dans le H1.",
            f"Intégrez « {article.keyword} » dans le H1.",
            "h1",
        ))

    # Keyword in intro
    if keyword and parsed["intro"] and keyword not in parsed["intro"].lower():
        issues.append(_issue(
            "keyword_in_intro", "seo", "warning",
            "Le mot-clé principal n'apparaît pas dans l'introduction.",
            "Placez le mot-clé dans les 100 premiers mots.",
            "introduction",
        ))

    # Keyword density (0.5% – 3%)
    if keyword and parsed["word_count"] > 0:
        count = content_lower.count(keyword)
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

    # Meta title
    meta_title = article.meta_title or ""
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
    if keyword and meta_title and keyword not in meta_title.lower():
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
    elif keyword and keyword.replace(" ", "-") not in slug and keyword.replace(" ", "_") not in slug:
        kw_slug = re.sub(r"[^a-z0-9]+", "-", keyword).strip("-")
        if kw_slug not in slug:
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
    long_paragraphs = [p for p in parsed["paragraphs"] if len(p.split()) > 150 and not p.startswith("#")]
    if long_paragraphs:
        issues.append(_issue(
            "long_paragraphs", "readability", "warning",
            f"{len(long_paragraphs)} paragraphe(s) dépassent 150 mots.",
            "Subdivisez les longs paragraphes pour aérer le texte.",
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

    # Minimum word count
    if parsed["word_count"] < 300:
        issues.append(_issue(
            "too_short", "quality", "critical",
            f"L'article est trop court ({parsed['word_count']} mots).",
            "Visez au moins 800 mots pour un article de blog.",
            "content",
        ))
    elif parsed["word_count"] < 800:
        issues.append(_issue(
            "below_recommended_length", "quality", "warning",
            f"L'article est en dessous de la longueur recommandée ({parsed['word_count']} mots).",
            "Développez le contenu pour atteindre 800+ mots.",
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

    # Excerpt
    if not article.excerpt:
        issues.append(_issue(
            "missing_excerpt", "quality", "info",
            "L'extrait (excerpt) est absent.",
            "Ajoutez un extrait de 1-2 phrases pour les aperçus.",
            "meta",
            auto_fix=True,
        ))

    return issues


def _run_eeat_checks(article: Article, parsed: dict) -> list[dict]:
    issues = []
    content = article.content or ""

    # External links
    external_links = re.findall(r"\[([^\]]+)\]\((https?://[^\)]+)\)", content)
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
    if "too_short" in issue_types or "below_recommended_length" in issue_types:
        suggestions.append(f"Développez l'article ({parsed['word_count']} → 800+ mots recommandés).")
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
    parsed = _parse_markdown(content)

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

    analysis = SeoAnalysis(
        project_id=article.project_id,
        article_id=article.id,
        seo_score=seo_score,
        readability_score=readability_score,
        quality_score=quality_score,
        eeat_score=eeat_score,
        readiness_status=readiness_status,
        issues_json=json.dumps(all_issues),
        suggestions_json=json.dumps(suggestions),
        created_at=datetime.now(timezone.utc),
    )
    db.add(analysis)

    article.seo_score = seo_score
    article.readability_score = readability_score
    article.quality_score = quality_score
    article.eeat_score = eeat_score
    article.readiness_status = readiness_status
    article.updated_at = datetime.now(timezone.utc)

    db.flush()
    return analysis
