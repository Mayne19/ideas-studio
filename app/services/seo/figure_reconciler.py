"""Chiffres de référence (chaîne v2) : une valeur par grandeur, avant rédaction.

Chaque section reçoit ses propres faits ; quand plusieurs sources chiffrent
la même grandeur différemment (prix d'un freelance : 900-5 000 € chez France
Num, 1 500-2 000 € ailleurs, 300-700 € par page), chaque section en reprenait
une autre et l'article se contredisait. La passe de cohérence corrigeait
après coup, phrase par phrase, parfois en créant une nouvelle contradiction.

Ici un appel court regroupe les faits chiffrés du registre par grandeur et
retient UNE formulation de référence par grandeur (source forte d'abord), que
toutes les sections reçoivent dans le brief commun.
"""
from __future__ import annotations

import logging
from typing import Callable

from app.services.seo.html_text_ops import extract_json_object

logger = logging.getLogger(__name__)

CallFn = Callable[[str, str, float], str]
MAX_FACTS = 40
MAX_FIGURES = 8


def _figure_facts(ledger_facts: list[dict]) -> list[dict]:
    return [
        f for f in ledger_facts or []
        if isinstance(f, dict) and f.get("fact_id") and str(f.get("figure") or "").strip()
    ][:MAX_FACTS]


def build_reconcile_prompt(facts: list[dict], keyword: str) -> str:
    lines = [
        f"Sujet de l'article : {keyword}",
        "",
        "Faits chiffrés vérifiés (identifiant, fiabilité de la source, énoncé, chiffre) :",
    ]
    for f in facts:
        lines.append(
            f"- {f['fact_id']} [{f.get('source_tier') or 'neutral'}] {str(f.get('claim', ''))[:220]} "
            f"(chiffre : {f.get('figure')})"
        )
    lines += [
        "",
        f"Regroupe les faits qui chiffrent la même grandeur (au plus {MAX_FIGURES} grandeurs, seulement "
        "celles chiffrées par au moins un fait). Pour chacune, écris UNE formulation de référence que "
        "tout l'article utilisera :",
        "- source « strong » d'abord ; sinon la fourchette la plus partagée par les sources ;",
        "- distingue les grandeurs différentes (prix total ≠ prix par page ≠ coût annuel) ;",
        "- n'invente aucun chiffre : la référence reprend un fait ou l'enveloppe de plusieurs faits.",
        "- écarte les faits qui visent un autre public ou un autre cas que le lecteur de l'article "
        "(administrations, grands comptes…) : ils ne deviennent jamais une référence.",
        "",
        'Réponds en JSON : {"figures": [{"quantity": "prix d\'un site vitrine chez un freelance", '
        '"reference": "900 à 5 000 €, 1 500 à 2 000 € en moyenne", "fact_ids": ["F2", "F21"]}]}',
    ]
    return "\n".join(lines)


def reconcile_figures(ledger_facts: list[dict], keyword: str, call_fn: CallFn,
                      fatal_exceptions: tuple[type[BaseException], ...] = ()) -> dict:
    """{figures: [{quantity, reference, fact_ids}], error}. Sans fait chiffré,
    aucun appel."""
    facts = _figure_facts(ledger_facts)
    report: dict = {"figures": [], "error": None, "facts_considered": len(facts)}
    if len(facts) < 2:
        return report
    known = {f["fact_id"] for f in facts}
    try:
        raw = call_fn(build_reconcile_prompt(facts, keyword), "FigureReconciliation", 0.1)
    except fatal_exceptions:
        raise
    except Exception as exc:
        logger.warning("figure_reconciler: appel en échec : %s", exc)
        report["error"] = str(exc)[:300]
        return report
    data = extract_json_object(raw) or {}
    for item in data.get("figures") or []:
        if not isinstance(item, dict):
            continue
        quantity = str(item.get("quantity") or "").strip()
        reference = str(item.get("reference") or "").strip()
        ids = [str(i).strip() for i in item.get("fact_ids") or [] if str(i).strip() in known]
        if quantity and reference and ids:
            report["figures"].append({"quantity": quantity, "reference": reference, "fact_ids": ids})
        if len(report["figures"]) >= MAX_FIGURES:
            break
    return report


def format_reference_figures(figures: list[dict]) -> str:
    if not figures:
        return ""
    lines = [
        "Chiffres de référence (identiques dans tout l'article ; pour ces grandeurs, n'utilise pas "
        "d'autre fourchette, même si un fait de ta section en donne une autre) :"
    ]
    for fig in figures:
        lines.append(f"- {fig['quantity']} : {fig['reference']} [{', '.join(fig['fact_ids'])}]")
    return "\n".join(lines)
