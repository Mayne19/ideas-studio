"""Entrée et sortie du rédacteur. Les consignes de rédaction sont toutes dans
le skill .claude/skills/redaction-article/SKILL.md : ce module n'en ajoute
aucune. Il transmet le sujet (et la liste des articles du site si elle
existe), puis sépare l'article Markdown de la fiche de publication JSON."""

from __future__ import annotations

import json
import re
import unicodedata

SKILL_NAME = "redaction-article"
_FICHE_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


def build_prompt(subject: str, site_articles: list[dict] | None = None) -> str:
    lines = [f"/{SKILL_NAME}", "", f"Sujet : {subject.strip()}"]
    if site_articles:
        lines += ["", "Articles déjà publiés sur le site :"]
        for article in site_articles:
            lines.append(f"- {article.get('titre') or article.get('title', '')} | {article.get('url', '')} | "
                         f"{article.get('resume') or article.get('summary', '')}")
    return "\n".join(lines)


def split_output(text: str) -> tuple[str, dict | None, str]:
    """(article Markdown, fiche ou None, erreur de fiche). La fiche est le
    dernier bloc ```json de la réponse ; l'article est tout ce qui précède."""

    matches = list(_FICHE_RE.finditer(text or ""))
    if not matches:
        return (text or "").strip(), None, "aucun bloc ```json trouvé après l'article"
    last = matches[-1]
    article = (text[:last.start()]).strip()
    article = re.sub(r"^```(?:markdown|md)?\s*\n(.*)\n```$", r"\1", article, flags=re.DOTALL).strip()
    try:
        fiche = json.loads(last.group(1))
    except json.JSONDecodeError as exc:
        return article, None, f"JSON invalide : {exc}"
    if not isinstance(fiche, dict):
        return article, None, "la fiche n'est pas un objet JSON"
    return article, fiche, ""


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")[:80] or "article"


def article_slug(subject: str, fiche: dict | None) -> str:
    slug = str((fiche or {}).get("slug") or "")
    return slug if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) else slugify(subject)
