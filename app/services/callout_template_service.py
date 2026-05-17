import json
import re
from html import unescape
from html.parser import HTMLParser

from sqlalchemy.orm import Session

from app.core.utils import generate_unique_slug, slugify
from app.models.article import Article
from app.models.project_callout_template import ProjectCalloutTemplate
from app.schemas.callout_template import CalloutTemplateCreate, CalloutTemplateUpdate


def _unique_slug(db: Session, project_id: str, value: str, exclude_id: str | None = None) -> str:
    base = slugify(value)
    q = db.query(ProjectCalloutTemplate.slug).filter(
        ProjectCalloutTemplate.project_id == project_id,
        ProjectCalloutTemplate.slug.like(f"{base}%"),
    )
    if exclude_id:
        q = q.filter(ProjectCalloutTemplate.id != exclude_id)
    existing = {row[0] for row in q.all()}
    return generate_unique_slug(base, existing)


def list_callout_templates(db: Session, project_id: str) -> list[ProjectCalloutTemplate]:
    return (
        db.query(ProjectCalloutTemplate)
        .filter(ProjectCalloutTemplate.project_id == project_id)
        .order_by(ProjectCalloutTemplate.label.asc(), ProjectCalloutTemplate.created_at.asc())
        .all()
    )


def get_callout_template_by_id(db: Session, project_id: str, callout_id: str) -> ProjectCalloutTemplate | None:
    return (
        db.query(ProjectCalloutTemplate)
        .filter(
            ProjectCalloutTemplate.project_id == project_id,
            ProjectCalloutTemplate.id == callout_id,
        )
        .first()
    )


def create_callout_template(db: Session, data: CalloutTemplateCreate, project_id: str) -> ProjectCalloutTemplate:
    slug = data.slug or _unique_slug(db, project_id, data.label)
    template = ProjectCalloutTemplate(
        project_id=project_id,
        slug=slug,
        label=data.label,
        style=data.style,
        default_title=data.default_title,
        color_background=data.color_background,
        color_border=data.color_border,
        color_text=data.color_text,
        icon=data.icon,
        source=data.source,
        external_id=data.external_id,
        class_name=data.class_name,
        settings_json=data.settings_json,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_callout_template(db: Session, template: ProjectCalloutTemplate, data: CalloutTemplateUpdate) -> ProjectCalloutTemplate:
    update_dict = data.model_dump(exclude_unset=True)
    if "label" in update_dict and "slug" not in update_dict:
        update_dict["slug"] = _unique_slug(db, template.project_id, update_dict["label"], exclude_id=template.id)
    for field, value in update_dict.items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


def delete_callout_template(db: Session, template: ProjectCalloutTemplate) -> None:
    if callout_template_in_use(db, template):
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail="Ce callout est encore utilise dans au moins un article.")
    db.delete(template)
    db.commit()


def callout_template_in_use(db: Session, template: ProjectCalloutTemplate) -> bool:
    return db.query(Article).filter(
        Article.project_id == template.project_id,
        Article.callouts_json.isnot(None),
        Article.callouts_json.contains(template.id),
    ).first() is not None


class _CalloutHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.callouts: list[dict] = []
        self._stack: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value for key, value in attrs}
        if tag == "div" and attr_map.get("data-block-type") == "callout":
            self._stack.append({
                "attrs": attr_map,
                "depth": 1,
                "body_parts": [],
                "plain_parts": [],
                "capture_depth": 0,
            })
            return

        if not self._stack:
            return

        current = self._stack[-1]
        current["depth"] += 1

        class_name = attr_map.get("class", "")
        if "callout-body" in class_name.split():
            current["capture_depth"] = current["depth"]
            return

        if current["capture_depth"]:
            rendered_attrs = "".join(
                f' {name}="{value}"' if value is not None else f" {name}"
                for name, value in attrs
            )
            current["body_parts"].append(f"<{tag}{rendered_attrs}>")
            if tag in {"p", "div", "br", "li", "ul", "ol"}:
                current["plain_parts"].append(" ")

    def handle_endtag(self, tag: str) -> None:
        if not self._stack:
            return
        current = self._stack[-1]
        if current["capture_depth"] and current["capture_depth"] != current["depth"]:
            current["body_parts"].append(f"</{tag}>")
        if current["capture_depth"] == current["depth"]:
            current["capture_depth"] = 0

        current["depth"] -= 1
        if current["depth"] <= 0:
            attrs = current["attrs"]
            body_html = "".join(current["body_parts"]).strip()
            body_text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", body_html))).strip()
            self.callouts.append({
                "template_id": attrs.get("data-template-id"),
                "template_key": attrs.get("data-template-key"),
                "label": attrs.get("data-callout-label"),
                "title": attrs.get("data-callout-title"),
                "style": attrs.get("data-callout-style"),
                "icon": attrs.get("data-callout-icon"),
                "class_name": attrs.get("data-callout-class-name"),
                "source": attrs.get("data-callout-source"),
                "colors": {
                    "background": attrs.get("data-color-background"),
                    "border": attrs.get("data-color-border"),
                    "text": attrs.get("data-color-text"),
                },
                "body_html": body_html or None,
                "body_text": body_text or None,
            })
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if not self._stack:
            return
        current = self._stack[-1]
        if current["capture_depth"]:
            current["body_parts"].append(data)
            current["plain_parts"].append(data)


def extract_callouts_from_content(content: str | None) -> str | None:
    if not content or "data-block-type=\"callout\"" not in content:
        return None
    parser = _CalloutHTMLParser()
    parser.feed(content)
    if not parser.callouts:
        return None
    return json.dumps(parser.callouts)
