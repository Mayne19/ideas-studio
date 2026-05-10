import json
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.core.utils import calculate_word_count
from app.models.article import Article
from app.models.article_log import ArticleLog
from app.models.article_version import ArticleVersion
from app.models.category import Category
from app.models.media_asset import MediaAsset
from app.models.notification import Notification
from app.models.optimization_recommendation import OptimizationRecommendation
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.seo_analysis import SeoAnalysis
from app.models.traffic_event import TrafficEvent
from app.models.user import User

DEMO_USER_EMAIL = "lucas@ideas-studio.dev"
DEMO_PROJECT_NAME = "Ideas Studio Demo"
DEMO_DOMAIN = "demo.ideas-studio.dev"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def token() -> str:
    return secrets.token_urlsafe(48)


def slugify(text: str) -> str:
    allowed = []
    for char in text.lower():
        if char.isalnum():
            allowed.append(char)
        elif char in {" ", "-", "_", "&"}:
            allowed.append("-")
    slug = "".join(allowed)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def get_or_create_project(db, user: User) -> Project:
    project = (
        db.query(Project)
        .filter(Project.name == DEMO_PROJECT_NAME, Project.domain == DEMO_DOMAIN)
        .first()
    )
    if project is None:
        now = utc_now()
        project = Project(
            owner_id=user.id,
            name=DEMO_PROJECT_NAME,
            domain=DEMO_DOMAIN,
            language="fr",
            country_target="FR",
            audience="Fondateurs, responsables contenu et consultants SEO qui veulent piloter une stratégie éditoriale assistée par IA.",
            tone="expert, clair, actionnable",
            status="connected",
            public_tracking_key=token(),
            secret_api_key=token(),
            connected_at=now - timedelta(days=35),
            last_seen_at=now - timedelta(hours=2),
            created_at=now - timedelta(days=90),
            updated_at=now - timedelta(hours=2),
        )
        db.add(project)
        db.flush()
    elif project.owner_id != user.id:
        project.owner_id = user.id
        project.updated_at = utc_now()

    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
        .first()
    )
    if member is None:
        db.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner", status="active"))
    else:
        member.role = "owner"
        member.status = "active"

    return project


def seed_categories(db, project: Project) -> dict[str, Category]:
    rows = [
        ("SEO Technique", "seo-technique", "Architecture, indexation, maillage interne et qualité technique.", 10, 6),
        ("IA & Rédaction", "ia-redaction", "Méthodes de production éditoriale augmentée par IA.", 20, 8),
        ("Optimisation", "optimisation", "Amélioration continue des contenus et priorisation des actions.", 30, 4),
        ("Performance", "performance", "Trafic, conversion, reporting et pilotage business.", 40, 4),
    ]
    categories: dict[str, Category] = {}
    for name, slug, description, priority, frequency in rows:
        category = (
            db.query(Category)
            .filter(Category.project_id == project.id, Category.slug == slug)
            .first()
        )
        if category is None:
            category = Category(
                project_id=project.id,
                name=name,
                slug=slug,
                description=description,
                priority=priority,
                target_frequency=frequency,
                created_at=utc_now() - timedelta(days=82 - priority // 10),
                updated_at=utc_now() - timedelta(days=7),
            )
            db.add(category)
            db.flush()
        categories[slug] = category
    return categories


def article_content(title: str, keyword: str) -> str:
    return (
        f"<h2>{title}</h2>"
        f"<p>Cet article démo sert à tester le workflow éditorial Ideas Studio autour du mot-clé <strong>{keyword}</strong>.</p>"
        "<p>Il contient un angle, une intention de recherche, des scores qualité et des métadonnées pour alimenter les vues projet.</p>"
        "<h3>Points clés</h3>"
        "<ul><li>Identifier l'opportunité SEO.</li><li>Structurer le contenu pour la recherche.</li><li>Prioriser les actions mesurables.</li></ul>"
        "<p>La version complète peut être enrichie depuis l'éditeur une fois le scénario validé.</p>"
    )


def seed_article(db, project: Project, category: Category, data: dict) -> Article:
    article = (
        db.query(Article)
        .filter(Article.project_id == project.id, Article.slug == data["slug"])
        .first()
    )
    now = utc_now()
    if article is None:
        content = data.get("content") or article_content(data["title"], data["keyword"])
        article = Article(
            project_id=project.id,
            category_id=category.id,
            title=data["title"],
            slug=data["slug"],
            content=content,
            excerpt=data["excerpt"],
            status=data["status"],
            keyword=data["keyword"],
            secondary_keywords_json=json_dumps(data["secondary_keywords"]),
            audience=project.audience,
            angle=data["angle"],
            search_intent=data["search_intent"],
            outline_json=json_dumps(data["outline"]),
            serp_summary_json=json_dumps(data["serp_summary"]),
            opportunity_score=data["opportunity_score"],
            priority=data["priority"],
            meta_title=data["meta_title"],
            meta_description=data["meta_description"],
            cover_image_url=data.get("cover_image_url"),
            word_count=calculate_word_count(content),
            seo_score=data["seo_score"],
            readability_score=data["readability_score"],
            quality_score=data["quality_score"],
            eeat_score=data["eeat_score"],
            readiness_status=data["readiness_status"],
            faq_json=json_dumps(data["faq"]),
            callouts_json=json_dumps(data["callouts"]),
            internal_links_json=json_dumps(data["internal_links"]),
            external_links_json=json_dumps(data["external_links"]),
            search_console_metrics_json=json_dumps(data["search_console_metrics"]),
            content_blocks_json=json_dumps(data["content_blocks"]),
            published_at=data.get("published_at"),
            scheduled_at=data.get("scheduled_at"),
            created_at=now - timedelta(days=data["age_days"]),
            updated_at=now - timedelta(days=data["updated_days"]),
        )
        db.add(article)
        db.flush()
    return article


def seed_analyses_and_related(db, project: Project, user: User, articles: list[Article]) -> None:
    for index, article in enumerate(articles, start=1):
        has_analysis = (
            db.query(SeoAnalysis)
            .filter(SeoAnalysis.article_id == article.id)
            .first()
        )
        if has_analysis is None:
            db.add(SeoAnalysis(
                project_id=project.id,
                article_id=article.id,
                seo_score=article.seo_score or 0,
                readability_score=article.readability_score or 0,
                quality_score=article.quality_score or 0,
                eeat_score=article.eeat_score or 0,
                readiness_status=article.readiness_status or "needs_improvement",
                issues_json=json_dumps([
                    "Ajouter un exemple concret dans l'introduction",
                    "Renforcer le maillage interne vers une page pilier",
                ]),
                suggestions_json=json_dumps([
                    "Ajouter une FAQ courte",
                    "Clarifier l'intention de recherche dans le chapô",
                ]),
                created_at=utc_now() - timedelta(days=max(1, index)),
            ))

        has_version = (
            db.query(ArticleVersion)
            .filter(ArticleVersion.article_id == article.id, ArticleVersion.version_number == 1)
            .first()
        )
        if has_version is None:
            db.add(ArticleVersion(
                project_id=project.id,
                article_id=article.id,
                title=article.title,
                slug=article.slug,
                content=article.content,
                excerpt=article.excerpt,
                meta_title=article.meta_title,
                meta_description=article.meta_description,
                cover_image_url=article.cover_image_url,
                faq_json=article.faq_json,
                callouts_json=article.callouts_json,
                internal_links_json=article.internal_links_json,
                external_links_json=article.external_links_json,
                content_blocks_json=article.content_blocks_json,
                version_number=1,
                version_type="manual",
                created_by=user.id,
                created_at=article.created_at + timedelta(hours=2),
            ))

        has_media = (
            db.query(MediaAsset)
            .filter(MediaAsset.article_id == article.id)
            .first()
        )
        if has_media is None:
            db.add(MediaAsset(
                project_id=project.id,
                article_id=article.id,
                url=article.cover_image_url or f"https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1200&q=80&sig={index}",
                filename=f"{article.slug}.jpg",
                mime_type="image/jpeg",
                size=245000 + index * 12000,
                alt_text=f"Illustration pour {article.title}",
                caption="Image de démonstration pour l'environnement de test.",
                source="unsplash-demo-url",
                created_at=article.created_at + timedelta(hours=3),
                updated_at=article.updated_at,
            ))


def seed_recommendations(db, project: Project, articles: list[Article]) -> None:
    rows = [
        ("add_faq", 90, "La page capte déjà du trafic informationnel.", "Ajouter une FAQ de 4 questions pour améliorer la couverture longue traîne."),
        ("improve_eeat", 75, "Le score EEAT est inférieur au score SEO.", "Ajouter une note auteur, des sources et un exemple client."),
        ("refresh_content", 60, "Le contenu publié commence à dater.", "Mettre à jour les données de performance et les exemples 2026."),
    ]
    for article, (rec_type, priority, reason, suggestion) in zip(articles, rows):
        exists = (
            db.query(OptimizationRecommendation)
            .filter(
                OptimizationRecommendation.project_id == project.id,
                OptimizationRecommendation.article_id == article.id,
                OptimizationRecommendation.type == rec_type,
            )
            .first()
        )
        if exists is None:
            db.add(OptimizationRecommendation(
                project_id=project.id,
                article_id=article.id,
                type=rec_type,
                priority=priority,
                reason=reason,
                suggestion=suggestion,
                status="pending",
                created_at=utc_now() - timedelta(days=priority // 20),
                updated_at=utc_now() - timedelta(days=priority // 20),
            ))


def seed_traffic(db, project: Project, articles: list[Article]) -> None:
    if db.query(TrafficEvent).filter(TrafficEvent.project_id == project.id).first() is not None:
        return

    published = [article for article in articles if article.status == "published"]
    if not published:
        return

    referrers = ["https://google.com", "https://www.linkedin.com", "https://newsletter.example.com", ""]
    countries = ["FR", "BE", "CH", "CA"]
    devices = ["desktop", "mobile", "tablet"]
    browsers = ["Chrome", "Safari", "Firefox"]
    now = utc_now()
    for day in range(28):
        for article_index, article in enumerate(published):
            views = 2 + (day % 5) + article_index
            for view in range(views):
                db.add(TrafficEvent(
                    project_id=project.id,
                    url=f"https://{DEMO_DOMAIN}/articles/{article.slug}",
                    path=f"/articles/{article.slug}",
                    referrer=referrers[(day + view + article_index) % len(referrers)] or None,
                    country=countries[(day + view) % len(countries)],
                    device=devices[(day + view + article_index) % len(devices)],
                    browser=browsers[(day + view) % len(browsers)],
                    visitor_hash=f"demo-{article_index}-{day}-{view % 7}",
                    user_agent="Mozilla/5.0 Demo",
                    created_at=now - timedelta(days=day, hours=view % 12),
                ))


def seed_notifications_and_logs(db, project: Project, user: User, articles: list[Article]) -> None:
    if db.query(Notification).filter(Notification.project_id == project.id).first() is None:
        db.add_all([
            Notification(
                project_id=project.id,
                user_id=user.id,
                type="seo",
                title="3 recommandations SEO prêtes",
                message="Des optimisations sont disponibles sur les articles publiés.",
                level="info",
                created_at=utc_now() - timedelta(days=1),
            ),
            Notification(
                project_id=project.id,
                user_id=user.id,
                type="performance",
                title="Pic de trafic détecté",
                message="Le trafic organique a progressé sur les 7 derniers jours.",
                level="success",
                created_at=utc_now() - timedelta(hours=6),
            ),
        ])

    if db.query(ArticleLog).filter(ArticleLog.project_id == project.id).first() is None:
        db.add_all([
            ArticleLog(
                project_id=project.id,
                article_id=articles[0].id if articles else None,
                level="info",
                step="seed",
                message="Données démo restaurées pour tester l'interface.",
                created_at=utc_now() - timedelta(minutes=5),
            ),
            ArticleLog(
                project_id=project.id,
                article_id=articles[-1].id if articles else None,
                level="warning",
                step="review",
                message="Un article démo nécessite une relecture éditoriale.",
                created_at=utc_now() - timedelta(minutes=2),
            ),
        ])


def build_articles(categories: dict[str, Category]) -> list[tuple[Category, dict]]:
    now = utc_now()
    base = [
        ("seo-technique", "audit-seo-technique-checklist-2026", "published", "audit SEO technique", 91, 84, 88, 81, "ready", 24, 2),
        ("ia-redaction", "brief-editorial-ia-sans-perdre-la-voix", "ready_to_publish", "brief éditorial IA", 86, 89, 85, 78, "ready", 18, 1),
        ("optimisation", "optimiser-un-article-qui-stagne", "draft", "optimisation contenu SEO", 73, 80, 76, 70, "needs_improvement", 9, 3),
        ("performance", "dashboard-editorial-kpis-seo", "writing_in_progress", "dashboard éditorial SEO", 68, 74, 71, 65, "needs_improvement", 6, 1),
        ("ia-redaction", "checklist-relecture-contenu-ia", "review_needed", "relecture contenu IA", 79, 86, 82, 74, "needs_improvement", 4, 0),
        ("seo-technique", "maillage-interne-hub-editorial", "published", "maillage interne SEO", 88, 82, 84, 76, "ready", 42, 7),
        ("optimisation", "idees-contenu-saas-b2b", "idea_priority", "idées contenu SaaS", 62, 71, 68, 64, "needs_improvement", 2, 0),
        ("performance", "mesurer-roi-contenu-organique", "idea_proposed", "ROI contenu organique", 66, 73, 69, 67, "needs_improvement", 1, 0),
    ]
    result = []
    for index, (category_slug, slug, status, keyword, seo, readability, quality, eeat, readiness, age, updated) in enumerate(base, start=1):
        title = {
            "audit-seo-technique-checklist-2026": "Audit SEO technique : la checklist 2026",
            "brief-editorial-ia-sans-perdre-la-voix": "Créer un brief éditorial IA sans perdre la voix de marque",
            "optimiser-un-article-qui-stagne": "Optimiser un article SEO qui stagne",
            "dashboard-editorial-kpis-seo": "Construire un dashboard éditorial orienté KPI SEO",
            "checklist-relecture-contenu-ia": "Checklist de relecture pour contenu assisté par IA",
            "maillage-interne-hub-editorial": "Maillage interne : bâtir un hub éditorial efficace",
            "idees-contenu-saas-b2b": "10 idées de contenu SaaS B2B à prioriser",
            "mesurer-roi-contenu-organique": "Mesurer le ROI d'une stratégie de contenu organique",
        }[slug]
        data = {
            "title": title,
            "slug": slug,
            "status": status,
            "keyword": keyword,
            "secondary_keywords": [f"{keyword} exemple", f"{keyword} checklist", "content operations"],
            "excerpt": f"Scénario de démonstration pour tester {keyword} dans Ideas Studio.",
            "angle": "Méthode pratique orientée production et pilotage éditorial.",
            "search_intent": "informational",
            "outline": [
                {"level": 2, "title": "Pourquoi ce sujet compte"},
                {"level": 2, "title": "Méthode étape par étape"},
                {"level": 2, "title": "Indicateurs à suivre"},
            ],
            "serp_summary": {
                "top_competitors": ["blog.example.com", "seo-lab.example", "contentops.example"],
                "content_gap": "Peu de contenus relient stratégie, exécution et mesure.",
            },
            "opportunity_score": float(55 + index * 5),
            "priority": 100 - index * 8,
            "meta_title": f"{title} | Ideas Studio",
            "meta_description": f"Guide démo pour {keyword}, avec priorités, score SEO et actions concrètes.",
            "cover_image_url": f"https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1200&q=80&demo={index}",
            "seo_score": float(seo),
            "readability_score": float(readability),
            "quality_score": float(quality),
            "eeat_score": float(eeat),
            "readiness_status": readiness,
            "faq": [
                {"question": "Quand utiliser ce workflow ?", "answer": "Quand un contenu doit être priorisé, produit ou optimisé."},
                {"question": "Quel KPI suivre ?", "answer": "Le trafic organique, les positions, la qualité éditoriale et les conversions."},
            ],
            "callouts": [
                {"type": "tip", "text": "Commencer par une hypothèse SEO claire avant de rédiger."},
            ],
            "internal_links": [
                {"label": "Dashboard éditorial", "url": "/projects/demo/performance"},
                {"label": "Pipeline idées", "url": "/projects/demo/ideas"},
            ],
            "external_links": [
                {"label": "Google Search Central", "url": "https://developers.google.com/search"},
            ],
            "search_console_metrics": {
                "clicks": 120 + index * 34,
                "impressions": 2400 + index * 640,
                "ctr": round(0.035 + index * 0.004, 3),
                "position": round(12.5 - index * 0.7, 1),
            },
            "content_blocks": [
                {"type": "paragraph", "text": "Bloc éditorial de démonstration."},
                {"type": "checklist", "items": ["Analyser", "Prioriser", "Publier", "Mesurer"]},
            ],
            "published_at": now - timedelta(days=age - 1) if status == "published" else None,
            "scheduled_at": now + timedelta(days=3) if status == "ready_to_publish" else None,
            "age_days": age,
            "updated_days": updated,
        }
        result.append((categories[category_slug], data))
    return result


def main() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == DEMO_USER_EMAIL).first()
        if user is None:
            raise SystemExit(
                f"User {DEMO_USER_EMAIL} not found. Create/login with this account before running the demo seed."
            )

        project = get_or_create_project(db, user)
        categories = seed_categories(db, project)
        articles = [seed_article(db, project, category, data) for category, data in build_articles(categories)]
        seed_analyses_and_related(db, project, user, articles)
        seed_recommendations(db, project, articles)
        seed_traffic(db, project, articles)
        seed_notifications_and_logs(db, project, user, articles)

        db.commit()
        print(f"Seeded demo project: {project.name} ({project.id})")
        print(f"Owner/member: {user.email} ({user.id})")
        print(f"Categories: {len(categories)}")
        print(f"Articles/ideas: {len(articles)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
