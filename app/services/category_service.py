from sqlalchemy.orm import Session
from app.models.category import Category
from app.models.article import Article
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.core.utils import slugify, generate_unique_slug


def _unique_slug(db: Session, project_id: str, name: str, exclude_id: str | None = None) -> str:
    base = slugify(name)
    q = db.query(Category.slug).filter(
        Category.project_id == project_id,
        Category.slug.like(f"{base}%"),
    )
    if exclude_id:
        q = q.filter(Category.id != exclude_id)
    existing = {row[0] for row in q.all()}
    return generate_unique_slug(base, existing)


def get_categories_for_project(db: Session, project_id: str) -> list[Category]:
    return db.query(Category).filter(Category.project_id == project_id).all()


def get_category_by_id(db: Session, category_id: str) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


def create_category(db: Session, data: CategoryCreate, project_id: str) -> Category:
    slug = data.slug or _unique_slug(db, project_id, data.name)
    category = Category(
        project_id=project_id,
        name=data.name,
        slug=slug,
        description=data.description,
        priority=data.priority,
        target_frequency=data.target_frequency,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category: Category, data: CategoryUpdate) -> Category:
    update_dict = data.model_dump(exclude_unset=True)
    if "name" in update_dict and "slug" not in update_dict:
        update_dict["slug"] = _unique_slug(db, category.project_id, update_dict["name"], exclude_id=category.id)
    for field, value in update_dict.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    has_articles = db.query(Article).filter(Article.category_id == category.id).first() is not None
    if has_articles:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Cannot delete category: articles are linked to it")
    db.delete(category)
    db.commit()
