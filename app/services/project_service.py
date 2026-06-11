import secrets
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.schemas.project import ProjectCreate, ProjectUpdate


def _generate_key() -> str:
    return secrets.token_urlsafe(48)


def create_project(db: Session, data: ProjectCreate, owner_id: str) -> Project:
    project = Project(
        owner_id=owner_id,
        name=data.name,
        domain=data.domain,
        language=data.language,
        country_target=data.country_target,
        audience=data.audience,
        tone=data.tone,
        public_tracking_key=_generate_key(),
        secret_api_key=_generate_key(),
        status="not_connected",
    )
    db.add(project)
    db.flush()

    member = ProjectMember(
        project_id=project.id,
        user_id=owner_id,
        role="owner",
        status="active",
    )
    db.add(member)
    db.commit()
    db.refresh(project)
    return project


def get_user_projects(db: Session, user_id: str) -> list[Project]:
    return (
        db.query(Project)
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .filter(ProjectMember.user_id == user_id, ProjectMember.status == "active")
        .all()
    )


def get_project_by_id(db: Session, project_id: str) -> Project | None:
    return db.query(Project).filter(Project.id == project_id).first()


def update_project(db: Session, project: Project, data: ProjectUpdate) -> Project:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    """Delete a project and all related data."""
    from app.models.article import Article
    from app.models.article_version import ArticleVersion
    from app.models.article_log import ArticleLog
    from app.models.category import Category
    from app.models.media_asset import MediaAsset
    from app.models.notification import Notification
    from app.models.optimization_recommendation import OptimizationRecommendation
    from app.models.project_member import ProjectMember
    from app.models.project_callout_template import ProjectCalloutTemplate
    from app.models.pipeline import ProjectPipeline
    from app.models.pipeline_log import PipelineLog
    from app.models.invitation import Invitation
    from app.models.traffic_event import TrafficEvent
    from app.models.seo_analysis import SeoAnalysis
    from app.models.article_comment import ArticleComment
    from app.models.activity_log import ActivityLog
    from app.models.webhook import Webhook
    from app.models.kanban_column import KanbanColumn

    article_ids = [a.id for a in db.query(Article).filter(Article.project_id == project.id).all()]
    db.query(ArticleVersion).filter(ArticleVersion.project_id == project.id).delete()
    db.query(ArticleLog).filter(ArticleLog.project_id == project.id).delete()
    db.query(ArticleComment).filter(ArticleComment.project_id == project.id).delete()
    for aid in article_ids:
        db.query(SeoAnalysis).filter(SeoAnalysis.article_id == aid).delete()
    db.query(OptimizationRecommendation).filter(OptimizationRecommendation.project_id == project.id).delete()
    db.query(Article).filter(Article.project_id == project.id).delete()
    db.query(MediaAsset).filter(MediaAsset.project_id == project.id).delete()
    db.query(Category).filter(Category.project_id == project.id).delete()
    db.query(Notification).filter(Notification.project_id == project.id).delete()
    db.query(ProjectCalloutTemplate).filter(ProjectCalloutTemplate.project_id == project.id).delete()
    db.query(ProjectMember).filter(ProjectMember.project_id == project.id).delete()
    db.query(ProjectPipeline).filter(ProjectPipeline.project_id == project.id).delete()
    db.query(PipelineLog).filter(PipelineLog.project_id == project.id).delete()
    db.query(Invitation).filter(Invitation.project_id == project.id).delete()
    db.query(TrafficEvent).filter(TrafficEvent.project_id == project.id).delete()
    db.query(ActivityLog).filter(ActivityLog.project_id == project.id).delete()
    db.query(Webhook).filter(Webhook.project_id == project.id).delete()
    db.query(KanbanColumn).filter(KanbanColumn.project_id == project.id).delete()
    db.delete(project)
    db.commit()


def disconnect_project(db: Session, project: Project) -> Project:
    project.status = "not_connected"
    project.connected_at = None
    project.last_seen_at = None
    db.commit()
    db.refresh(project)
    return project
