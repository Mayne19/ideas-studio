from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.utils import slugify, generate_unique_slug, calculate_word_count, calculate_reading_time_minutes
from app.models.content import Article, ArticleKeyword, ArticleRevision, ArticleSeo, Category, Keyword, KeywordRole
from app.models.reference import ArticleStatus, RevisionSource, RunStatus, set_article_status
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticlePublic, ArticlePublicApiResponse, CategoryBrief
from app.services.callout_template_service import extract_callouts_from_content

_EMPTY_CONTENT_MESSAGE = "Protection : contenu vide non sauvegardé pour éviter d'écraser un article existant."


def _is_effectively_empty_content(value: str | None) -> bool:
    if value is None:
        return True
    import re
    text = re.sub(r"<[^>]+>", " ", value)
    text = text.replace("&nbsp;", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text == ""


def _unique_slug(db: Session, project_id: str, title: str, exclude_id: str | None = None) -> str:
    base = slugify(title)
    query = select(Article.slug).where(
        Article.project_id == project_id,
        Article.slug.like(f"{base}%"),
    )
    if exclude_id:
        query = query.where(Article.id != exclude_id)
    existing = {row[0] for row in db.execute(query).all()}
    return generate_unique_slug(base, existing)


def set_primary_keyword(db: Session, project_id: str, article_id: str, term: str | None) -> None:
    db.execute(
        ArticleKeyword.__table__.delete().where(
            ArticleKeyword.article_id == article_id, ArticleKeyword.role == KeywordRole.PRIMARY
        )
    )
    if not term:
        return
    keyword = db.execute(select(Keyword).where(Keyword.project_id == project_id, Keyword.term == term)).scalar_one_or_none()
    if keyword is None:
        keyword = Keyword(project_id=project_id, term=term)
        db.add(keyword)
        db.flush()
    db.add(ArticleKeyword(article_id=article_id, keyword_id=keyword.id, role=KeywordRole.PRIMARY))


def primary_keyword(db: Session, article_id: str) -> str | None:
    return db.execute(
        select(Keyword.term)
        .join(ArticleKeyword, ArticleKeyword.keyword_id == Keyword.id)
        .where(ArticleKeyword.article_id == article_id, ArticleKeyword.role == KeywordRole.PRIMARY)
    ).scalar_one_or_none()


def create_article(db: Session, data: ArticleCreate, project_id: str) -> Article:
    slug = data.slug or _unique_slug(db, project_id, data.title)
    article = Article(
        project_id=project_id,
        category_id=data.category_id,
        sub_niche=data.sub_niche,
        slug=slug,
        search_intent=data.search_intent,
        priority=data.priority,
        is_featured=data.is_featured,
        author_name=data.author_name,
    )
    set_article_status(article, ArticleStatus.DRAFT)
    db.add(article)
    db.flush()

    revision = ArticleRevision(
        article_id=article.id,
        revision_no=1,
        source=RevisionSource.HUMAN,
        title=data.title,
        excerpt=data.excerpt,
        body=data.content,
        word_count=calculate_word_count(data.content or ""),
    )
    db.add(revision)
    db.flush()
    article.current_revision_id = revision.id

    if data.meta_title or data.meta_description:
        db.add(ArticleSeo(article_id=article.id, meta_title=data.meta_title, meta_description=data.meta_description))

    set_primary_keyword(db, project_id, article.id, data.keyword)

    db.commit()
    db.refresh(article)
    return article


def get_article_by_id(db: Session, article_id: str) -> Article | None:
    return db.get(Article, article_id)


def to_public_batch(db: Session, articles: list[Article]) -> list[ArticlePublic]:
    """Équivalent de [to_public(db, a) for a in articles] mais avec une seule
    requête groupée par type de donnée au lieu d'une boucle de ~8 requêtes par
    article (revision, seo, keyword, score, artifacts, workflow_run, pipeline).
    Voir incident du 2026-08-04 : Production/Catégories/Calendrier chargeaient
    30 articles en 16s+ à cause de ce N+1, jusqu'à dépasser le timeout HTTP.

    Réutilise compute_global_score/check_validation_thresholds (même calcul
    exact que to_public) en leur injectant les données préchargées en masse,
    au lieu de dupliquer leur logique métier ici."""
    from app.models.ai import Pipeline, WorkflowRun
    from app.models.content import ArticleScore
    from app.services.seo.artifacts import get_latest_artifacts_bulk
    from app.services.scoring_service import compute_global_score
    from app.services.validation_service import check_validation_thresholds

    if not articles:
        return []

    article_ids = [a.id for a in articles]
    project_ids = list({a.project_id for a in articles})

    revisions_by_id = {
        r.id: r for r in db.execute(
            select(ArticleRevision).where(
                ArticleRevision.id.in_([a.current_revision_id for a in articles if a.current_revision_id])
            )
        ).scalars().all()
    }
    seo_by_article = {
        s.article_id: s for s in db.execute(
            select(ArticleSeo).where(ArticleSeo.article_id.in_(article_ids))
        ).scalars().all()
    }
    keyword_rows = db.execute(
        select(ArticleKeyword.article_id, Keyword.term)
        .join(Keyword, Keyword.id == ArticleKeyword.keyword_id)
        .where(ArticleKeyword.article_id.in_(article_ids), ArticleKeyword.role == KeywordRole.PRIMARY)
    ).all()
    keyword_by_article = {row.article_id: row.term for row in keyword_rows}

    latest_score_by_article: dict[str, ArticleScore] = {}
    for score in db.execute(
        select(ArticleScore)
        .where(ArticleScore.article_id.in_(article_ids))
        .order_by(ArticleScore.article_id, ArticleScore.evaluated_at.desc())
    ).scalars().all():
        latest_score_by_article.setdefault(score.article_id, score)

    scoring_artifacts_by_article = get_latest_artifacts_bulk(
        db, article_ids,
        ["eeat_checklist", "readability_report", "originality_report", "geo_optimization",
         "seo_final_checklist", "human_presence_report"],
    )
    validation_artifacts_by_article = get_latest_artifacts_bulk(
        db, article_ids, ["originality_report", "sources", "estimated_cost", "fact_check_report"],
    )

    latest_run_by_article: dict[str, WorkflowRun] = {}
    for run in db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.article_id.in_(article_ids))
        .order_by(WorkflowRun.article_id, WorkflowRun.started_at.desc())
    ).scalars().all():
        latest_run_by_article.setdefault(run.article_id, run)

    pipeline_by_project = {
        p.project_id: p for p in db.execute(
            select(Pipeline).where(Pipeline.project_id.in_(project_ids))
        ).scalars().all()
    }

    results: list[ArticlePublic] = []
    for article in articles:
        revision = revisions_by_id.get(article.current_revision_id) if article.current_revision_id else None
        seo = seo_by_article.get(article.id)
        keyword = keyword_by_article.get(article.id)
        latest_score = latest_score_by_article.get(article.id)
        latest_run = latest_run_by_article.get(article.id)
        pipeline = pipeline_by_project.get(article.project_id)

        scoring = compute_global_score(
            db, article.id, article=article,
            latest_score=latest_score, artifacts=scoring_artifacts_by_article.get(article.id, {}),
        )

        ctx = {
            "content": revision.body if revision else "",
            "title": revision.title if revision else "",
            "meta_title": seo.meta_title if seo else "",
            "meta_description": seo.meta_description if seo else "",
            "keyword": keyword or "",
            "originality_report": validation_artifacts_by_article.get(article.id, {}).get("originality_report"),
            "sources": validation_artifacts_by_article.get(article.id, {}).get("sources"),
            "estimated_cost": validation_artifacts_by_article.get(article.id, {}).get("estimated_cost"),
            "fact_check": validation_artifacts_by_article.get(article.id, {}).get("fact_check_report"),
            "workflow_failed": bool(latest_run and latest_run.status_reason_id == RunStatus.FAILED),
            "workflow_incomplete": bool(latest_run and latest_run.status_reason_id in (RunStatus.QUEUED, RunStatus.RUNNING)),
            "cost_limit_eur": float(pipeline.cost_limit_per_article) if pipeline and pipeline.cost_limit_per_article else None,
            "scheduled_for": article.scheduled_for,
        }

        try:
            validation = check_validation_thresholds(db, article, precomputed_scoring=scoring, precomputed_context=ctx)
            is_validable = validation["valid"]
            reasons = validation["reasons"]
            warnings = validation["critical_warnings"]
            global_score = validation["global_score"]
            global_score_valid = validation["global_score_valid"]
        except Exception:
            is_validable, reasons, warnings = None, [], []
            global_score = float(latest_score.global_score) if latest_score and latest_score.global_score is not None else None
            global_score_valid = None

        results.append(ArticlePublic(
            id=article.id,
            project_id=article.project_id,
            category_id=article.category_id,
            sub_niche=article.sub_niche,
            title=revision.title if revision else "",
            slug=article.slug,
            content=revision.body if revision else None,
            excerpt=revision.excerpt if revision else None,
            status=article.status_reason_id,
            keyword=keyword,
            meta_title=seo.meta_title if seo else None,
            meta_description=seo.meta_description if seo else None,
            word_count=revision.word_count if revision else 0,
            priority=article.priority,
            is_featured=article.is_featured,
            seo_score=scoring["seo_contrib"],
            readability_score=scoring["readability_contrib"],
            quality_score=scoring["quality_contrib"],
            eeat_score=scoring["eeat_contrib"],
            geo_score=scoring["geo_contrib"],
            global_score=global_score,
            global_score_valid=global_score_valid,
            is_validable=is_validable,
            validation_reasons=reasons,
            critical_warnings=warnings,
            published_at=article.published_at,
            scheduled_for=article.scheduled_for,
            created_at=article.created_at,
            updated_at=article.updated_at,
            author_name=article.author_name,
            reading_time_minutes=revision.reading_time_minutes if revision else None,
            target_word_count=article.target_word_count,
            content_format=article.content_format,
            angle=None,
            search_intent=article.search_intent,
            opportunity_score=float(article.opportunity_score) if article.opportunity_score is not None else None,
            audience=None,
            rejection_reason=article.rejection_reason,
            rejection_note=article.rejection_note,
            has_draft_changes=article.current_revision_id != article.published_revision_id,
        ))
    return results


def to_public(db: Session, article: Article) -> ArticlePublic:
    from app.services.validation_service import check_validation_thresholds

    revision = article.current_revision
    seo = db.get(ArticleSeo, article.id)
    keyword = primary_keyword(db, article.id)

    from app.models.content import ArticleScore
    latest_score = db.execute(
        select(ArticleScore)
        .where(ArticleScore.article_id == article.id)
        .order_by(ArticleScore.evaluated_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    try:
        validation = check_validation_thresholds(db, article)
        is_validable = validation["valid"]
        reasons = validation["reasons"]
        warnings = validation["critical_warnings"]
        global_score = validation["global_score"]
        global_score_valid = validation["global_score_valid"]
    except Exception:
        is_validable, reasons, warnings = None, [], []
        global_score = float(latest_score.global_score) if latest_score and latest_score.global_score is not None else None
        global_score_valid = None

    return ArticlePublic(
        id=article.id,
        project_id=article.project_id,
        category_id=article.category_id,
        sub_niche=article.sub_niche,
        title=revision.title if revision else "",
        slug=article.slug,
        content=revision.body if revision else None,
        excerpt=revision.excerpt if revision else None,
        status=article.status_reason_id,
        keyword=keyword,
        meta_title=seo.meta_title if seo else None,
        meta_description=seo.meta_description if seo else None,
        word_count=revision.word_count if revision else 0,
        priority=article.priority,
        is_featured=article.is_featured,
        seo_score=float(latest_score.seo_score) if latest_score and latest_score.seo_score is not None else None,
        readability_score=float(latest_score.readability_score) if latest_score and latest_score.readability_score is not None else None,
        quality_score=float(latest_score.quality_score) if latest_score and latest_score.quality_score is not None else None,
        eeat_score=float(latest_score.eeat_score) if latest_score and latest_score.eeat_score is not None else None,
        geo_score=float(latest_score.geo_score) if latest_score and latest_score.geo_score is not None else None,
        global_score=global_score,
        global_score_valid=global_score_valid,
        is_validable=is_validable,
        validation_reasons=reasons,
        critical_warnings=warnings,
        published_at=article.published_at,
        scheduled_for=article.scheduled_for,
        created_at=article.created_at,
        updated_at=article.updated_at,
        author_name=article.author_name,
        reading_time_minutes=revision.reading_time_minutes if revision else None,
        target_word_count=article.target_word_count,
        content_format=article.content_format,
        angle=None,
        search_intent=article.search_intent,
        opportunity_score=float(article.opportunity_score) if article.opportunity_score is not None else None,
        audience=None,
        rejection_reason=article.rejection_reason,
        rejection_note=article.rejection_note,
        has_draft_changes=article.current_revision_id != article.published_revision_id,
    )


def list_articles(
    db: Session,
    project_id: str,
    status: int | None = None,
    statuses: list[int] | None = None,
    category_id: str | None = None,
    search: str | None = None,
    published_only: bool = False,
    archived: bool = False,
    blocked_cost_limit: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Article]:
    query = select(Article).where(Article.project_id == project_id)
    if published_only:
        query = query.where(Article.status_reason_id == ArticleStatus.PUBLISHED)
    elif archived:
        query = query.where(Article.status_reason_id == ArticleStatus.ARCHIVED)
    elif status is not None:
        query = query.where(Article.status_reason_id == status)
    elif statuses:
        query = query.where(Article.status_reason_id.in_(statuses))
    if category_id:
        query = query.where(Article.category_id == category_id)
    if search:
        query = query.join(ArticleRevision, ArticleRevision.id == Article.current_revision_id).where(
            ArticleRevision.title.ilike(f"%{search}%")
        )

    query = query.order_by(Article.created_at.desc())
    rows = db.execute(query).scalars().all()

    if blocked_cost_limit is not None:
        from app.services.seo.artifacts import get_latest_artifact
        filtered = []
        for article in rows:
            cost_data = get_latest_artifact(db, article.id, "estimated_cost")
            try:
                cost = float(cost_data.get("estimated_cost_eur")) if cost_data else None
            except (TypeError, ValueError):
                cost = None
            if cost is not None and cost > blocked_cost_limit:
                filtered.append(article)
        rows = filtered

    return rows[offset:offset + limit]


def update_article(db: Session, article: Article, data: ArticleUpdate) -> Article:
    update_dict = data.model_dump(exclude_unset=True)

    if (
        article.status_reason_id == ArticleStatus.PUBLISHED
        and "content" in update_dict
        and _is_effectively_empty_content(update_dict.get("content"))
        and article.current_revision
        and not _is_effectively_empty_content(article.current_revision.body)
    ):
        raise HTTPException(status_code=409, detail=_EMPTY_CONTENT_MESSAGE)

    revision_fields = {"title", "content", "excerpt", "faq", "callouts"}
    seo_fields = {"meta_title", "meta_description"}
    article_fields = {
        "category_id", "sub_niche", "slug", "search_intent",
        "rejection_reason", "rejection_note", "priority", "is_featured", "author_name",
        "target_word_count", "content_format",
    }

    if revision_fields & update_dict.keys():
        current = article.current_revision
        last_no = db.execute(
            select(ArticleRevision.revision_no)
            .where(ArticleRevision.article_id == article.id)
            .order_by(ArticleRevision.revision_no.desc())
            .limit(1)
        ).scalar_one_or_none() or 0
        body = update_dict.get("content", current.body if current else None)
        revision = ArticleRevision(
            article_id=article.id,
            revision_no=last_no + 1,
            source=RevisionSource.HUMAN,
            title=update_dict.get("title", current.title if current else ""),
            excerpt=update_dict.get("excerpt", current.excerpt if current else None),
            body=body,
            faq=update_dict.get("faq", current.faq if current else []),
            callouts=update_dict.get("callouts", extract_callouts_from_content(body) or (current.callouts if current else [])),
            word_count=calculate_word_count(body or ""),
            reading_time_minutes=calculate_reading_time_minutes(calculate_word_count(body or "")),
        )
        db.add(revision)
        db.flush()
        article.current_revision_id = revision.id

    if seo_fields & update_dict.keys():
        seo = db.get(ArticleSeo, article.id)
        if seo is None:
            seo = ArticleSeo(article_id=article.id)
            db.add(seo)
        if "meta_title" in update_dict:
            seo.meta_title = update_dict["meta_title"]
        if "meta_description" in update_dict:
            seo.meta_description = update_dict["meta_description"]

    if "keyword" in update_dict:
        set_primary_keyword(db, article.project_id, article.id, update_dict["keyword"])

    for field in article_fields:
        if field in update_dict:
            setattr(article, field, update_dict[field])

    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return article


def promote_article(db: Session, article: Article) -> Article:
    """Historiquement : recopiait content -> published_*. En v3, published_revision_id
    EST le snapshot — rien à recopier hors de publish_article. Conservé comme no-op
    pour compatibilité de route, voir REPRENDRE-LA-MAIN.md §6 étape 5."""
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return article


def delete_article(db: Session, article: Article) -> None:
    """content.articles cascade sur article_revisions/article_seo/article_scores/
    article_comments/article_keywords/article_links/artifacts/workflow_runs —
    voir ON DELETE CASCADE dans 01-schema.sql."""
    db.delete(article)
    db.commit()


def get_public_articles(
    db: Session,
    project_id: str,
    limit: int = 20,
    offset: int = 0,
    category_slug: str | None = None,
    sub_niche: str | None = None,
    featured: bool | None = None,
) -> list[ArticlePublicApiResponse]:
    query = select(Article).where(Article.project_id == project_id, Article.status_reason_id == ArticleStatus.PUBLISHED)

    if category_slug:
        query = query.join(Category, Article.category_id == Category.id).where(Category.slug == category_slug)
    if sub_niche:
        query = query.where(Article.sub_niche == sub_niche)
    if featured is not None:
        query = query.where(Article.is_featured == featured)

    articles = db.execute(
        query.order_by(Article.published_at.desc()).limit(limit).offset(offset)
    ).scalars().all()

    category_ids = {a.category_id for a in articles if a.category_id}
    category_map: dict[str, Category] = {}
    if category_ids:
        for cat in db.execute(select(Category).where(Category.id.in_(category_ids))).scalars().all():
            category_map[cat.id] = cat

    return [_to_public_response(db, a, category_map.get(a.category_id) if a.category_id else None) for a in articles]


def get_public_article_by_slug(db: Session, project_id: str, slug: str) -> ArticlePublicApiResponse | None:
    article = db.execute(
        select(Article).where(
            Article.project_id == project_id, Article.slug == slug, Article.status_reason_id == ArticleStatus.PUBLISHED
        )
    ).scalar_one_or_none()
    if not article:
        return None
    category = db.get(Category, article.category_id) if article.category_id else None
    return _to_public_response(db, article, category)


def _to_public_response(db: Session, article: Article, category: Category | None) -> ArticlePublicApiResponse:
    revision = article.published_revision or article.current_revision
    seo = db.get(ArticleSeo, article.id)
    keyword = primary_keyword(db, article.id)
    return ArticlePublicApiResponse(
        id=article.id,
        title=revision.title if revision else "",
        slug=article.slug,
        excerpt=revision.excerpt if revision else None,
        content=revision.body if revision else None,
        category=CategoryBrief(
            id=category.id,
            name=category.name,
            slug=category.slug,
            color=category.color,
        ) if category else None,
        category_slug=category.slug if category else None,
        category_color=category.color if category else None,
        sub_niche=article.sub_niche,
        is_featured=article.is_featured,
        main_keyword=keyword,
        meta_title=seo.meta_title if seo else None,
        meta_description=seo.meta_description if seo else None,
        author_name=article.author_name,
        reading_time_minutes=revision.reading_time_minutes if revision else None,
        faq=revision.faq if revision else [],
        callouts=revision.callouts if revision else [],
        published_at=article.published_at,
        updated_at=article.updated_at,
        has_draft_changes=article.current_revision_id != article.published_revision_id,
    )
