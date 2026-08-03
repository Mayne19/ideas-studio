from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.content import Article, Category
from app.schemas.category import CategoryCreate, CategoryPublic, CategoryUpdate
from app.core.utils import slugify, generate_unique_slug

_OVERRIDE_FIELDS = ("editorial_goal", "target_audience", "internal_notes", "word_count_min", "word_count_max")


def _unique_slug(db: Session, project_id: str, name: str, exclude_id: str | None = None) -> str:
    base = slugify(name)
    query = select(Category.slug).where(
        Category.project_id == project_id,
        Category.slug.like(f"{base}%"),
    )
    if exclude_id:
        query = query.where(Category.id != exclude_id)
    existing = {row[0] for row in db.execute(query).all()}
    return generate_unique_slug(base, existing)


def to_public(category: Category) -> CategoryPublic:
    overrides = category.overrides or {}
    return CategoryPublic(
        id=category.id,
        project_id=category.project_id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        color=category.color,
        priority_score=float(category.priority_score) if category.priority_score is not None else None,
        monthly_target=category.monthly_target,
        is_pipeline_enabled=category.is_pipeline_enabled,
        editorial_goal=overrides.get("editorial_goal"),
        target_audience=overrides.get("target_audience"),
        internal_notes=overrides.get("internal_notes"),
        word_count_min=overrides.get("word_count_min"),
        word_count_max=overrides.get("word_count_max"),
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


def get_categories_for_project(db: Session, project_id: str) -> list[Category]:
    return db.execute(select(Category).where(Category.project_id == project_id)).scalars().all()


def get_category_by_id(db: Session, category_id: str) -> Category | None:
    return db.get(Category, category_id)


def create_category(db: Session, data: CategoryCreate, project_id: str) -> Category:
    slug = data.slug or _unique_slug(db, project_id, data.name)
    overrides = {k: v for k in _OVERRIDE_FIELDS if (v := getattr(data, k)) is not None}
    category = Category(
        project_id=project_id,
        name=data.name,
        slug=slug,
        description=data.description,
        color=data.color,
        priority_score=data.priority_score,
        monthly_target=data.monthly_target,
        is_pipeline_enabled=data.is_pipeline_enabled,
        overrides=overrides,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category: Category, data: CategoryUpdate) -> Category:
    update_dict = data.model_dump(exclude_unset=True)
    if "name" in update_dict and "slug" not in update_dict:
        update_dict["slug"] = _unique_slug(db, category.project_id, update_dict["name"], exclude_id=category.id)

    overrides = dict(category.overrides or {})
    for field in _OVERRIDE_FIELDS:
        if field in update_dict:
            value = update_dict.pop(field)
            if value is None:
                overrides.pop(field, None)
            else:
                overrides[field] = value
    category.overrides = overrides

    for field, value in update_dict.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    has_articles = db.execute(
        select(Article.id).where(Article.category_id == category.id).limit(1)
    ).scalar_one_or_none() is not None
    if has_articles:
        raise HTTPException(status_code=409, detail="Cannot delete category: articles are linked to it")
    db.delete(category)
    db.commit()
