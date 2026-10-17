"""Contrôles du laboratoire : trois contrôles techniques bloquants et une
alerte de plagiat. Le style relève du skill, pas du code."""

from __future__ import annotations

FICHE_FIELDS: dict[str, type] = {
    "meta_title": str, "meta_description": str, "slug": str, "mot_cle_principal": str,
    "sources": list, "images": list, "liens_internes_places": list, "liens_internes_suggeres": list, "faq": list,
}
# Champs acceptés mais facultatifs (une fiche plus ancienne reste valide) :
# s'ils sont présents, ce sont des listes.
OPTIONAL_FICHE_FIELDS: dict[str, type] = {
    "integrations": list, "experience_a_ajouter": list, "a_mettre_a_jour": list,
}


def _caption_problems(fiche: dict) -> list[str]:
    problems: list[str] = []
    for collection in ("images", "integrations"):
        items = fiche.get(collection)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if isinstance(item, dict) and "legende" in item and not isinstance(item["legende"], str):
                problems.append(f"{collection}[{index}].legende doit être str")
    return problems


def summary_box(article: str) -> dict:
    ok = '<aside class="summary">' in article
    return {"name": "encadré « En résumé »", "passed": ok,
            "detail": "" if ok else 'aucun <aside class="summary"> dans l\'article'}


def no_em_dash(article: str) -> dict:
    count = article.count("—")
    return {"name": "aucun tiret cadratin", "passed": count == 0,
            "detail": "" if count == 0 else f"{count} tiret(s) cadratin(s)"}


def fiche_valid(fiche: dict | None, error: str) -> dict:
    if fiche is None:
        return {"name": "fiche json valide", "passed": False, "detail": error or "fiche absente"}
    problems = [f"{key} manquant" for key in FICHE_FIELDS if key not in fiche]
    problems += [f"{key} doit être {kind.__name__}" for key, kind in (FICHE_FIELDS | OPTIONAL_FICHE_FIELDS).items()
                 if key in fiche and not isinstance(fiche[key], kind)]
    problems += _caption_problems(fiche)
    return {"name": "fiche json valide", "passed": not problems, "detail": " ; ".join(problems)}


def blocking_checks(article: str, fiche: dict | None, fiche_error: str) -> list[dict]:
    return [summary_box(article), no_em_dash(article), fiche_valid(fiche, fiche_error)]
