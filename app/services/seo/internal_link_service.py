from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.content import Article, ArticleKeyword, ArticleRevision, Category, Keyword, KeywordRole
from app.models.reference import ArticleStatus
from app.schemas.seo_workflow import InternalLinkPlan, asdict
from app.services.seo.helpers import normalize_text, strip_html


def _extract_excerpt(article: Article, revision_title: str | None, max_chars: int = 140) -> str:
    """Petit extrait textuel de l'article cible pour contextualiser le lien."""
    rev = article.current_revision
    body = ""
    if rev is not None:
        body = rev.body or ""
    text = strip_html(body)
    text = re.sub(r"\s+", " ", text).strip()
    if text:
        return text[:max_chars] + ("…" if len(text) > max_chars else "")
    return revision_title or ""


def build_internal_link_plan(
    db: Session,
    project_id: str,
    keyword: str,
    category_id: str | None = None,
    exclude_article_id: str | None = None,
    limit: int = 5,
    cannibalization_hints: list[dict] | None = None,
    editorial_tier: str | None = None,
) -> InternalLinkPlan:
    """editorial_tier : tier de l'article en cours de génération
    (voir article_editorial_tier_service.py). Un article "cluster" doit
    obligatoirement lier le pillar de sa catégorie (bonus +50, dominant
    sur le scoring lexical normal, plafonné à 18) ; un article "pillar" ne
    lie jamais un autre pillar de la même catégorie (la hiérarchie reste
    à plat, un pillar ne pointe pas vers un pair)."""
    plan = InternalLinkPlan()

    rows = db.execute(
        select(Article, ArticleRevision.title, Keyword.term)
        .outerjoin(ArticleRevision, ArticleRevision.id == Article.current_revision_id)
        .outerjoin(
            ArticleKeyword,
            (ArticleKeyword.article_id == Article.id) & (ArticleKeyword.role == KeywordRole.PRIMARY),
        )
        .outerjoin(Keyword, Keyword.id == ArticleKeyword.keyword_id)
        .where(
            Article.project_id == project_id,
            Article.status_reason_id == ArticleStatus.PUBLISHED,
        )
    ).all()

    if exclude_article_id:
        rows = [r for r in rows if r[0].id != exclude_article_id]

    if editorial_tier == "pillar":
        rows = [r for r in rows if not (r[0].category_id == category_id and r[0].editorial_tier == "pillar")]

    normalized_keyword = normalize_text(keyword)
    scored = []

    # Priority IDs from cannibalization hints (section overlap detected)
    hint_ids: set[str] = set()
    if cannibalization_hints:
        for hint in cannibalization_hints:
            aid = hint.get("article_id")
            if aid:
                hint_ids.add(aid)
                target = db.get(Article, aid)
                hint_excerpt = _extract_excerpt(target, hint.get("title"), 140) if target else ""
                # Add hint entries directly with high relevance
                scored.append({
                    "target_article_id": aid,
                    "target_url": f"/articles/{target.slug}" if target else f"/articles/{aid}",
                    "anchor_text": hint.get("title") or "Article connexe",
                    "placement": "auto",
                    "reason": "section overlap detected",
                    "relevance_score": 20,
                    "category": hint.get("category"),
                    "context": {
                        "target_keyword": hint.get("keyword") or "",
                        "target_excerpt": hint_excerpt,
                        "context_note": "Section complémentaire — utile pour le maillage sur ce sous-sujet",
                    },
                })

    category_names: dict[str, str] = {}

    for article, a_title_raw, a_keyword_raw in rows:
        if article.id in hint_ids:
            continue
        score = 0
        a_title = normalize_text(a_title_raw or "")
        a_keyword = normalize_text(a_keyword_raw or "")

        if a_keyword and normalized_keyword in a_keyword:
            score += 10
        if a_title and normalized_keyword in a_title:
            score += 5
        if article.category_id and category_id and article.category_id == category_id:
            score += 3

        is_category_pillar = (
            editorial_tier == "cluster"
            and article.editorial_tier == "pillar"
            and article.category_id
            and category_id
            and article.category_id == category_id
        )
        if is_category_pillar:
            score += 50

        if score > 0:
            cat_name = None
            if article.category_id:
                if article.category_id not in category_names:
                    cat = db.get(Category, article.category_id)
                    category_names[article.category_id] = cat.name if cat else None
                cat_name = category_names[article.category_id]

            context_note = (
                "Pillar de la catégorie — lien obligatoire (article de référence)"
                if is_category_pillar
                else (
                    "Forte pertinence : même mot-clé principal"
                    if score >= 10
                    else "Pertinence moyenne : sujet connexe ou catégorie partagée"
                )
            )
            scored.append({
                "target_article_id": article.id,
                "target_url": f"/articles/{article.slug}",
                "anchor_text": a_title_raw or "Article connexe",
                "placement": "auto",
                "reason": "Pillar de la catégorie" if is_category_pillar else f"Pertinence {score}/10",
                "relevance_score": score,
                "category": cat_name,
                "context": {
                    "target_keyword": a_keyword_raw or "",
                    "target_excerpt": _extract_excerpt(article, a_title_raw, 140),
                    "context_note": context_note,
                },
            })

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    plan.links = scored[:limit]

    if not plan.links:
        plan.limitations.append("No relevant internal articles found")

    return plan


def build_internal_link_plan_dict(
    db: Session,
    project_id: str,
    keyword: str,
    category_id: str | None = None,
    exclude_article_id: str | None = None,
    limit: int = 5,
    cannibalization_hints: list[dict] | None = None,
    editorial_tier: str | None = None,
) -> dict:
    return asdict(build_internal_link_plan(
        db, project_id, keyword, category_id, exclude_article_id, limit, cannibalization_hints, editorial_tier
    ))
