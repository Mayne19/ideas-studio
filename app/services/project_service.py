import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import EditorialProfile, Organization, OrganizationMember, Project, ProjectCredential, ProjectMember, PublishingTarget
from app.models.reference import CredentialKind, MemberRole, MembershipStatus, ProjectStatus, set_project_status
from app.schemas.project import ProjectCreate, ProjectUpdate


def _generate_key() -> str:
    return secrets.token_urlsafe(48)


def _slugify(value: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "projet"


def _unique_slug(db: Session, model, base: str, scope_filter=None) -> str:
    candidate = base
    suffix = 1
    while True:
        query = select(model.id).where(model.slug == candidate)
        if scope_filter is not None:
            query = query.where(scope_filter)
        exists = db.execute(query).scalar_one_or_none()
        if not exists:
            return candidate
        suffix += 1
        candidate = f"{base}-{suffix}"


def get_or_create_personal_organization(db: Session, user_id: str) -> Organization:
    """Une organisation personnelle par utilisateur, créée à la demande — le
    concept d'organisation n'est pas (encore) exposé côté frontend, voir
    REPRENDRE-LA-MAIN.md §5 (owner_id -> core.organizations + project_members
    role=owner)."""
    membership = db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user_id)
    ).scalars().first()
    if membership is not None:
        return db.get(Organization, membership.organization_id)

    from app.models.core import User
    user = db.get(User, user_id)
    label = user.username or user.email.split("@")[0] if user else user_id
    slug = _unique_slug(db, Organization, _slugify(f"perso-{label}"))
    org = Organization(name=f"Espace de {label}", slug=slug)
    db.add(org)
    db.flush()
    member = OrganizationMember(organization_id=org.id, user_id=user_id, role_id=MemberRole.OWNER)
    member.status_reason_id = MembershipStatus.ACTIVE
    member.state_id = 0
    db.add(member)
    db.flush()
    return org


def _issue_credential(db: Session, project_id: str, kind: CredentialKind, label: str) -> tuple[str, ProjectCredential]:
    """Retourne (raw_token, credential) — le raw_token n'est plus jamais
    récupérable ensuite, seuls token_prefix/token_sha256 sont stockés."""
    raw = _generate_key()
    credential = ProjectCredential(
        project_id=project_id,
        kind=kind,
        label=label,
        token_prefix=raw[:8],
        token_sha256=hashlib.sha256(raw.encode("utf-8")).digest(),
    )
    db.add(credential)
    return raw, credential


def create_project(db: Session, data: ProjectCreate, owner_id: str) -> dict:
    org = get_or_create_personal_organization(db, owner_id)
    slug = _unique_slug(db, Project, _slugify(data.name), Project.organization_id == org.id)

    project = Project(
        organization_id=org.id,
        name=data.name,
        slug=slug,
        domain=data.domain,
        locale=data.locale or "fr-FR",
        timezone=data.timezone or "Europe/Paris",
    )
    set_project_status(project, ProjectStatus.NOT_CONNECTED)
    db.add(project)
    db.flush()

    profile = EditorialProfile(
        project_id=project.id,
        version=1,
        is_active=True,
        audience=data.audience,
        tone=data.tone,
        reader_level=data.reader_level,
        writing_style=data.writing_style,
        vertical=data.vertical,
        word_count_min=data.word_count_min,
        word_count_max=data.word_count_max,
        rules=data.rules or {},
        constraints=data.constraints or {},
        created_by=owner_id,
    )
    db.add(profile)

    member = ProjectMember(
        project_id=project.id,
        user_id=owner_id,
        role_id=MemberRole.OWNER,
    )
    member.status_reason_id = MembershipStatus.ACTIVE
    member.state_id = 0
    db.add(member)

    raw_tracking_key, _ = _issue_credential(db, project.id, CredentialKind.TRACKING, "default")
    db.commit()
    db.refresh(project)

    result = serialize_project(db, project)
    result["public_tracking_key"] = raw_tracking_key
    return result


def get_user_projects(db: Session, user_id: str) -> list[dict]:
    projects = db.execute(
        select(Project)
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .where(ProjectMember.user_id == user_id, ProjectMember.status_reason_id == MembershipStatus.ACTIVE)
    ).scalars().all()
    return [serialize_project(db, p) for p in projects]


def get_project_by_id(db: Session, project_id: str) -> Project | None:
    return db.get(Project, project_id)


def _primary_target(db: Session, project_id: str) -> PublishingTarget | None:
    return db.execute(
        select(PublishingTarget)
        .where(PublishingTarget.project_id == project_id)
        .order_by(PublishingTarget.is_primary.desc(), PublishingTarget.created_at.asc())
        .limit(1)
    ).scalar_one_or_none()


def serialize_project(db: Session, project: Project) -> dict:
    profile = project.active_editorial_profile
    target = _primary_target(db, project.id)
    tracking_cred = db.execute(
        select(ProjectCredential).where(
            ProjectCredential.project_id == project.id,
            ProjectCredential.kind == CredentialKind.TRACKING,
            ProjectCredential.revoked_at.is_(None),
        )
    ).scalars().first()
    owner_member = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.role_id == MemberRole.OWNER,
        )
    ).scalars().first()

    return {
        "id": project.id,
        "owner_id": owner_member.user_id if owner_member else None,
        "name": project.name,
        "domain": project.domain,
        "locale": project.locale,
        "timezone": project.timezone,
        "audience": profile.audience if profile else None,
        "tone": profile.tone if profile else None,
        "reader_level": profile.reader_level if profile else None,
        "writing_style": profile.writing_style if profile else None,
        "vertical": profile.vertical if profile else None,
        "word_count_min": profile.word_count_min if profile else None,
        "word_count_max": profile.word_count_max if profile else None,
        "status": project.status_reason_id,
        "public_tracking_key_prefix": tracking_cred.token_prefix if tracking_cred else None,
        "connected_at": None,
        "last_seen_at": None,
        "public_site_url": target.site_url if target else None,
        "revalidate_url": target.revalidate_url if target else None,
        "revalidate_configured": bool(target and target.revalidate_url),
        "last_revalidated_at": target.last_synced_at if target else None,
        "last_revalidate_status": target.last_sync_status if target else None,
        "last_revalidate_error": target.last_sync_error if target else None,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def update_project(db: Session, project: Project, data: ProjectUpdate) -> dict:
    update_data = data.model_dump(exclude_unset=True)
    site_url = update_data.pop("site_url", None)
    revalidate_url = update_data.pop("revalidate_url", None)

    profile_fields = {"audience", "tone", "reader_level", "writing_style", "vertical",
                       "word_count_min", "word_count_max", "rules", "constraints"}
    profile_updates = {k: v for k, v in update_data.items() if k in profile_fields}
    project_updates = {k: v for k, v in update_data.items() if k not in profile_fields}

    for field, value in project_updates.items():
        setattr(project, field, value)

    if profile_updates:
        profile = project.active_editorial_profile
        if profile is None:
            profile = EditorialProfile(project_id=project.id, version=1, is_active=True)
            db.add(profile)
        for field, value in profile_updates.items():
            setattr(profile, field, value)

    if site_url is not None or revalidate_url is not None:
        target = _primary_target(db, project.id)
        if target is None:
            target = PublishingTarget(project_id=project.id, site_url=site_url or "", is_primary=True)
            db.add(target)
        if site_url is not None:
            target.site_url = site_url
        if revalidate_url is not None:
            target.revalidate_url = revalidate_url

    db.commit()
    db.refresh(project)
    return serialize_project(db, project)


def delete_project(db: Session, project: Project) -> None:
    """core.projects cascade sur toutes les tables filles (content.*, ai.*,
    analytics.*, ops.*) — voir ON DELETE CASCADE dans 01-schema.sql. Une
    seule suppression suffit, plus besoin de purge manuelle table par table."""
    db.delete(project)
    db.commit()


def disconnect_project(db: Session, project: Project) -> dict:
    set_project_status(project, ProjectStatus.NOT_CONNECTED)
    db.commit()
    db.refresh(project)
    return serialize_project(db, project)
