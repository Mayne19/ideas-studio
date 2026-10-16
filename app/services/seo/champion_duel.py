"""Duel contre le champion : notre article face au n°1 de Google.

Référence extérieure plutôt qu'auto-évaluation : un article déjà classé en
tête sur une requête disputée est jugé « réussi » par Google et ses lecteurs.
On le dissèque, puis des juges IA d'autres familles que le rédacteur
comparent à l'aveugle notre article et le sien.

- Les deux textes passent par le même extracteur (trafilatura, Markdown) :
  la mise en page, les images et les outils interactifs du champion ne sont
  pas jugés, seulement le fond et sa structure.
- Chaque juge lit les deux ordres (A/B puis B/A) pour annuler le biais de
  position ; notre article ne gagne un critère que s'il l'emporte en moyenne.
- Victoire : total plus élevé ET majorité des préférences « je publie ».
"""
from __future__ import annotations

import logging
import random
from typing import Callable
from urllib.parse import urlparse

from app.services.seo.html_text_ops import extract_json_object

logger = logging.getLogger(__name__)

CallFn = Callable[[str, str, float], str]

DUEL_CRITERIA = {
    "intent": "Répond vite et exactement à la question réelle du lecteur",
    "accuracy": "Exactitude, aucune erreur ni idée reçue, cohérence des chiffres",
    "sources": "Sources fiables et vérifiables, chiffres datés",
    "information_gain": "Apporte ce que les autres n'ont pas : exemple chiffré, méthode, cas par profil, avis d'expert",
    "depth": "Couvre les sous-questions utiles sans remplissage",
    "clarity": "Clarté, lisibilité, ton d'expert, facilité à parcourir",
    "structure": "Titres, tableaux, listes et composants utiles au lecteur",
    "freshness": "Données actuelles, aucune information périmée",
    "citability": "Facile à citer pour une IA de recherche (réponses autonomes, faits nets)",
    "retention": "Accroche dès les premières lignes et donne envie de lire jusqu'au bout (au moins 80 %) : "
                 "chaque section commence par ce que le lecteur veut savoir, aucun passage creux",
}
_EXCLUDED_HOST_PARTS = ("youtube.", "reddit.", "quora.", "facebook.", "linkedin.", "tiktok.", "instagram.",
                        "pinterest.", "twitter.", "x.com")


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def pick_champions(organic: list[dict], exclude_hosts: tuple[str, ...] = (), limit: int = 3) -> list[dict]:
    """Les `limit` premiers résultats organiques éditoriaux (pas de vidéo,
    forum ni réseau social, ni notre propre site)."""
    champions: list[dict] = []
    for item in organic or []:
        url = item.get("url") or item.get("link") or ""
        host = _host(url)
        if not host or any(p in host for p in _EXCLUDED_HOST_PARTS) or any(host.endswith(h) for h in exclude_hosts):
            continue
        champions.append({"url": url, "title": item.get("title", ""), "position": item.get("position")})
        if len(champions) >= limit:
            break
    return champions


def pick_champion(organic: list[dict], exclude_hosts: tuple[str, ...] = ()) -> dict | None:
    champions = pick_champions(organic, exclude_hosts, limit=1)
    return champions[0] if champions else None


def build_matrix_prompt(champions: list[tuple[str, str]], keyword: str) -> str:
    parts = [
        "Tu es rédacteur en chef. Ces articles sont les mieux classés sur Google pour la requête ci-dessous. "
        "Le n°1 n'est pas forcément le meilleur partout : identifie, sous-sujet par sous-sujet, quel article "
        "le traite le mieux et ce que contient cette meilleure version, puis ce qui manque à tous.",
        f"Requête : {keyword}",
        "",
        "Réponds UNIQUEMENT en JSON :",
        '{"subtopics": [{"subtopic": "...", "best": "C1|C2|C3", "best_version": "ce qui la rend la meilleure", '
        '"to_beat": "ce qu\'il faudrait faire pour faire mieux"}], "missing_everywhere": ["..."], '
        '"hook_patterns": ["comment le meilleur article accroche le lecteur dès le début"]}',
    ]
    for i, (url, md) in enumerate(champions, 1):
        parts += ["", f"=== C{i} ({url}) ===", md[:14000]]
    return "\n".join(parts)


def build_subtopic_matrix(champions: list[tuple[str, str]], keyword: str, call_fn: CallFn) -> dict:
    """Matrice « meilleure version de chaque sous-sujet » sur le top 3 :
    cible à battre section par section."""
    try:
        data = extract_json_object(call_fn(build_matrix_prompt(champions, keyword), "ChampionMatrix", 0.2))
    except Exception as exc:
        return {"error": str(exc)[:300]}
    return data if isinstance(data, dict) else {"error": "réponse JSON invalide"}


def to_markdown(html: str, url: str = "") -> str:
    """Normalisation commune des deux articles."""
    import trafilatura

    if "<html" not in (html or "").lower():
        html = f"<html><body><article>{html}</article></body></html>"
    text = trafilatura.extract(html, url=url or None, output_format="markdown", include_tables=True,
                               include_links=False, include_images=False, favor_recall=True)
    return (text or "").strip()


def build_dissection_prompt(champion_md: str, keyword: str) -> str:
    return "\n".join([
        "Tu es rédacteur en chef. Cet article est classé n°1 sur Google pour la requête ci-dessous. "
        "Analyse en expert pourquoi il réussit et où il est battable.",
        f"Requête : {keyword}",
        "",
        "Réponds UNIQUEMENT en JSON :",
        '{"why_it_wins": ["..."], "must_match": ["élément que notre article doit avoir aussi"], '
        '"weaknesses": ["faiblesse précise à exploiter"], "beat_plan": ["apport concret qui le dépasserait"], '
        '"structure": ["titres principaux dans l\'ordre"], "components": ["tableau, exemple chiffré, checklist…"], '
        '"word_count_estimate": 0}',
        "",
        "Article :",
        champion_md[:24000],
    ])


def dissect_champion(champion_md: str, keyword: str, call_fn: CallFn) -> dict:
    try:
        data = extract_json_object(call_fn(build_dissection_prompt(champion_md, keyword), "ChampionDissection", 0.2))
    except Exception as exc:
        return {"error": str(exc)[:300]}
    return data if isinstance(data, dict) else {"error": "réponse JSON invalide"}


def build_duel_prompt(first_md: str, second_md: str, keyword: str, reader_question: str) -> str:
    criteria = "\n".join(f"- {k} : {v}" for k, v in DUEL_CRITERIA.items())
    return "\n".join([
        "Tu es rédacteur en chef d'un média expert et lecteur exigeant. Compare deux articles qui répondent à la "
        "même requête. Tu ne sais pas qui les a écrits. Sois impartial et précis ; ignore la longueur en "
        "elle-même, seule compte l'utilité pour le lecteur.",
        f"Requête : {keyword}",
        f"Question réelle du lecteur : {reader_question or keyword}",
        "",
        "Note chaque article de 0 à 10 sur chaque critère :",
        criteria,
        "",
        "Puis réponds : lequel publierais-tu sous ton nom ? lequel le lecteur préférera-t-il ? lequel une IA de "
        "recherche citerait-elle ?",
        "",
        "Réponds UNIQUEMENT en JSON :",
        '{"scores": {"A": {"intent": 0, "...": 0}, "B": {"intent": 0, "...": 0}}, '
        '"publish": "A|B", "reader_prefers": "A|B", "ai_cites": "A|B", '
        '"a_better_at": ["..."], "b_better_at": ["..."], "verdict": "deux phrases"}',
        "",
        "=== ARTICLE A ===",
        first_md[:20000],
        "",
        "=== ARTICLE B ===",
        second_md[:20000],
    ])


def _side_scores(data: dict, side: str) -> dict[str, float]:
    raw = ((data.get("scores") or {}).get(side) or {}) if isinstance(data, dict) else {}
    out = {}
    for key in DUEL_CRITERIA:
        try:
            out[key] = max(0.0, min(10.0, float(raw.get(key))))
        except (TypeError, ValueError):
            out[key] = 0.0
    return out


def run_duel(ours_md: str, champion_md: str, keyword: str, reader_question: str,
             judges: list[tuple[str, CallFn]], rng: random.Random | None = None) -> dict:
    """Chaque juge lit les deux ordres. Retourne scores moyens, préférences
    et avantages exprimés pour chaque camp."""
    rng = rng or random.Random()
    rounds: list[dict] = []
    for name, call in judges:
        orders = [True, False]
        rng.shuffle(orders)
        for ours_first in orders:
            first, second = (ours_md, champion_md) if ours_first else (champion_md, ours_md)
            try:
                data = extract_json_object(call(build_duel_prompt(first, second, keyword, reader_question),
                                                f"ChampionDuel_{name}", 0.1))
            except Exception as exc:
                rounds.append({"judge": name, "error": str(exc)[:300]})
                continue
            if not isinstance(data, dict) or "scores" not in data:
                rounds.append({"judge": name, "error": "réponse JSON invalide"})
                continue
            ours_side, champ_side = ("A", "B") if ours_first else ("B", "A")
            rounds.append({
                "judge": name, "ours_first": ours_first,
                "ours": _side_scores(data, ours_side), "champion": _side_scores(data, champ_side),
                "publish_ours": str(data.get("publish", "")).strip().upper() == ours_side,
                "reader_ours": str(data.get("reader_prefers", "")).strip().upper() == ours_side,
                "ai_ours": str(data.get("ai_cites", "")).strip().upper() == ours_side,
                "ours_better_at": data.get(f"{ours_side.lower()}_better_at") or [],
                "champion_better_at": data.get(f"{champ_side.lower()}_better_at") or [],
                "verdict": str(data.get("verdict") or "")[:400],
            })
    valid = [r for r in rounds if "error" not in r]
    summary: dict = {"rounds": rounds, "valid_rounds": len(valid)}
    if not valid:
        return summary
    per_criterion = {
        key: {
            "ours": round(sum(r["ours"][key] for r in valid) / len(valid), 2),
            "champion": round(sum(r["champion"][key] for r in valid) / len(valid), 2),
        }
        for key in DUEL_CRITERIA
    }
    ours_total = round(sum(c["ours"] for c in per_criterion.values()), 1)
    champ_total = round(sum(c["champion"] for c in per_criterion.values()), 1)
    publish_rate = sum(r["publish_ours"] for r in valid) / len(valid)
    summary.update({
        "criteria": per_criterion,
        "ours_total": ours_total,
        "champion_total": champ_total,
        "publish_rate": round(publish_rate, 2),
        "reader_rate": round(sum(r["reader_ours"] for r in valid) / len(valid), 2),
        "ai_rate": round(sum(r["ai_ours"] for r in valid) / len(valid), 2),
        "losing_criteria": [k for k, c in per_criterion.items() if c["ours"] < c["champion"]],
        "won": ours_total > champ_total and publish_rate > 0.5,
    })
    return summary
