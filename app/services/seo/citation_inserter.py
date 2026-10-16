"""Insertion déterministe des citations externes et des liens internes.

Demander au rédacteur de placer lui-même les liens ne marchait pas : aucun
lien n'était inséré alors que le plan contenait des sources fortes
(francenum.gouv.fr, fr.wikipedia.org, pages tarifs officielles). Ici un petit
appel choisit, pour chaque source candidate, la phrase exacte de l'article
qu'elle soutient et un groupe de mots naturel de cette phrase ; le code pose
ensuite le <a href> lui-même.

Règles :
- 1 à 3 citations externes au total (liens déjà présents compris), seulement
  vers des sources fiables accompagnées d'un extrait ; une source sans phrase
  qui lui corresponde est ignorée (jamais de lien forcé) ;
- rel="noopener" target="_blank", sans nofollow pour les sources de
  référence (gouv, Wikipédia, sites officiels) ; nofollow pour les autres ;
- jusqu'à 2 liens internes, même mécanisme ;
- jamais dans un titre, jamais dans un lien existant, une phrase ne porte
  qu'un lien.
"""
from __future__ import annotations

import html as html_lib
import logging
import re
from typing import Callable
from urllib.parse import urlparse

from app.services.seo.html_text_ops import (
    extract_json_object, find_sentence_span, inside_link, split_units, text_blocks, unit_heading,
)
from app.services.seo.section_writer import lost_h2s
from app.services.seo.source_quality_service import classify_source_quality

logger = logging.getLogger(__name__)

CallFn = Callable[[str, str, float], str]

MIN_EXTERNAL = 1
MAX_EXTERNAL = 3
MAX_INTERNAL = 2
_HREF_RE = re.compile(r"""<a\b[^>]*href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_REFERENCE_SUFFIXES = (".gouv.fr", ".gov", ".gouv", ".europa.eu", ".edu")


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def is_official_host(url: str, keyword: str) -> bool:
    """Site officiel d'une entité du mot-clé (webflow.com pour « webflow ou
    wordpress ») : sa page tarifs est une source primaire."""
    parts = _host(url).split(".")
    if len(parts) < 2:
        return False
    tokens = {t for t in re.split(r"[^\w]+", (keyword or "").lower()) if len(t) >= 4}
    return parts[-2] in tokens


def is_reference_source(url: str, keyword: str = "") -> bool:
    host = _host(url)
    if not host:
        return False
    return (
        classify_source_quality(url) == "strong"
        or host.endswith(_REFERENCE_SUFFIXES)
        or host == "wikipedia.org" or host.endswith(".wikipedia.org")
        or is_official_host(url, keyword)
    )


def eligible_external_sources(links: list[dict], keyword: str = "") -> list[dict]:
    """Sources fiables avec extrait, dans l'ordre du plan (déjà classé)."""
    eligible = []
    for link in links or []:
        if not isinstance(link, dict):
            continue
        url = str(link.get("url") or "").strip()
        excerpt = str(link.get("excerpt") or "").strip()
        if not url.startswith("http") or not excerpt:
            continue
        if link.get("domain_tier") == "weak":
            continue
        if not (is_reference_source(url, keyword) or link.get("source_reliability") == "high"):
            continue
        eligible.append(link)
    return eligible


def existing_hrefs(content: str) -> list[str]:
    return [m.group(1).strip() for m in _HREF_RE.finditer(content or "")]


def _external_count(content: str) -> int:
    # Les crédits photo ne sont pas des citations.
    return sum(1 for href in existing_hrefs(content)
               if href.startswith("http") and not _host(href).endswith("unsplash.com"))


def _article_digest(content: str) -> str:
    lines: list[str] = []
    for index, unit in enumerate(split_units(content)):
        blocks = text_blocks(unit)
        if not blocks:
            continue
        lines.append("## " + ("INTRODUCTION" if index == 0 else unit_heading(unit)))
        lines.extend(f"- {b}" for b in blocks)
    return "\n".join(lines)


def build_citation_prompt(content: str, external: list[dict], internal: list[dict]) -> str:
    parts = [
        "Tu places des liens dans un article déjà rédigé. Pour chaque source ci-dessous, trouve dans "
        "l'article UNE phrase dont l'affirmation est directement soutenue par l'extrait de la source "
        "(ou, pour un article interne, une phrase qui parle de son sujet).",
        "Pour chaque lien retenu, donne :",
        "- \"sentence\" : la phrase copiée mot pour mot depuis l'article ;",
        "- \"anchor\" : un groupe de 2 à 6 mots copié tel quel dans cette phrase, qui décrit le contenu "
        "de la source (jamais « cliquez ici », « source », « ici » ni une URL).",
        "Si aucune phrase ne correspond vraiment à une source, ne la mets pas. Une phrase différente par lien. "
        "N'utilise jamais un titre de section.",
        "",
        "Réponds UNIQUEMENT en JSON : {\"links\": [{\"id\": \"E1\", \"sentence\": \"...\", \"anchor\": \"...\"}]}",
        "",
    ]
    if external:
        parts.append("Sources externes :")
        for i, link in enumerate(external, 1):
            title = str(link.get("anchor_text") or "").strip()
            parts.append(f"- E{i} ({_host(link['url'])}) {title} : « {str(link.get('excerpt') or '').strip()} »")
    if internal:
        parts.append("Articles internes du site :")
        for i, link in enumerate(internal, 1):
            title = str(link.get("anchor_text") or "").strip()
            context = link.get("context") or {}
            excerpt = str(context.get("target_excerpt") or "").strip() if isinstance(context, dict) else ""
            parts.append(f"- I{i} {title}" + (f" : « {excerpt} »" if excerpt else ""))
    parts += ["", "Article :", _article_digest(content)]
    return "\n".join(parts)


def _anchor_html(url: str, anchor_html: str, external: bool, follow: bool) -> str:
    href = html_lib.escape(url, quote=True)
    if not external:
        return f'<a href="{href}">{anchor_html}</a>'
    rel = "noopener" if follow else "noopener nofollow"
    return f'<a href="{href}" target="_blank" rel="{rel}">{anchor_html}</a>'


_EXTERNAL_A_RE = re.compile(r"""<a\b([^>]*?)href\s*=\s*(["'])(https?://[^"']+)\2([^>]*)>""", re.IGNORECASE)


def normalize_external_rels(content: str, keyword: str = "") -> str:
    """Liens externes posés par le rédacteur : même règle rel que ceux posés
    ici (follow vers les sources de référence, nofollow sinon), et toujours
    target=_blank. Les crédits photo (unsplash.com) ne sont pas touchés."""
    def _fix(match: re.Match) -> str:
        url = match.group(3)
        if _host(url).endswith("unsplash.com"):
            return match.group(0)
        attrs = re.sub(r"""\s(?:rel|target)\s*=\s*(["'])[^"']*\1""", "", match.group(1) + " " + match.group(4))
        attrs = " ".join(attrs.split())
        rel = "noopener" if is_reference_source(url, keyword) else "noopener nofollow"
        href = html_lib.escape(html_lib.unescape(url), quote=True)
        return f'<a {attrs + " " if attrs else ""}href="{href}" target="_blank" rel="{rel}">'
    return _EXTERNAL_A_RE.sub(_fix, content or "")


_FULL_EXTERNAL_A_RE = re.compile(r"""<a\b[^>]*href\s*=\s*(["'])(https?://[^"']+)\1[^>]*>(.*?)</a>""",
                                 re.IGNORECASE | re.DOTALL)


def dedupe_external_links(content: str) -> str:
    """Une URL externe n'est liée qu'une fois : les liens suivants vers la
    même page sont retirés (le texte d'ancre reste)."""
    seen: set[str] = set()

    def _keep_first(match: re.Match) -> str:
        url = html_lib.unescape(match.group(2)).rstrip("/")
        if _host(url).endswith("unsplash.com"):
            return match.group(0)
        if url in seen:
            return match.group(3)
        seen.add(url)
        return match.group(0)
    return _FULL_EXTERNAL_A_RE.sub(_keep_first, content or "")


def insert_link(content: str, sentence: str, anchor: str, url: str, *, external: bool, follow: bool) -> tuple[str, str | None]:
    """Pose le lien sur `anchor` dans `sentence`. Retourne (contenu, raison
    du refus ou None)."""
    anchor = (anchor or "").strip().strip(".,;:!?«»\"' ")
    words = anchor.split()
    if not 1 <= len(words) <= 8:
        return content, "ancre absente ou trop longue"
    if anchor.lower() in {"ici", "cliquez ici", "source", "ce lien", "en savoir plus"} or "http" in anchor.lower():
        return content, "ancre non descriptive"
    span = find_sentence_span(content, sentence)
    if span is None:
        return content, "phrase introuvable, ambiguë ou dans un titre"
    start, end = span
    fragment = content[start:end]
    if re.search(r"<a\b", fragment, re.IGNORECASE) or inside_link(content, start):
        return content, "la phrase porte déjà un lien"
    pattern = re.compile(
        r"(?<![\w])" + r"\s+".join(
            "(?:" + "|".join(sorted({re.escape(w), re.escape(html_lib.escape(w, quote=False))})) + ")" for w in words
        ) + r"(?![\w])",
        re.IGNORECASE,
    )
    match = pattern.search(fragment)
    if match is None:
        return content, "ancre absente de la phrase"
    a_start, a_end = start + match.start(), start + match.end()
    linked = _anchor_html(url, content[a_start:a_end], external, follow)
    return content[:a_start] + linked + content[a_end:], None


def _apply_picks(content: str, picks: list, candidates: dict[str, tuple[dict, bool]], keyword: str,
                 budget: dict[str, int], report: dict, used_sentences: set[str]) -> str:
    for pick in picks:
        if not isinstance(pick, dict):
            continue
        cid = str(pick.get("id") or "").strip().upper()
        sentence = str(pick.get("sentence") or "").strip()
        anchor = str(pick.get("anchor") or "").strip()
        if cid not in candidates:
            continue
        link, external = candidates[cid]
        url = link["url"] if external else link["target_url"]
        kind = "external" if external else "internal"
        entry = {"id": cid, "url": url, "sentence": sentence, "anchor": anchor}
        if budget[kind] <= 0:
            report["skipped"].append({**entry, "reason": "plafond de liens atteint"})
            continue
        if url in existing_hrefs(content):
            report["skipped"].append({**entry, "reason": "lien déjà présent"})
            continue
        if sentence.lower() in used_sentences:
            report["skipped"].append({**entry, "reason": "phrase déjà liée"})
            continue
        follow = is_reference_source(url, keyword) if external else True
        candidate, reason = insert_link(content, sentence, anchor, url, external=external, follow=follow)
        if reason is None and lost_h2s(content, candidate):
            reason = "insertion qui altère un titre"
        if reason:
            report["skipped"].append({**entry, "reason": reason})
            continue
        content = candidate
        budget[kind] -= 1
        used_sentences.add(sentence.lower())
        report["inserted"].append({**entry, "type": kind, "rel": "" if not external else ("noopener" if follow else "noopener nofollow")})
        del candidates[cid]
    return content


def insert_citations(
    content: str,
    call_fn: CallFn,
    external_links: list[dict] | None,
    internal_links: list[dict] | None,
    *,
    keyword: str = "",
    fatal_exceptions: tuple[type[BaseException], ...] = (),
) -> tuple[str, dict]:
    content = dedupe_external_links(normalize_external_rels(content, keyword))
    report: dict = {"inserted": [], "skipped": [], "candidates_external": 0, "candidates_internal": 0,
                    "existing_external": _external_count(content), "error": None}
    present = set(existing_hrefs(content))
    external = [link for link in eligible_external_sources(external_links or [], keyword) if link["url"] not in present][:MAX_EXTERNAL]
    internal = [
        link for link in (internal_links or [])
        if isinstance(link, dict) and str(link.get("target_url") or "").startswith("/")
        and link["target_url"] not in present
    ][:MAX_INTERNAL]
    budget = {"external": max(0, MAX_EXTERNAL - report["existing_external"]), "internal": MAX_INTERNAL}
    if budget["external"] == 0:
        external = []
    report["candidates_external"] = len(external)
    report["candidates_internal"] = len(internal)
    if not external and not internal:
        return content, report

    candidates: dict[str, tuple[dict, bool]] = {f"E{i}": (link, True) for i, link in enumerate(external, 1)}
    candidates.update({f"I{i}": (link, False) for i, link in enumerate(internal, 1)})
    used_sentences: set[str] = set()

    for attempt in (1, 2):
        ext_pending = [candidates[k][0] for k in candidates if k.startswith("E")]
        int_pending = [candidates[k][0] for k in candidates if k.startswith("I")]
        if attempt == 2:
            # Seconde chance uniquement pour atteindre le minimum d'une citation
            # externe, sur les sources restantes ; les liens internes ne sont
            # pas redemandés.
            if report["existing_external"] + sum(1 for i in report["inserted"] if i["type"] == "external") >= MIN_EXTERNAL:
                break
            if not ext_pending:
                break
            int_pending = []
        # Les identifiants doivent rester stables entre la liste du prompt et la réponse.
        prompt_ids = {f"E{i}": k for i, k in enumerate([k for k in candidates if k.startswith("E")], 1)}
        if int_pending:
            prompt_ids.update({f"I{i}": k for i, k in enumerate([k for k in candidates if k.startswith("I")], 1)})
        try:
            raw = call_fn(build_citation_prompt(content, ext_pending, int_pending), f"CitationPlacement#{attempt}", 0.2)
        except fatal_exceptions:
            raise
        except Exception as exc:
            logger.warning("citations: appel en échec : %s", exc)
            report["error"] = str(exc)[:300]
            continue
        data = extract_json_object(raw)
        if data is None or not isinstance(data.get("links"), list):
            report["error"] = "réponse JSON invalide"
            continue
        picks = []
        for pick in data["links"]:
            if isinstance(pick, dict) and str(pick.get("id") or "").strip().upper() in prompt_ids:
                picks.append({**pick, "id": prompt_ids[str(pick["id"]).strip().upper()]})
        content = _apply_picks(content, picks, candidates, keyword, budget, report, used_sentences)
    return content, report
