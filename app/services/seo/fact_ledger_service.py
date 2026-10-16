from __future__ import annotations

"""A2 Research Reader, partie extraction : registre central des faits
(`fact_ledger`, chaîne v2 étape 6). Remplace l'EvidencePack nourri de
snippets de 500 caractères.

Un appel LLM bon marché par page lue (artefact `source_pages`) extrait des
faits {claim, quote_verbatim, figure, date_or_as_of, usage_hint}. Le code
vérifie ensuite que `quote_verbatim` est une sous-chaîne exacte du texte de
la page (espaces normalisés seulement) : un fait dont la citation n'existe
pas dans la page est supprimé, jamais « corrigé ». Un chiffre absent de sa
citation est retiré du fait. Chaque fait reçoit un identifiant F1, F2… et
garde l'URL et le tier de sa page.
"""

import logging
import re
from typing import Callable

logger = logging.getLogger(__name__)

JsonCall = Callable[[str], dict]

MAX_FACTS_PER_PAGE = 8
MAX_FACTS_TOTAL = 40
MIN_QUOTE_CHARS = 20
_WS_RE = re.compile(r"\s+")
_DIGITS_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _collapse(text: str) -> str:
    return _WS_RE.sub(" ", text or "").strip()


def quote_in_page(quote: str, page_text: str) -> bool:
    """Vrai si la citation est une sous-chaîne exacte de la page. Seuls les
    blancs (sauts de ligne, espaces multiples, insécables) sont normalisés :
    ni la casse, ni la ponctuation, ni les mots ne peuvent différer."""
    quote = (quote or "").strip()
    if len(quote) < MIN_QUOTE_CHARS or not page_text:
        return False
    if quote in page_text:
        return True
    return _collapse(quote.replace(" ", " ")) in _collapse(page_text.replace(" ", " "))


def figure_in_quote(figure: str, quote: str) -> bool:
    """Chaque nombre du chiffre annoncé doit apparaître dans la citation."""
    numbers = _DIGITS_RE.findall(figure or "")
    if not numbers:
        return bool((figure or "").strip()) and _collapse(figure).lower() in _collapse(quote).lower()
    quote_numbers = {n.replace(",", ".") for n in _DIGITS_RE.findall((quote or "").replace(" ", "").replace(" ", ""))}
    quote_numbers |= {n.replace(",", ".") for n in _DIGITS_RE.findall(quote or "")}
    return all(n.replace(",", ".") in quote_numbers for n in numbers)


def build_page_prompt(page: dict, keyword: str, reader_question: str) -> str:
    return (
        "Tu prépares le dossier de faits d'un article. Extrais de cette page les faits précis "
        "et vérifiables utiles au lecteur : chiffres, prix, dates, durées, limites, conditions, "
        "définitions officielles, résultats d'études.\n\n"
        f"Sujet : {keyword}\n"
        + (f"Question du lecteur : {reader_question}\n" if reader_question else "")
        + f"Page : {page.get('title') or ''} ({page.get('url')})\n\n"
        "Règles absolues :\n"
        "- quote_verbatim est un passage COPIÉ MOT POUR MOT depuis la page (20 à 300 caractères), "
        "sans rien changer : il sera vérifié automatiquement et le fait sera supprimé sinon.\n"
        "- claim reformule le fait en une phrase autonome, sans rien ajouter à la citation.\n"
        "- figure : le chiffre clé tel qu'il apparaît dans la citation, sinon vide.\n"
        "- date_or_as_of : la date ou période à laquelle le fait est valable si la page la donne, sinon vide.\n"
        "- usage_hint : la sous-question de l'article à laquelle ce fait répond.\n"
        f"- {MAX_FACTS_PER_PAGE} faits au maximum ; aucun fait si la page n'en contient pas.\n\n"
        f"Texte de la page :\n\"\"\"\n{page.get('text') or ''}\n\"\"\"\n\n"
        "Réponds UNIQUEMENT avec ce JSON :\n"
        '{"facts": [{"claim": "...", "quote_verbatim": "...", "figure": "", "date_or_as_of": "", '
        '"usage_hint": "..."}]}'
    )


def verify_page_facts(raw_facts, page: dict) -> tuple[list[dict], list[dict]]:
    """(faits gardés, faits rejetés avec raison) pour une page."""
    kept: list[dict] = []
    rejected: list[dict] = []
    text = page.get("text") or ""
    seen: set[str] = set()
    for item in raw_facts if isinstance(raw_facts, list) else []:
        if not isinstance(item, dict):
            continue
        claim = _collapse(str(item.get("claim") or ""))
        quote = str(item.get("quote_verbatim") or "").strip().strip("\"«» ").strip()
        if not claim:
            continue
        if not quote_in_page(quote, text):
            rejected.append({"claim": claim[:200], "quote": quote[:200], "reason": "quote_not_in_page"})
            continue
        key = _collapse(quote).lower()
        if key in seen:
            continue
        seen.add(key)
        figure = _collapse(str(item.get("figure") or ""))
        if figure and not figure_in_quote(figure, quote):
            figure = ""
        kept.append({
            "claim": claim[:400],
            "quote_verbatim": quote[:600],
            "figure": figure[:80],
            "date_or_as_of": _collapse(str(item.get("date_or_as_of") or ""))[:60],
            "usage_hint": _collapse(str(item.get("usage_hint") or ""))[:200],
            "url": page.get("url") or "",
            "source_tier": page.get("source_tier") or "neutral",
            "page_role": page.get("role") or "",
        })
        if len(kept) >= MAX_FACTS_PER_PAGE:
            break
    return kept, rejected


def build_fact_ledger(
    source_pages: dict,
    keyword: str,
    call_json: JsonCall,
    *,
    reader_question: str = "",
    max_facts: int = MAX_FACTS_TOTAL,
) -> dict:
    """Artefact `fact_ledger` : {facts, rejected, pages_processed, llm_calls,
    status}. Les sources primaires passent avant les concurrents."""
    pages = [p for p in (source_pages or {}).get("pages") or [] if isinstance(p, dict) and p.get("text")]
    pages.sort(key=lambda p: 0 if p.get("role") == "primary" else 1)
    facts: list[dict] = []
    rejected: list[dict] = []
    calls = 0
    errors = 0
    for page in pages:
        if len(facts) >= max_facts:
            break
        calls += 1
        try:
            result = call_json(build_page_prompt(page, keyword, reader_question))
        except Exception as exc:
            logger.warning("fact_ledger: extraction échouée pour %s : %s", page.get("url"), exc)
            errors += 1
            continue
        raw = result.get("facts") if isinstance(result, dict) else None
        kept, dropped = verify_page_facts(raw, page)
        rejected.extend({**d, "url": page.get("url")} for d in dropped)
        facts.extend(kept)
    facts = facts[:max_facts]
    for i, fact in enumerate(facts, start=1):
        fact["fact_id"] = f"F{i}"
    status = "success" if facts else ("error" if errors and errors == calls else "empty")
    if not pages:
        status = "skipped"
    return {
        "status": status,
        "facts": facts,
        "rejected": rejected[:50],
        "rejected_count": len(rejected),
        "pages_processed": len(pages),
        "llm_calls": calls,
    }


def enrich_markers(ledger: dict, markers: list[dict]) -> list[dict]:
    """Marqueurs [F#] du rédacteur complétés par l'URL, la citation et le
    chiffre du fait : matière du futur vérificateur (A7)."""
    by_id = {f.get("fact_id"): f for f in (ledger or {}).get("facts") or []}
    enriched = []
    for marker in markers or []:
        fact = by_id.get(marker.get("fact_id")) or {}
        enriched.append({
            **marker,
            "known": bool(fact),
            "url": fact.get("url", ""),
            "quote_verbatim": fact.get("quote_verbatim", ""),
            "figure": fact.get("figure", ""),
        })
    return enriched


def citation_candidates_from_markers(ledger: dict, markers: list[dict], keyword: str = "",
                                     competitor_hosts: set[str] | None = None) -> list[dict]:
    """Sources externes candidates pour CitationPass, dans l'ordre des faits
    réellement utilisés par le rédacteur (marqueurs connus). L'extrait est
    la citation exacte du fait, ce qui permet à CitationPass de choisir la
    bonne phrase. Les concurrents de la SERP et les sources faibles sont
    exclus (on ne renvoie pas le lecteur chez un concurrent)."""
    from app.services.seo.external_link_service import _clean_url, _is_serp_competitor

    by_id = {f.get("fact_id"): f for f in (ledger or {}).get("facts") or []}
    links: list[dict] = []
    seen: set[str] = set()
    for marker in markers or []:
        fact = by_id.get(marker.get("fact_id"))
        if not fact:
            continue
        url = _clean_url(fact.get("url") or "")
        if not url or url in seen or fact.get("source_tier") == "weak":
            continue
        if competitor_hosts and _is_serp_competitor(url, competitor_hosts):
            continue
        seen.add(url)
        links.append({
            "url": url,
            "anchor_text": fact.get("claim", "")[:80],
            "placement": "auto",
            "reason": f"Fait {fact.get('fact_id')} utilisé par le rédacteur",
            "source_reliability": "high" if fact.get("source_tier") == "strong" else "medium",
            "domain_tier": fact.get("source_tier") or "neutral",
            "excerpt": (fact.get("quote_verbatim") or "")[:220],
            "nofollow_recommended": fact.get("source_tier") != "strong",
            "fact_id": fact.get("fact_id"),
        })
    return links


def ledger_to_evidence_pack(ledger: dict) -> dict:
    """Vue compatible EvidencePack (GEO, cohérence, score) du registre."""
    items = []
    for fact in (ledger or {}).get("facts") or []:
        items.append({
            "type": "statistique" if fact.get("figure") else "donnee",
            "fact": fact.get("claim", ""),
            "figure": fact.get("figure", ""),
            "source_url": fact.get("url", ""),
            "reliability": "high" if fact.get("source_tier") == "strong" else "medium",
            "usage_hint": fact.get("usage_hint", ""),
            "fact_id": fact.get("fact_id", ""),
        })
    return {"status": "success" if items else "empty", "evidence_items": items, "source": "fact_ledger"}
