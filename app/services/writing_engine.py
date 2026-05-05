import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.article import Article
from app.services.providers.llm_provider import LLMProvider
from app.services.log_service import log_step
from app.core.utils import calculate_word_count


_MOCK_OUTLINE = [
    {"heading": "Introduction", "notes": "Présenter le sujet et son importance"},
    {"heading": "Partie 1 : Les bases", "notes": "Expliquer les fondamentaux"},
    {"heading": "Partie 2 : Mise en pratique", "notes": "Exemples concrets et étapes"},
    {"heading": "Conclusion", "notes": "Résumé et appel à l'action"},
]


def _mock_content_from_outline(title: str, keyword: str, outline: list[dict]) -> str:
    parts = [f"# {title}\n"]
    for section in outline:
        heading = section.get("heading", "Section")
        notes = section.get("notes", "")
        parts.append(f"\n## {heading}\n\n[Mock] Contenu généré pour la section \"{heading}\". {notes}\n")
    parts.append(f"\n*Article optimisé pour le mot-clé : {keyword}*\n")
    return "".join(parts)


def _extract_excerpt(content: str, max_length: int = 300) -> str:
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("[") and not line.startswith("*"):
            return line[:max_length]
    return content[:max_length]


def start_writing_from_idea(
    db: Session,
    article: Article,
    llm: LLMProvider,
) -> Article:
    # Mark as in progress before any generation
    article.status = "writing_in_progress"
    article.updated_at = datetime.now(timezone.utc)
    db.flush()

    log_step(db, article.project_id, "Démarrage de la rédaction", level="info", step="start_writing", article_id=article.id)

    if llm.is_mock:
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
            f"Rédige un article de blog SEO complet en Markdown.\n"
            f"Titre : {article.title}\n"
            f"Mot-clé principal : {article.keyword}\n"
            f"Angle éditorial : {article.angle or 'informatif'}\n"
            f"Audience : {article.audience or 'grand public'}\n\n"
            f"Plan à suivre :\n"
        )
        for section in outline:
            content_prompt += f"- {section.get('heading', '')}: {section.get('notes', '')}\n"
        content_prompt += "\nRédige l'article complet en Markdown, optimisé pour le SEO."

        content = llm.generate_text(content_prompt, temperature=0.7)
        if not content:
            content = _mock_content_from_outline(article.title, article.keyword or "", outline)

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
        f"Rédaction terminée — {article.word_count} mots",
        level="info",
        step="start_writing",
        article_id=article.id,
    )
    db.flush()
    return article
