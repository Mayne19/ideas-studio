import json
from datetime import datetime, timezone
from time import perf_counter
from sqlalchemy.orm import Session

from app.models.article import Article
from app.services.providers.llm_provider import LLMProvider, GenerationFailedError
from app.services.log_service import log_step
from app.core.utils import calculate_word_count
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


def start_writing_from_idea(
    db: Session,
    article: Article,
    llm: LLMProvider,
) -> Article:
    started_at = perf_counter()
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
            f"Réponds en JSON : liste d'objets {{\"heading\": \"...\", \"notes\": \"...\"}}"
        )
        outline_data = llm.generate_json(outline_prompt)
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
            "des exemples concrets, des listes si pertinent, et une FAQ en fin d'article. "
            "Minimum 800 mots. Sois précis, utile et original."
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
        content = markdown_to_html(content)

    article.content = content
    article.word_count = calculate_word_count(content)

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

    article.status = "draft_ready"
    article.updated_at = datetime.now(timezone.utc)

    log_step(
        db,
        article.project_id,
        f"Rédaction terminée — {article.word_count} mots en {int((perf_counter() - started_at) * 1000)} ms via {llm.describe()}",
        level="info",
        step="start_writing",
        article_id=article.id,
    )
    db.flush()
    return article
