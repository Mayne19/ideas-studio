import json
import re
from html import unescape
from html.parser import HTMLParser

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.utils import generate_unique_slug, slugify
from app.models.content import Article, ArticleRevision, CalloutTemplate
from app.schemas.callout_template import CalloutTemplateCreate, CalloutTemplatePublic, CalloutTemplateUpdate

_STYLE_FIELDS = ("default_title", "color_background", "color_border", "color_text",
                  "icon", "class_name", "source", "settings_json", "style")


def to_public(template: CalloutTemplate) -> CalloutTemplatePublic:
    style = template.style or {}
    return CalloutTemplatePublic(
        id=template.id,
        project_id=template.project_id,
        slug=template.slug,
        label=template.label,
        style=style.get("style"),
        default_title=style.get("default_title"),
        color_background=style.get("color_background"),
        color_border=style.get("color_border"),
        color_text=style.get("color_text"),
        icon=style.get("icon"),
        source=style.get("source", "manual"),
        external_id=template.external_id,
        class_name=style.get("class_name"),
        created_at=template.created_at,
    )


def _unique_slug(db: Session, project_id: str, value: str, exclude_id: str | None = None) -> str:
    base = slugify(value)
    query = select(CalloutTemplate.slug).where(
        CalloutTemplate.project_id == project_id,
        CalloutTemplate.slug.like(f"{base}%"),
    )
    if exclude_id:
        query = query.where(CalloutTemplate.id != exclude_id)
    existing = {row[0] for row in db.execute(query).all()}
    return generate_unique_slug(base, existing)


def list_callout_templates(db: Session, project_id: str) -> list[CalloutTemplate]:
    return db.execute(
        select(CalloutTemplate)
        .where(CalloutTemplate.project_id == project_id)
        .order_by(CalloutTemplate.label.asc(), CalloutTemplate.created_at.asc())
    ).scalars().all()


def get_callout_template_by_id(db: Session, project_id: str, callout_id: str) -> CalloutTemplate | None:
    return db.execute(
        select(CalloutTemplate).where(
            CalloutTemplate.project_id == project_id,
            CalloutTemplate.id == callout_id,
        )
    ).scalar_one_or_none()


def create_callout_template(db: Session, data: CalloutTemplateCreate, project_id: str) -> CalloutTemplate:
    slug = data.slug or _unique_slug(db, project_id, data.label)
    style = {k: v for k in _STYLE_FIELDS if (v := getattr(data, k, None)) is not None}
    template = CalloutTemplate(
        project_id=project_id,
        slug=slug,
        label=data.label,
        style=style,
        external_id=data.external_id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_callout_template(db: Session, template: CalloutTemplate, data: CalloutTemplateUpdate) -> CalloutTemplate:
    update_dict = data.model_dump(exclude_unset=True)
    if "label" in update_dict and "slug" not in update_dict:
        update_dict["slug"] = _unique_slug(db, template.project_id, update_dict["label"], exclude_id=template.id)

    style = dict(template.style or {})
    for field in _STYLE_FIELDS:
        if field in update_dict:
            value = update_dict.pop(field)
            if value is None:
                style.pop(field, None)
            else:
                style[field] = value
    template.style = style

    if "label" in update_dict:
        template.label = update_dict.pop("label")
    if "slug" in update_dict:
        template.slug = update_dict.pop("slug")
    if "external_id" in update_dict:
        template.external_id = update_dict.pop("external_id")

    db.commit()
    db.refresh(template)
    return template


def delete_callout_template(db: Session, template: CalloutTemplate) -> None:
    if callout_template_in_use(db, template):
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail="Ce callout est encore utilise dans au moins un article.")
    db.delete(template)
    db.commit()


def callout_template_in_use(db: Session, template: CalloutTemplate) -> bool:
    rows = db.execute(
        select(ArticleRevision.callouts)
        .join(Article, Article.current_revision_id == ArticleRevision.id)
        .where(Article.project_id == template.project_id, ArticleRevision.callouts.isnot(None))
    ).scalars().all()
    for callouts in rows:
        if any(isinstance(c, dict) and c.get("template_id") == template.id for c in (callouts or [])):
            return True
    return False


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
                    "background": attrs.get("data-callout-color-background") or attrs.get("data-color-background"),
                    "border": attrs.get("data-callout-color-border") or attrs.get("data-color-border"),
                    "text": attrs.get("data-callout-color-text") or attrs.get("data-color-text"),
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


def extract_callouts_from_content(content: str | None) -> list[dict] | None:
    if not content or "data-block-type=\"callout\"" not in content:
        return None
    parser = _CalloutHTMLParser()
    parser.feed(content)
    if not parser.callouts:
        return None
    return parser.callouts
