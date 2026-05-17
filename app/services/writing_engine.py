import json
import re
from datetime import datetime, timezone
from time import perf_counter
from sqlalchemy.orm import Session

from app.models.article import Article
from app.services.providers.llm_provider import LLMProvider, GenerationFailedError
from app.services.log_service import log_step
from app.core.config import settings
from app.core.utils import (
    calculate_reading_time_minutes,
    calculate_word_count,
    generate_unique_slug,
    slugify,
)
from app.core.markdown import markdown_to_html


_MOCK_OUTLINE = [
    {"heading": "Introduction", "notes": "Présenter le sujet et son importance"},
    {"heading": "Développement", "notes": "Expliquer les concepts clés en détail avec des exemples concrets"},
    {"heading": "Bonnes pratiques", "notes": "Conseils pratiques et recommandations actionnables"},
    {"heading": "Conclusion", "notes": "Résumé des points clés et perspectives"},
]


def _mock_content_from_outline(title: str, keyword: str, outline: list[dict]) -> str:
    parts = [f"<h1>{title}</h1>"]
    for section in outline:
        heading = section.get("heading", "Section")
        notes = section.get("notes", "")
        parts.append(f"<h2>{heading}</h2>")
        parts.append(f"<p>{notes}. Ce contenu est un exemple généré à titre indicatif. Remplacez-le par votre propre texte développé et original.</p>")
        parts.append("<p>Pour rédiger cette section, développez les points suivants :</p><ul><li>Expliquez le concept principal en 2-3 paragraphes</li><li>Donnez un exemple concret et chiffré</li><li>Montrez comment l'appliquer dans votre contexte</li></ul>")
    parts.append(f"<p><em>Article optimisé pour le mot-clé : {keyword}</em></p>")
    return "".join(parts)


def _extract_excerpt(content: str, max_length: int = 300) -> str:
    text = content
    if text.startswith("<"):
        import re
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
    else:
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("[") and not line.startswith("*"):
                text = line
                break
    return text[:max_length]


def _ensure_article_slug(db: Session, article: Article) -> None:
    if article.slug and not article.slug.startswith("idea-"):
        return
    base = slugify(article.title or article.keyword or "article")
    existing = {
        row[0]
        for row in db.query(Article.slug).filter(
            Article.project_id == article.project_id,
            Article.id != article.id,
            Article.slug.like(f"{base}%"),
        ).all()
    }
    article.slug = generate_unique_slug(base, existing)


def _contains_forbidden_placeholder(content: str) -> bool:
    lowered = content.lower()
    return "[mock]" in lowered or "lorem ipsum" in lowered


def _normalize_generated_html(content: str) -> str:
    cleaned = content.strip()
    cleaned = re.sub(r"<p>\s*</p>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<h([1-6])[^>]*>\s*</h\1>", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _generate_faq_json(article: Article, llm: LLMProvider) -> str | None:
    if llm.is_mock:
        return article.faq_json
    faq_prompt = (
        f"À partir de l'article suivant, génère 3 à 5 questions fréquentes utiles.\n"
        f"Titre : {article.title}\n"
        f"Mot-clé principal : {article.keyword}\n"
        f"Contenu HTML :\n{article.content}\n\n"
        "Réponds uniquement avec un objet JSON au format "
        '{"faq":[{"question":"...","answer":"..."}]}.'
    )
    faq_data = llm.generate_json(
        faq_prompt,
        schema_hint='{"faq":[{"question":"...","answer":"..."}]}',
    )
    faq_items = faq_data.get("faq") if isinstance(faq_data, dict) else None
    if not isinstance(faq_items, list):
        return None
    normalized = []
    for item in faq_items:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        if question and answer:
            normalized.append({"question": question, "answer": answer})
    if not normalized:
        return None
    return json.dumps(normalized)


def start_writing_from_idea(
    db: Session,
    article: Article,
    llm: LLMProvider,
    *,
    preferred_title: str | None = None,
    keyword: str | None = None,
    audience: str | None = None,
    angle: str | None = None,
    search_intent: str | None = None,
    include_faq: bool | None = None,
    include_callouts: bool | None = None,
) -> Article:
    started_at = perf_counter()
    if preferred_title:
        article.title = preferred_title.strip()
    if keyword:
        article.keyword = keyword.strip()
    if audience:
        article.audience = audience.strip()
    if angle:
        article.angle = angle.strip()
    if search_intent:
        article.search_intent = search_intent.strip()

    # Mark as in progress before any generation
    article.status = "writing_in_progress"
    article.updated_at = datetime.now(timezone.utc)
    db.flush()

    log_step(
        db,
        article.project_id,
        f"Démarrage de la rédaction avec {llm.describe()}",
        level="info",
        step="start_writing",
        article_id=article.id,
    )

    if llm.is_mock:
        log_step(
            db,
            article.project_id,
            "Mode mock actif pour la rédaction. Brouillon indicatif uniquement.",
            level="warning",
            step="start_writing",
            article_id=article.id,
        )
        outline = _MOCK_OUTLINE
        article.outline_json = json.dumps(outline)
        content = _mock_content_from_outline(article.title, article.keyword or "", outline)
    else:
        outline_prompt = (
            f"Crée un plan détaillé pour un article de blog SEO.\n"
            f"Titre : {article.title}\n"
            f"Mot-clé principal : {article.keyword}\n"
            f"Intention de recherche : {article.search_intent or 'informational'}\n"
            f"Audience : {article.audience or 'grand public'}\n\n"
            f"Réponds en JSON : {{\"outline\": [{{\"heading\": \"...\", \"notes\": \"...\"}}]}}"
        )
        outline_data = llm.generate_json(outline_prompt, schema_hint='{"outline":[{"heading":"...","notes":"..."}]}')
        outline = outline_data if isinstance(outline_data, list) else outline_data.get("outline", _MOCK_OUTLINE)
        if not outline:
            outline = _MOCK_OUTLINE
        article.outline_json = json.dumps(outline)

        log_step(db, article.project_id, f"Plan généré ({len(outline)} sections)", level="info", step="generate_outline", article_id=article.id)

        content_prompt = (
            f"Rédige un article de blog SEO complet et détaillé.\n"
            f"Titre : {article.title}\n"
            f"Mot-clé principal : {article.keyword}\n"
            f"Angle éditorial : {article.angle or 'informatif'}\n"
            f"Audience : {article.audience or 'grand public'}\n\n"
            f"Plan à suivre :\n"
        )
        for section in outline:
            content_prompt += f"- {section.get('heading', '')}: {section.get('notes', '')}\n"
        content_prompt += (
            "\nRédige l'article en Markdown, avec une introduction développée, "
            "plusieurs sections détaillées (H2/H3), des paragraphes riches, "
            "des exemples concrets, des listes si pertinent, des blockquotes si utile "
            "et des tableaux Markdown si cela apporte une vraie valeur. "
            f"Minimum {settings.MIN_GENERATED_ARTICLE_WORDS} mots. "
            "N'inclus pas de section FAQ dans le contenu principal : la FAQ sera générée séparément. "
            f"{'Prévois 1 ou 2 encadrés callout pertinents sous forme de paragraphes introduits naturellement.' if include_callouts else ''} "
            "Sois précis, utile et original."
        )

        content = llm.generate_text(content_prompt, temperature=0.7)
        if not content or not content.strip():
            article.status = "failed"
            article.updated_at = datetime.now(timezone.utc)
            log_step(
                db,
                article.project_id,
                "Le provider IA n'a pas retourné de contenu exploitable pour la rédaction.",
                level="error",
                step="start_writing",
                article_id=article.id,
            )
            raise GenerationFailedError("Provider IA indisponible, génération réelle impossible.")
        content = _normalize_generated_html(markdown_to_html(content))
        if _contains_forbidden_placeholder(content):
            article.status = "failed"
            article.updated_at = datetime.now(timezone.utc)
            log_step(
                db,
                article.project_id,
                "Le contenu généré contient des placeholders interdits ([Mock] ou lorem ipsum).",
                level="error",
                step="start_writing",
                article_id=article.id,
            )
            raise GenerationFailedError("Le provider IA a retourné un contenu non exploitable.")

    article.content = content
    article.word_count = calculate_word_count(content)
    article.reading_time_minutes = calculate_reading_time_minutes(
        article.word_count,
        settings.WORDS_PER_READING_MINUTE,
    )
    _ensure_article_slug(db, article)

    # Generate meta_title if absent
    if not article.meta_title:
        if llm.is_mock:
            article.meta_title = f"{article.title}"[:255]
        else:
            meta_prompt = f"Écris un meta title SEO pour cet article (max 60 caractères) : {article.title}. Mot-clé : {article.keyword}"
            article.meta_title = (llm.generate_text(meta_prompt, temperature=0.3) or article.title)[:255]

    # Generate meta_description if absent
    if not article.meta_description:
        if llm.is_mock:
            article.meta_description = f"Découvrez tout ce que vous devez savoir sur {article.keyword or article.title}. Guide complet avec conseils pratiques."[:500]
        else:
            desc_prompt = f"Écris une meta description SEO (140-160 caractères) pour cet article : {article.title}. Mot-clé : {article.keyword}"
            article.meta_description = (llm.generate_text(desc_prompt, temperature=0.3) or "")[:500]

    # Generate excerpt if absent
    if not article.excerpt:
        article.excerpt = _extract_excerpt(content)

    if include_faq is not False:
        article.faq_json = _generate_faq_json(article, llm)

    article.status = "draft_ready"
    article.updated_at = datetime.now(timezone.utc)

    log_step(
        db,
        article.project_id,
        (
            f"Rédaction terminée — {article.word_count} mots, "
            f"{article.reading_time_minutes} min de lecture, "
            f"faq={'oui' if article.faq_json else 'non'} "
            f"en {int((perf_counter() - started_at) * 1000)} ms via {llm.describe()}"
        ),
        level="info",
        step="start_writing",
        article_id=article.id,
    )
    db.flush()
    return article
