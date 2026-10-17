"""Mode de génération « agent » de l'orchestrateur.

L'agent rédacteur unique (agent_writer) remplace la recherche, le plan, la
rédaction, la relecture et la révision. L'orchestrateur garde : contexte
projet, cannibalisation (déjà faits avant l'appel), création de l'article,
contrôles par le code avec deux tours de correction au maximum dans la même
conversation, données structurées, checklist SEO, juge éditorial (score) et
rapport de génération.
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from app.core.utils import calculate_reading_time_minutes, calculate_word_count
from app.models.content import Article
from app.models.reference import ArticleStatus, RunStatus, WorkflowPhase, set_article_status, set_run_status

if TYPE_CHECKING:  # pragma: no cover
    from app.services.seo.seo_generation_orchestrator import SEOGenerationOrchestrator

MAX_FAQ, MIN_FAQ = 5, 3
logger = logging.getLogger(__name__)


def published_articles(db, project) -> list[dict]:
    """Articles publiés du projet (titre et URL) pour les liens internes."""
    from sqlalchemy import select

    from app.models.content import ArticleRevision

    if project is None or not project.domain:
        return []
    base = project.domain if project.domain.startswith("http") else f"https://{project.domain}"
    rows = db.execute(
        select(Article.slug, ArticleRevision.title)
        .join(ArticleRevision, ArticleRevision.id == Article.current_revision_id)
        .where(Article.project_id == project.id, Article.published_at.is_not(None))
        .order_by(Article.published_at.desc())
        .limit(60)
    ).all()
    return [{"title": title, "url": f"{base.rstrip('/')}/blog/{slug}"} for slug, title in rows if slug and title]


def assembly_errors(data: dict) -> list[str]:
    """Contrôle d'assemblage : FAQ présente et hors du corps, conclusion en
    dernier H2 (avant la FAQ), aucun bloc répété."""
    from app.services.seo.structure_fixer import remove_body_faq, remove_duplicates

    errors: list[str] = []
    content = data.get("content_html") or ""
    faq = data.get("faq") or []
    if not (MIN_FAQ <= len(faq) <= MAX_FAQ):
        errors.append(f"La FAQ doit contenir 3 à 5 questions (actuellement {len(faq)}).")
    if remove_body_faq(content) != content:
        errors.append("Le corps contient une section FAQ : la FAQ va uniquement dans le champ « faq », après la conclusion.")
    if remove_duplicates(content) != content:
        errors.append("Un titre ou un paragraphe est répété dans l'article : supprime la répétition.")
    if not re.search(r"<h2\b", content, re.IGNORECASE):
        errors.append("L'article n'a aucun H2 ; la conclusion doit être un H2 placé en dernier.")
    return errors


# Seules ces règles déclenchent un tour de correction payant (consigne du
# 2026-10-17) : les autres (longueur des paragraphes, variation…) restent
# informatives, sinon les corrections abîment l'article.
CORRECTION_RULES = ("no_em_dash", "banned_vocabulary", "verbal_tics", "single_h1", "heading_hierarchy")
INTRO_MAX_WORDS, INTRO_MAX_SHARE = 150, 0.15


def structure_errors(content: str, title: str) -> list[str]:
    from app.services.seo.html_text_ops import html_to_text, split_units
    from app.services.seo.structure_validator import validate_structure

    report = validate_structure(content, title)
    errors = []
    for rule in report.get("rules") or []:
        if rule.get("passed") or rule.get("rule") not in CORRECTION_RULES:
            continue
        for v in (rule.get("violations") or [])[:3]:
            where = f" (section « {v['section']} »)" if v.get("section") else ""
            errors.append(f"{rule['label']}{where} : {v.get('detail', '')}")
    intro_words = len(html_to_text(split_units(content)[0]).split()) if content else 0
    total_words = len(html_to_text(content).split()) or 1
    if intro_words > INTRO_MAX_WORDS and intro_words / total_words > INTRO_MAX_SHARE:
        errors.append(f"Introduction trop longue : {intro_words} mots (au plus {INTRO_MAX_WORDS} mots ou "
                      f"{int(INTRO_MAX_SHARE * 100)} % de l'article).")
    return errors


def link_errors(content: str) -> list[str]:
    """Une même URL au plus une fois dans le corps."""
    counts: dict[str, int] = {}
    for url in re.findall(r"""<a\b[^>]*href\s*=\s*["']([^"']+)["']""", content or "", re.IGNORECASE):
        key = url.split("#")[0].rstrip("/")
        counts[key] = counts.get(key, 0) + 1
    return [f"L'URL {url} est liée {n} fois : garde un seul lien, au premier endroit où la source sert."
            for url, n in counts.items() if n > 1]


_STEP_HEADING_RE = re.compile(r"\b(étapes?|gestes?|méthode|marche à suivre|procédure)\b", re.IGNORECASE)
_COUNT_WORDS = {"deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10}


def html_render_errors(content: str) -> list[str]:
    """Tableaux avec en-tête ; méthode à étapes en liste numérotée."""
    from app.services.seo.html_text_ops import html_to_text, split_units, unit_heading

    errors = []
    for table in re.findall(r"<table\b.*?</table>", content or "", re.IGNORECASE | re.DOTALL):
        if "<th" not in table.lower():
            errors.append("Un tableau n'a pas de ligne d'en-tête (<thead> avec <th>).")
        rows = re.findall(r"<tr\b.*?</tr>", table, re.IGNORECASE | re.DOTALL)
        widths = {len(re.findall(r"<t[hd]\b", r, re.IGNORECASE)) for r in rows}
        if len(widths) > 1:
            errors.append("Un tableau a des lignes de longueurs différentes : chaque ligne doit avoir le même nombre de cellules.")
    for unit in split_units(content or "")[1:]:
        if _STEP_HEADING_RE.search(unit_heading(unit)) and "<ul" in unit.lower() and "<ol" not in unit.lower():
            errors.append(f"La section « {unit_heading(unit)} » présente des étapes en liste à puces : utilise une liste numérotée <ol>.")
    return errors


def announced_count_errors(content: str) -> list[str]:
    """« Les quatre gestes » dans un titre : la section doit en contenir
    exactement quatre (éléments de liste ou H3)."""
    from app.services.seo.html_text_ops import split_units, unit_heading

    errors = []
    for unit in split_units(content or "")[1:]:
        heading = unit_heading(unit)
        m = re.search(r"\b(" + "|".join(_COUNT_WORDS) + r"|\d{1,2})\s+(?:[a-zéèêàâîïôûç]+\s+)?(erreurs|étapes|gestes|"
                      r"questions|conseils|astuces|raisons|signes|règles|critères|outils|méthodes|solutions)",
                      heading.lower())
        if not m:
            continue
        announced = int(m.group(1)) if m.group(1).isdigit() else _COUNT_WORDS[m.group(1)]
        body = re.sub(r"^\s*<h2\b[^>]*>.*?</h2>", "", unit, flags=re.IGNORECASE | re.DOTALL)
        h3 = len(re.findall(r"<h3\b", body, re.IGNORECASE))
        items = max((len(re.findall(r"<li\b", lst, re.IGNORECASE))
                     for lst in re.findall(r"<[ou]l\b.*?</[ou]l>", body, re.IGNORECASE | re.DOTALL)), default=0)
        if announced not in (h3, items):
            errors.append(f"Le titre « {heading} » annonce {announced} {m.group(2)}, la section en contient "
                          f"{h3 or items}.")
    return errors


def consistency_errors(content: str, call_fn) -> list[str]:
    """Une même chose avec deux valeurs différentes (détection seule)."""
    from app.services.seo.consistency_checker import build_consistency_prompt
    from app.services.seo.html_text_ops import extract_json_object

    try:
        data = extract_json_object(call_fn(build_consistency_prompt(content), "AgentConsistencyCheck", 0.1)) or {}
    except Exception:
        return []
    return [
        f"Contradiction : « {i.get('sentence', '')} » contre « {i.get('related_sentence', '')} » ({i.get('reason', '')})"
        for i in data.get("issues") or []
        if isinstance(i, dict) and i.get("type") == "contradiction"
    ][:5]


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _url_key(url: str) -> str:
    """Normalise une URL pour comparer facts.source_url et sources.url."""
    try:
        parsed = urlsplit((url or "").strip())
        if not parsed.scheme or not parsed.netloc:
            return ""
        host = (parsed.hostname or "").lower().removeprefix("www.")
        port = parsed.port
        netloc = host if not port or port in (80, 443) else f"{host}:{port}"
        query = urlencode(sorted((key, value) for key, value in parse_qsl(parsed.query)
                                 if not key.lower().startswith(("utm_", "fbclid", "gclid"))))
        path = unquote(parsed.path).rstrip("/") or "/"
        # Le schéma n'identifie pas la ressource éditoriale : http et https
        # doivent correspondre, comme www et la barre finale.
        return urlunsplit(("", netloc, path, query, ""))
    except (ValueError, UnicodeError):
        return ""


def competitor_hosts(candidate: dict) -> set[str]:
    return {_registered_domain(h) for h in (_host(c.get("url", ""))
                                            for c in candidate.get("competitors") or [] if isinstance(c, dict)) if h}


_COMMON_TWO_LEVEL_SUFFIXES = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "co.nz", "co.jp",
    "co.in", "com.br", "com.cn", "com.mx", "com.sg", "com.tr", "co.za", "gouv.fr", "gc.ca", "qc.ca",
}


def _registered_domain(host: str) -> str:
    """Return a registrable-looking domain, keeping subdomains equivalent."""
    labels = [label for label in host.split(".") if label]
    if len(labels) <= 2:
        return host
    suffix = ".".join(labels[-2:])
    return ".".join(labels[-3:]) if suffix in _COMMON_TWO_LEVEL_SUFFIXES else suffix


def _brand_variants(host: str) -> set[str]:
    """« linge-net.com » -> {« linge-net », « linge net », « lingenet »}."""
    label = host.split(".")[0] if host.count(".") >= 1 else host
    label = _fold_accents(label)
    return {v for v in (label, label.replace("-", " "), label.replace("-", "")) if len(v) >= 4}


def _fold_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


_COMMON_WORD_BRANDS_PATH = Path(__file__).with_name("data") / "common_word_brands.txt"
_ATTRIBUTION_VERBS = {"conseille", "recommande", "explique", "indique", "reconnait", "ecrit", "affirme", "precise", "propose"}


def _load_common_word_brands() -> set[str]:
    try:
        return {_fold_accents(line.strip().lower()) for line in _COMMON_WORD_BRANDS_PATH.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")}
    except OSError:  # pragma: no cover - packaging failure fallback
        logger.warning("common_word_brands.txt is missing; using the minimal fallback list")
        return {"ideal"}


_COMMON_WORD_BRANDS = _load_common_word_brands()


def _mentions_competitor(raw_text: str, name: str) -> bool:
    """Match brands with accents, while avoiding common-word false positives."""
    folded = _fold_accents(raw_text)
    for match in re.finditer(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", folded, re.IGNORECASE):
        original = raw_text[match.start():match.end()]
        if name in _COMMON_WORD_BRANDS and original == original.lower():
            prefix = folded[max(0, match.start() - 18):match.start()]
            if not re.search(r"(?:site|magazine|blog|selon|d['’]après)\s+$", prefix, re.IGNORECASE):
                continue
        elif name in _COMMON_WORD_BRANDS:
            prefix = folded[:match.start()].rstrip(" \t\r\f\v")
            sentence_start = not prefix or bool(re.search(r"[.!?;:\n]\s*$", prefix))
            if sentence_start:
                next_words = _fold_accents(raw_text[match.end():match.end() + 80]).lower()
                verbs = re.findall(r"[a-zà-ÿ]+", next_words)
                if not any(word in _ATTRIBUTION_VERBS for word in verbs[:3]):
                    continue
        return True
    return False


def competitor_errors(candidate: dict) -> list[str]:
    """Concurrents : jamais liés, jamais nommés, jamais sources ; au moins 3
    domaines de sources admissibles (consigne du 2026-10-17)."""
    from html import unescape

    content = candidate.get("content_html") or ""
    hosts = competitor_hosts(candidate)
    errors = []
    for url in re.findall(r"""<a\b[^>]*href\s*=\s*["']([^"']+)["']""", content, re.IGNORECASE):
        if _registered_domain(_host(url)) in hosts:
            errors.append(f"Lien vers un concurrent ({_host(url)}) : supprime ce lien, un concurrent n'est jamais une source.")
    block_end = re.compile(r"</(?:h[1-6]|p|li|blockquote|tr|td|th)\s*>", re.IGNORECASE)
    raw_text = unescape(re.sub(r"<[^>]+>", " ", block_end.sub("\n", content)))
    raw_text = re.sub(r"[ \t\r\f\v]+", " ", raw_text)
    raw_text = re.sub(r" *\n *", "\n", raw_text).strip()
    text = raw_text.lower()
    for host in hosts:
        for name in _brand_variants(host):
            if _mentions_competitor(raw_text, name):
                errors.append(f"Le texte nomme le concurrent « {name} » : retire toute mention des concurrents.")
                break
    if re.search(r"\b(sites concurrents|certains sites|conseils (trouvés )?en ligne)\b", text):
        errors.append("Le texte parle de « sites concurrents », « certains sites » ou de « conseils en ligne » : formulation interdite.")
    source_urls = {_url_key(s.get("url", "")) for s in candidate.get("sources") or [] if isinstance(s, dict)} - {""}
    competitor_source_urls = {_url_key(s.get("url", "")) for s in candidate.get("sources") or []
                              if isinstance(s, dict) and _registered_domain(_host(s.get("url", ""))) in hosts}
    if competitor_source_urls:
        errors.append("Un concurrent apparaît dans « sources » : un concurrent n'est jamais une source admissible.")
    source_domains = {_registered_domain(_host(url)) for url in source_urls} - hosts - {""}
    if len(source_domains) < 3:
        errors.append(f"Seulement {len(source_domains)} domaine(s) de sources admissibles hors concurrents : il en faut au "
                      "moins 3 (institutions, associations de consommateurs, organismes techniques, fabricants, études).")
    return errors


_PROSE_COUNT_RE = re.compile(
    r"\b(?:(deux|trois|quatre|cinq|six|sept|huit|neuf|dix|\d{1,2})\s+|"
    r"(un|une)\s+seul(?:e)?\s+)"
    r"(?:[a-zéèêàâîïôûç]+\s+)?"
    r"(gestes?|étapes?|erreurs?|règles?|conseils?|questions?|critères?|astuces?|raisons?|signes?|solutions?|méthodes?|points?|choses?)\b",
    re.IGNORECASE)


QUOTE_MIN_WORDS = 4
_QUOTE_RE = re.compile(r"«\s*(.+?)\s*»|“(.+?)”", re.DOTALL)


def _normalize_quote(text: str) -> str:
    """Comparaison tolérante : casse, apostrophes et guillemets typographiques,
    espaces (dont insécables), ponctuation, et accents ignorés."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"[’‘`´]", "'", text)
    text = re.sub(r"[^\w']+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def quote_errors(candidate: dict) -> list[str]:
    """Toute citation entre guillemets d'au moins 4 mots doit venir d'une
    citation de « facts ». Une citation tronquée (morceaux séparés par « … »
    ou « [...] ») est acceptée si chaque morceau s'y trouve."""
    from app.services.seo.html_text_ops import html_to_text

    quotes = [_normalize_quote(str(f.get("quote") or "")) for f in candidate.get("facts") or [] if isinstance(f, dict)]
    haystack = [q for q in quotes if q]
    missing = []
    for m in _QUOTE_RE.finditer(html_to_text(candidate.get("content_html") or "")):
        passage = (m.group(1) or m.group(2) or "").strip()
        if len(passage.split()) < QUOTE_MIN_WORDS:
            continue
        pieces = [_normalize_quote(p) for p in re.split(r"…|\.\.\.|\[\s*\.*\s*\]", passage)]
        pieces = [p for p in pieces if p]
        if not all(any(piece in q for q in haystack) for piece in pieces):
            missing.append(passage[:200])
    if not missing:
        return []
    return ["Citations absentes des citations de « facts » (ajoute chaque fait avec sa citation exacte, "
            "ou reformule sans guillemets) : " + " | ".join(f"« {q} »" for q in missing)]


def fact_errors(candidate: dict) -> list[str]:
    """Chaque fait doit être traçable par une source et une citation."""
    sources = {_url_key(item.get("url", "")) for item in candidate.get("sources") or []
               if isinstance(item, dict)} - {""}
    errors = []
    for index, fact in enumerate(candidate.get("facts") or [], start=1):
        if not isinstance(fact, dict):
            errors.append(f"Le fait #{index} n'est pas un objet JSON.")
            continue
        if not str(fact.get("value") or "").strip():
            errors.append(f"Le fait #{index} n'a pas de valeur.")
        if not str(fact.get("quote") or "").strip():
            errors.append(f"Le fait #{index} n'a pas de citation exacte dans « quote ».")
        source_url = _url_key(str(fact.get("source_url") or ""))
        if not source_url or source_url not in sources:
            errors.append("La source du fait #{} n'apparaît pas dans « sources ».".format(index))
    return errors


def self_review_errors(candidate: dict) -> list[str]:
    """L'agent ne peut pas justifier un fait par sa mémoire."""
    notes = str((candidate.get("self_review") or {}).get("notes") or "")
    suspicious = re.compile(
        r"(?:connaissances générales|de mémoire|sans\s+(?:source|citation)|"
        r"non\s+sourc(?:é|ée|és|ées)|non\s+vérifi(?:é|ée|és|ées)|"
        r"pas\s+d['’]une\s+source(?:\s+lue)?|ne\s+vient\s+pas\s+d['’]une\s+source|"
        r"faute\s+de\s+source)", re.IGNORECASE)
    negated = re.compile(
        r"\b(?:(?:aucun|aucune|rien|jamais|ni)\b.{0,40}|"
        r"(?:pas\s+de|n['’]\w*\s+pas|plus\s+de)\b.{0,40})"
        r"(?:connaissances générales|de mémoire|sans\s+(?:source|citation)|"
        r"non\s+sourc(?:é|ée|és|ées)|non\s+vérifi(?:é|ée|és|ées))\b", re.IGNORECASE)
    for sentence in re.split(r"(?<=[.!?;])\s+|,\s+(?=(?:mais|sauf|cependant|toutefois)\b)", notes,
                             flags=re.IGNORECASE):
        if suspicious.search(sentence) and not negated.search(sentence):
            return ["L'auto-relecture reconnaît un fait non sourcé : supprime-le ou ajoute une citation exacte."]
    return []


def prose_count_errors(content: str) -> list[str]:
    """« deux gestes à faire dans l'ordre » suivi d'une liste de trois
    éléments : faute dure."""
    errors = []

    def inside(tag: str, position: int) -> bool:
        return content.lower().rfind(f"<{tag}", 0, position) > content.lower().rfind(f"</{tag}", 0, position)

    for m in _PROSE_COUNT_RE.finditer(content or ""):
        if inside("blockquote", m.start()) or inside("table", m.start()):
            continue
        if re.search(r"<h[23]\b[^>]*>[^<]*$", content[:m.start()], re.IGNORECASE):
            continue  # dans un titre : vérifié par announced_count_errors
        after = content[m.end():m.end() + 4000]
        nxt = re.search(r"<(ol|ul)\b.*?</\1>", after, re.IGNORECASE | re.DOTALL)
        between = after[:nxt.start()] if nxt else ""
        if not nxt or re.search(r"<h[23]\b", between, re.IGNORECASE) or len(between) > 600:
            continue
        raw_count = m.group(1) or m.group(2)
        announced = int(raw_count) if raw_count.isdigit() else (_COUNT_WORDS[raw_count.lower()]
                                                                if raw_count.lower() in _COUNT_WORDS else 1)
        items = len(re.findall(r"<li\b", nxt.group(0), re.IGNORECASE))
        if items != announced:
            errors.append(f"Le texte annonce « {m.group(0)} » mais la liste qui suit contient {items} éléments.")
    return errors


def fact_lines(candidate: dict) -> list[str]:
    """Faits de l'agent tels que le juge les reçoit (valeur, citation, source)."""
    return [f"{f.get('value', '')} — « {f.get('quote', '')} » (source : {f.get('source_url', '')})"
            for f in candidate.get("facts") or [] if isinstance(f, dict)]


def judge_errors(orch, article, candidate: dict) -> list[str]:
    """Fautes « de sens » du juge éditorial corrigées par un tour : titre qui
    ne tient pas sa promesse (heading_mismatch) et chiffre absent des faits
    cités (unsourced_figure, passage renvoyé tel quel). Le juge reçoit les
    faits de l'agent pour ne pas signaler un chiffre bien sourcé."""
    from app.services.seo.editorial_judge import judge_article

    def judge_call(prompt: str, step: str, temperature: float) -> str:
        return orch._write_pass(prompt, "quality_gate", article, temperature, step)

    try:
        judgement = judge_article(candidate.get("content_html") or "", judge_call, title=candidate.get("title") or "",
                                  keyword=article_keyword(orch), brief={}, facts=fact_lines(candidate),
                                  reference_figures=[], competitors=sorted(competitor_hosts(candidate)),
                                  strict_facts=True)
    except Exception:
        return []
    orch.context["agent_last_judgement"] = judgement
    errors = []
    for b in judgement.get("blockers") or []:
        if b.get("type") == "heading_mismatch":
            errors.append(f"Titre en désaccord avec sa section : {b.get('section', '')} ({b.get('detail', '')})")
        elif b.get("type") == "unsourced_figure":
            errors.append(f"Chiffre ou affirmation sans citation dans « facts » (section {b.get('section', '')}) : "
                          f"{b.get('detail', '')}. Ajoute le fait avec sa citation exacte, ou retire-le.")
    return errors


def correction_rounds(writer, check, data: dict, run_report: dict, step=lambda label: None) -> tuple[dict, list, dict]:
    """Au plus deux tours de correction sur les fautes dures. Une erreur
    pendant un tour (dont l'arrêt dur du coût) termine la boucle : le
    meilleur article déjà obtenu (au pire celui du tour 0) est gardé."""
    best, (best_errors, plag_report) = data, check(data)
    run_report["rounds"].append({"round": 0, "errors": best_errors})
    for round_no in (1, 2):
        if not best_errors:
            break
        try:
            corrected = writer.correct(best_errors)
        except Exception as exc:
            run_report["rounds"].append({"round": round_no, "error": str(exc)[:300]})
            break
        if corrected is None:
            run_report["rounds"].append({"round": round_no, "error": "JSON corrigé inexploitable"})
            continue
        errors, report = check(corrected)
        run_report["rounds"].append({"round": round_no, "errors": errors})
        if len(errors) <= len(best_errors):
            best, best_errors, plag_report = corrected, errors, report
        step(f"AgentWriter correction #{round_no} ({len(errors)} erreur(s) restante(s))")
    run_report["remaining_errors"] = best_errors
    return best, best_errors, plag_report


REVIEW_SYSTEM = (
    "Tu es un relecteur indépendant. Tu ne réécris rien : tu cherches uniquement les contradictions internes "
    "d'un article.")
REVIEW_INSTRUCTIONS = """Relis cet article.
1. Repère chaque règle, seuil ou calcul que l'article pose lui-même (par exemple une formule, un rythme, une heure).
2. Applique-les à chaque ligne de tableau, à chaque conseil, à la conclusion et à la FAQ.
3. Compare aussi chaque affirmation chiffrée aux faits cités ci-dessous.
Signale seulement une vraie contradiction : deux passages qui ne peuvent pas être vrais ensemble, ou un conseil
qui contredit le calcul de l'article ou un fait cité. Ne signale ni le style, ni une simple reformulation, ni un
arrondi (« 10 minutes » et « environ dix minutes » ne se contredisent pas).

Réponds uniquement par ce JSON :
{"contradictions": [{"passage": "texte exact de l'article", "probleme": "ce qui contredit quoi", "correction": "ce qu'il faut écrire"}]}
Liste vide si l'article est cohérent.

Faits cités :
{facts}

Article (HTML) :
{content}"""


def consistency_review(complete, candidate: dict) -> list[str]:
    """Relecture indépendante (conversation neuve, sans outils) : les
    contradictions trouvées deviennent des fautes dures à corriger."""
    from app.services.seo.html_text_ops import extract_json_object

    prompt = (REVIEW_INSTRUCTIONS.replace("{facts}", "\n".join(f"- {line}" for line in fact_lines(candidate)) or "- aucun")
              .replace("{content}", candidate.get("content_html") or ""))
    data = extract_json_object(complete(REVIEW_SYSTEM, prompt)) or {}
    errors = []
    for item in data.get("contradictions") or []:
        if isinstance(item, dict) and str(item.get("passage") or "").strip():
            errors.append(f"Contradiction interne : « {str(item['passage']).strip()[:300]} » : "
                          f"{str(item.get('probleme') or '').strip()[:300]} Correction attendue : "
                          f"{str(item.get('correction') or '').strip()[:300]}")
    return errors


def review_round(writer, check, complete, best: dict, best_errors: list, plag_report: dict,
                 run_report: dict) -> tuple[dict, list, dict]:
    """Relecture de cohérence puis, si elle trouve des contradictions, un tour
    de correction. Le nouvel article n'est gardé que s'il n'ajoute aucune
    faute dure ; une erreur (dont l'arrêt dur) garde l'article précédent."""
    try:
        review = consistency_review(complete, best)
    except Exception as exc:
        run_report["consistency_review"] = {"error": str(exc)[:300]}
        return best, best_errors, plag_report
    run_report["consistency_review"] = {"contradictions": review}
    if not review:
        return best, best_errors, plag_report
    try:
        corrected = writer.correct(best_errors + review)
    except Exception as exc:
        run_report["rounds"].append({"round": "relecture", "error": str(exc)[:300]})
        return best, best_errors, plag_report
    if corrected is None:
        run_report["rounds"].append({"round": "relecture", "error": "JSON corrigé inexploitable"})
        return best, best_errors, plag_report
    errors, report = check(corrected)
    run_report["rounds"].append({"round": "relecture", "errors": errors})
    if len(errors) <= len(best_errors):
        best, best_errors, plag_report = corrected, errors, report
        run_report["remaining_errors"] = best_errors
    return best, best_errors, plag_report


def article_keyword(orch) -> str:
    return str((orch.context.get("idea_discovery") or {}).get("main_keyword") or "")


def plagiarism_errors(orch: "SEOGenerationOrchestrator", content: str) -> tuple[list[str], dict]:
    from app.services.seo.plagiarism_check import SerpPlagiarismBackend, check_plagiarism

    backend = None
    if orch.serp_adapter.configured:
        own = (orch.project.domain if orch.project else "") or ""
        backend = SerpPlagiarismBackend(orch.serp_adapter.search, own_domain=own)
    report = check_plagiarism(content, backend)
    errors = [f"Phrase reprise mot pour mot d'une page en ligne ({m.get('url', '')}) : reformule « {m.get('sentence', '')} »"
              for m in report.get("matches") or []]
    return errors, report


def _unique_slug(db, project_id: str, wanted: str, article_id: str) -> str:
    from sqlalchemy import select

    from app.core.utils import slugify

    base = slugify(wanted or "")[:80] or f"article-{uuid.uuid4().hex[:6]}"
    slug, n = base, 2
    while db.execute(select(Article.id).where(Article.project_id == project_id, Article.slug == slug,
                                              Article.id != article_id)).first():
        slug, n = f"{base}-{n}", n + 1
    return slug


def generate_with_agent(orch: "SEOGenerationOrchestrator", *, final_title: str, final_keyword: str,
                        chosen_category: str | None, category_name: str, project_context: dict,
                        category_strategy: dict, idea_discovery: dict, cannibalization: dict,
                        audience: str | None, existing_article_id: str | None, api_key: str, model: str,
                        provider: str = "anthropic") -> Article:
    from app.models.content import ArticleSeo
    from app.models.ai import WorkflowRun
    from app.services.seo.agent_writer import (
        AgentWriter, AgentWriterError, anthropic_client, build_user_message, load_system_prompt, locale_names,
    )
    from app.services.seo.seo_generation_orchestrator import _DraftArticle

    db = orch.db
    if existing_article_id:
        article = db.get(Article, existing_article_id)
        if article is None:
            raise RuntimeError(f"Article {existing_article_id} non trouvé")
        set_article_status(article, ArticleStatus.WRITING_IN_PROGRESS)
    else:
        article = Article(
            id=str(uuid.uuid4()), project_id=orch.project_id, category_id=chosen_category,
            slug=f"idea-{uuid.uuid4().hex[:8]}", search_intent=idea_discovery.get("detected_intent"),
            status_reason_id=ArticleStatus.WRITING_IN_PROGRESS, state_id=0, priority=0,
            opportunity_score=idea_discovery.get("opportunity_score", 0.5),
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        )
        db.add(article)
    db.flush()
    draft = _DraftArticle(article)
    draft.title, draft.keyword = final_title, final_keyword
    draft.audience = audience or project_context.get("target_audience")
    orch.workflow_run = WorkflowRun(article_id=article.id, phase_id=WorkflowPhase.PRODUCTION,
                                    status_reason_id=RunStatus.RUNNING, state_id=0)
    db.add(orch.workflow_run)
    db.flush()
    for key, value in (("project_context", project_context), ("category_strategy", category_strategy),
                       ("idea_discovery", idea_discovery), ("cannibalization_check", cannibalization)):
        orch._save(article.id, key, value)

    langue, pays = locale_names(orch.project.locale if orch.project else None)
    system = load_system_prompt(site_name=orch.project.name if orch.project else "", langue=langue, pays=pays,
                                site_domain=(orch.project.domain if orch.project else "") or "")
    editor_notes = " ".join(x for x in (orch.context.get("expert_notes") or "", orch.context.get("context_hint") or "") if x)
    user_message = build_user_message(keyword=final_keyword, category=category_name, editor_notes=editor_notes or None,
                                      published_articles=published_articles(db, orch.project))
    agent_settings = orch._agent_settings()
    if provider == "openrouter":
        from app.services.seo.agent_writer_openrouter import OpenRouterAgentClient, page_fetcher, reader_get
        fetch_fn = page_fetcher(orch.page_cache, fallback=reader_get if agent_settings["reader_fallback"] else None)
        client = OpenRouterAgentClient(api_key, model=model, search_fn=orch.serp_adapter.search, fetch_fn=fetch_fn,
                                       max_searches=6, max_fetches=6, max_cost_usd=agent_settings["max_cost_usd"],
                                       reasoning_effort=agent_settings["reasoning_effort"])
    else:
        client = anthropic_client(api_key)
    writer = AgentWriter(client, model=model, system=system)
    run_report: dict = {"rounds": []}
    try:
        orch._step("AgentWriter (recherche et rédaction)")
        data = writer.write(user_message)
    except AgentWriterError as exc:
        return _fail(orch, article, draft, category_name, f"Agent rédacteur : {exc}", writer, run_report)
    except Exception as exc:  # erreur API (clé, quota, réseau)
        return _fail(orch, article, draft, category_name, f"Agent rédacteur indisponible : {exc}", writer, run_report)

    def check(candidate: dict) -> tuple[list[str], dict]:
        """Fautes dures seulement (elles déclenchent une correction) ; la
        cohérence est informative et rangée dans le rapport."""
        content = candidate.get("content_html") or ""
        errors = structure_errors(content, candidate.get("title") or final_title)
        errors += assembly_errors(candidate) + link_errors(content) + html_render_errors(content)
        errors += announced_count_errors(content) + prose_count_errors(content) + competitor_errors(candidate)
        errors += fact_errors(candidate) + quote_errors(candidate)
        errors += self_review_errors(candidate)
        errors += judge_errors(orch, article, candidate)
        plag_errors, plag_report = plagiarism_errors(orch, content)
        plag_report["consistency_info"] = consistency_errors(content, orch._polish_call_fn(article))
        return errors + plag_errors, plag_report

    best, best_errors, plag_report = correction_rounds(writer, check, data, run_report, orch._step)
    if agent_settings["consistency_review"] and callable(getattr(client, "complete", None)):
        orch._step("AgentWriter relecture de cohérence")
        best, best_errors, plag_report = review_round(writer, check, client.complete, best, best_errors,
                                                      plag_report, run_report)

    content = best.get("content_html") or ""
    if orch._is_french():
        from app.services.seo.french_typography import fix_french_text, fix_french_typography
        content = fix_french_typography(content)
        best["title"] = fix_french_text(best.get("title") or final_title)
    draft.title = best.get("title") or final_title
    draft.content = content
    draft.meta_title = (best.get("meta_title") or draft.title)[:255]
    draft.meta_description = (best.get("meta_description") or "")[:500]
    draft.faq = [{"question": str(f.get("question", "")).strip(), "answer": str(f.get("answer", "")).strip()}
                 for f in best.get("faq") or [] if isinstance(f, dict) and f.get("question") and f.get("answer")]
    draft.excerpt = orch._extract_excerpt(content)
    draft.word_count = calculate_word_count(content)
    draft.reading_time_minutes = calculate_reading_time_minutes(draft.word_count)
    article.slug = _unique_slug(db, orch.project_id, best.get("slug") or draft.title, article.id)
    orch._persist_revision(draft)
    orch._save(article.id, "agent_writer_output",
               {k: best.get(k) for k in ("sources", "facts", "competitors", "sub_questions", "self_review")})
    orch._save(article.id, "plagiarism_report", plag_report)

    _finish_seo(orch, article, draft, category_name, best)
    run_report["consistency_info"] = (plag_report or {}).get("consistency_info") or []
    run_report.update(writer.report())
    orch._save(article.id, "agent_writer_report", run_report)
    orch._score_article(article, draft)
    set_article_status(article, ArticleStatus.DRAFT_READY)
    article.updated_at = datetime.now(timezone.utc)
    orch._finalize_report(article, draft, category_name, {}, {}, {}, {}, {}, {}, {})
    set_run_status(orch.workflow_run, RunStatus.SUCCEEDED)
    orch.workflow_run.finished_at = datetime.now(timezone.utc)
    db.flush()
    return article


def _finish_seo(orch, article: Article, draft, category_name: str, best: dict) -> None:
    """Données structurées, checklist SEO et juge éditorial (score)."""
    from app.models.content import ArticleSeo
    from app.services.seo.seo_final_checklist_service import check_seo_final_dict
    from app.services.structured_data_builder import build_structured_data

    try:
        structured = build_structured_data(
            title=draft.title, slug=article.slug, meta_title=draft.meta_title, meta_description=draft.meta_description,
            excerpt=draft.excerpt, author=draft.author_name, published_at=article.published_at,
            updated_at=article.updated_at, category=category_name, content=draft.content,
            faq_json=json.dumps(draft.faq) if draft.faq else None, cover_image_url=None,
            site_name=orch.project.name if orch.project else None,
            organization_name=orch.project.name if orch.project else None,
        )
        draft.structured_data_json = structured
        seo_row = orch.db.get(ArticleSeo, article.id)
        if seo_row is not None and isinstance(structured, dict) and structured.get("schemas"):
            seo_row.structured_data = structured
        orch._save(article.id, "structured_data", structured)
        orch._step("StructuredDataBuilder")
    except Exception as exc:
        orch._error("StructuredDataBuilder", str(exc))
    try:
        seo_final = check_seo_final_dict(
            content=draft.content, title=draft.title, slug=article.slug, meta_title=draft.meta_title,
            meta_description=draft.meta_description, keyword=draft.keyword, faq_count=len(draft.faq or []),
            internal_links=[], external_links=[], images=[], has_structured_data=bool(draft.structured_data_json),
            min_word_count=None,
        )
        orch._save(article.id, "seo_final_checklist", seo_final)
        orch._step("SEOFinalChecklist")
    except Exception as exc:
        orch._error("SEOFinalChecklist", str(exc))
    try:
        from app.services.seo.editorial_judge import judge_article
        from app.services.seo.structure_validator import validate_structure

        def judge_call(prompt: str, step: str, temperature: float) -> str:
            return orch._write_pass(prompt, "quality_gate", article, temperature, step)

        judgement = judge_article(draft.content, judge_call, title=draft.title, keyword=draft.keyword or "",
                                  brief={}, facts=fact_lines(best), reference_figures=[],
                                  structure_report=validate_structure(draft.content, draft.title),
                                  competitors=sorted(competitor_hosts(best)), strict_facts=True)
        if not judgement.get("error"):
            orch.context["editorial_judgement"] = {"final": judgement, "rounds": [judgement]}
            orch._save(article.id, "editorial_judgement", {"final": judgement, "rounds": [judgement]})
            orch._step(f"EditorialJudge ({judgement['content_score']}/95)")
    except Exception as exc:
        orch._error("EditorialJudge", str(exc))


def _fail(orch, article: Article, draft, category_name: str, message: str, writer, run_report: dict) -> Article:
    orch._error("AgentWriter", message)
    set_article_status(article, ArticleStatus.FAILED)
    article.updated_at = datetime.now(timezone.utc)
    set_run_status(orch.workflow_run, RunStatus.FAILED)
    orch.workflow_run.error = message
    orch.workflow_run.finished_at = datetime.now(timezone.utc)
    run_report.update(writer.report())
    run_report["error"] = message
    orch._save(article.id, "agent_writer_report", run_report)
    orch.db.flush()
    orch._finalize_report(article, draft, category_name, {}, {}, {}, {}, {}, {}, {})
    return article
