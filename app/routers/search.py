from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_, select
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.core import Project, ProjectMember, User
from app.models.content import Article, ArticleKeyword, ArticleRevision, Category, Keyword, MediaAsset
from app.models.reference import KeywordRole, MembershipStatus

router = APIRouter(tags=["search"])


@router.get("/search")
def global_search(
    q: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not q or not q.strip():
        return []

    query = q.strip()
    member_project_ids = db.execute(
        select(ProjectMember.project_id).where(
            ProjectMember.user_id == current_user.id,
            ProjectMember.status_reason_id == MembershipStatus.ACTIVE,
        )
    ).scalars().all()

    if not member_project_ids:
        return []

    results = []

    settings_entries = [
        ("settings", "Paramètres", "Général", "settings"),
        ("strategy", "Stratégie", "Audience, ton éditorial et consignes IA", "settings/strategy"),
        ("providers", "Providers", "Connecter Gemini, OpenAI, OpenRouter, Anthropic, Mistral", "settings/providers"),
        ("agents", "Agents", "Assigner providers et modèles aux agents IA", "settings/agents"),
        ("pipeline", "Pipeline", "Automatisations éditoriales et génération planifiée", "settings/pipeline"),
        ("integration", "Intégration", "Site connecté, API et revalidation", "settings/integration"),
        ("media", "Médias", "Médiathèque du projet", "media"),
        ("articles", "Articles", "Bibliothèque CMS", "articles"),
        ("ideas", "Idées", "Backlog intelligent", "ideas"),
        ("production", "Production", "Workflow de fabrication", "production"),
        ("validation", "Validation", "Contrôle humain", "validation"),
        ("generate", "Génération IA", "Exécution et diagnostic IA", "generate"),
    ]
    normalized_query = query.lower()
    for project_id in member_project_ids:
        for key, title, subtitle, path in settings_entries:
            haystack = f"{key} {title} {subtitle}".lower()
            if normalized_query in haystack:
                results.append({
                    "type": "page",
                    "id": f"{project_id}:{key}",
                    "title": title,
                    "subtitle": subtitle,
                    "url": f"/projects/{project_id}/{path}",
                    "project_id": project_id,
                })

    project_names = {
        p.id: p.name
        for p in db.execute(select(Project).where(Project.id.in_(member_project_ids))).scalars().all()
    }

    # Search articles (join revision pour titre/contenu, join keyword pour mot-clé)
    article_rows = db.execute(
        select(Article, ArticleRevision, Keyword.term)
        .join(ArticleRevision, ArticleRevision.id == Article.current_revision_id)
        .outerjoin(
            ArticleKeyword,
            (ArticleKeyword.article_id == Article.id) & (ArticleKeyword.role == KeywordRole.PRIMARY),
        )
        .outerjoin(Keyword, Keyword.id == ArticleKeyword.keyword_id)
        .where(
            Article.project_id.in_(member_project_ids),
            or_(
                ArticleRevision.title.ilike(f"%{query}%"),
                Article.slug.ilike(f"%{query}%"),
                ArticleRevision.body.ilike(f"%{query}%"),
                Keyword.term.ilike(f"%{query}%"),
                ArticleRevision.excerpt.ilike(f"%{query}%"),
            ),
        )
        .limit(limit)
    ).all()
    for article, revision, keyword_term in article_rows:
        results.append({
            "type": "article",
            "id": article.id,
            "title": revision.title,
            "subtitle": project_names.get(article.project_id, str(article.status_reason_id)),
            "slug": article.slug,
            "excerpt": revision.excerpt,
            "url": f"/projects/{article.project_id}/articles/{article.id}/edit",
            "project_id": article.project_id,
            "project_name": project_names.get(article.project_id),
            "status": article.status_reason_id,
            "updated_at": article.updated_at.isoformat() if article.updated_at else None,
        })

    # Search categories
    categories = db.execute(
        select(Category).where(
            Category.project_id.in_(member_project_ids),
            or_(
                Category.name.ilike(f"%{query}%"),
                Category.description.ilike(f"%{query}%"),
            ),
        ).limit(limit)
    ).scalars().all()
    for c in categories:
        results.append({
            "type": "category",
            "id": c.id,
            "title": c.name,
            "subtitle": project_names.get(c.project_id, "Catégorie"),
            "slug": c.slug,
            "excerpt": c.description,
            "url": f"/projects/{c.project_id}/categories",
            "project_id": c.project_id,
            "project_name": project_names.get(c.project_id),
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })

    media_items = db.execute(
        select(MediaAsset).where(
            MediaAsset.project_id.in_(member_project_ids),
            or_(
                MediaAsset.filename.ilike(f"%{query}%"),
                MediaAsset.alt_text.ilike(f"%{query}%"),
                MediaAsset.caption.ilike(f"%{query}%"),
            ),
        ).limit(limit)
    ).scalars().all()
    for media in media_items:
        results.append({
            "type": "media",
            "id": media.id,
            "title": media.filename or media.url,
            "subtitle": project_names.get(media.project_id, "Média"),
            "url": f"/projects/{media.project_id}/media",
            "project_id": media.project_id,
            "project_name": project_names.get(media.project_id),
            "updated_at": media.created_at.isoformat() if media.created_at else None,
        })

    # Search projects
    matched_projects = db.execute(
        select(Project).where(
            Project.id.in_(member_project_ids),
            Project.name.ilike(f"%{query}%"),
        ).limit(limit)
    ).scalars().all()
    for p in matched_projects:
        results.append({
            "type": "project",
            "id": p.id,
            "title": p.name,
            "subtitle": p.domain,
            "slug": p.name,
            "excerpt": p.domain,
            "url": f"/projects/{p.id}",
            "project_id": p.id,
            "project_name": p.name,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        })

    return results
