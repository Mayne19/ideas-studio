"""Concepteur du gain d'information (chaîne v2, chantier 2).

Avant le plan, un appel conçoit ce qui a fait gagner les articles validés par
le fondateur : réponse directe, piège que le lecteur ne voit pas, promesse
concrète, outil de décision, exemple chiffré calculé, fait surprenant sourcé,
erreurs fréquentes, contradictions et manques des concurrents. Le code
vérifie les identifiants de faits et les calculs simples ; les éléments sont
ensuite affectés à une section du plan (assign_gain_elements) et transmis au
rédacteur et au juge.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Callable

from app.services.seo.html_text_ops import extract_json_object

logger = logging.getLogger(__name__)

CallFn = Callable[[str, str, float], str]
MAX_FACTS = 40


def build_design_prompt(keyword: str, reader_question: str, facts: list[dict],
                        competitors: list[dict], matrix: dict | None = None) -> str:
    lines = [
        "Tu es rédacteur en chef. Avant d'écrire, conçois ce qui rendra cet article plus utile que tous ceux "
        "déjà classés sur Google.",
        f"Requête : {keyword}",
        f"Question réelle du lecteur : {reader_question or keyword}",
        "",
        "Faits vérifiés (identifiant, énoncé, chiffre) :",
    ]
    for f in facts[:MAX_FACTS]:
        lines.append(f"- {f.get('fact_id')} : {str(f.get('claim', ''))[:200]}"
                     + (f" (chiffre : {f['figure']})" if f.get("figure") else ""))
    if competitors:
        lines += ["", "Pages concurrentes (titre : extrait) :"]
        lines += [f"- {c.get('title', '')} : {str(c.get('snippet', ''))[:220]}" for c in competitors[:8]]
    if matrix and not matrix.get("error"):
        lines += ["", "Analyse des concurrents : " + str(matrix)[:2500]]
    lines += [
        "",
        "Règles : chaque chiffre de worked_example vient des faits ou d'un calcul montré étape par étape, avec "
        "des opérations simples (« 39 / 100 = 0,39 »), ou d'un montant rond annoncé comme exemple ; "
        "surprising_fact cite un fact_id existant ; competitor_contradictions reste vide si les sources ne se "
        "contredisent pas ; n'invente rien.",
        "",
        "Réponds UNIQUEMENT en JSON :",
        '{"direct_answer": "réponse à la question en 2 phrases maximum", '
        '"trap": "le piège que le lecteur ne voit pas, appuyé sur un fait vérifié", '
        '"promise": "une phrase : ce que l\'article donne concrètement au lecteur", '
        '"competitor_contradictions": ["..."], "competitor_gaps": ["ce qu\'aucun concurrent ne traite"], '
        '"decision_tool": {"type": "tableau de diagnostic | tableau de décision | grille", "columns": ["..."], '
        '"rows": [["..."]]}, '
        '"worked_example": {"situation": "cas concret", "calculation": ["étape de calcul"], "result": "résultat"}, '
        '"surprising_fact": {"fact": "...", "fact_id": "F3"}, '
        '"common_mistakes": ["erreur fréquente et sa conséquence"]}',
    ]
    return "\n".join(lines)


_NUM = r"(\d+(?:[  ]\d{3})*(?:[.,]\d+)?)"
_CALC_RE = re.compile(_NUM + r"\s*([+\-x×*/÷])\s*" + _NUM + r"\s*=\s*" + _NUM)
_PCT_RE = re.compile(_NUM + r"\s*%\s*(?:de|of|×|x|\*)\s*" + _NUM + r"[^=]*=\s*" + _NUM)


def _to_float(text: str) -> float:
    return float(re.sub(r"[  ]", "", text).replace(",", "."))


def check_calculations(steps: list[str]) -> list[str]:
    """Calculs simples faux dans les étapes (a op b = c, x % de y = z)."""
    wrong: list[str] = []
    for step in steps or []:
        text = str(step)
        for a, op, b, c in _CALC_RE.findall(text):
            x, y, z = _to_float(a), _to_float(b), _to_float(c)
            expected = {"+": x + y, "-": x - y, "x": x * y, "×": x * y, "*": x * y,
                        "/": x / y if y else None, "÷": x / y if y else None}[op]
            if expected is None or abs(expected - z) > max(0.02, abs(expected) * 0.01):
                wrong.append(text)
        for p, base, result in _PCT_RE.findall(text):
            expected = _to_float(p) / 100 * _to_float(base)
            if abs(expected - _to_float(result)) > max(0.02, abs(expected) * 0.01):
                wrong.append(text)
    return wrong


def validate_design(data: dict, known_fact_ids: set[str]) -> tuple[dict, list[str]]:
    """Retire ce qui est invérifiable ; retourne (design, problèmes)."""
    problems: list[str] = []
    design = {k: data.get(k) for k in (
        "direct_answer", "trap", "promise", "competitor_contradictions", "competitor_gaps",
        "decision_tool", "worked_example", "surprising_fact", "common_mistakes")}
    fact = design.get("surprising_fact")
    if isinstance(fact, dict) and str(fact.get("fact_id") or "") not in known_fact_ids:
        problems.append(f"fait surprenant sans identifiant connu ({fact.get('fact_id')})")
        design["surprising_fact"] = None
    example = design.get("worked_example")
    if isinstance(example, dict):
        wrong = check_calculations(example.get("calculation") or [])
        if wrong:
            problems.append("calcul faux : " + " | ".join(wrong[:2]))
    else:
        design["worked_example"] = None
    tool = design.get("decision_tool")
    if not (isinstance(tool, dict) and tool.get("columns") and tool.get("rows")):
        design["decision_tool"] = None
    for key in ("competitor_contradictions", "competitor_gaps", "common_mistakes"):
        design[key] = [str(x) for x in design.get(key) or [] if str(x).strip()][:5]
    return design, problems


def design_information_gain(keyword: str, reader_question: str, facts: list[dict], competitors: list[dict],
                            call_fn: CallFn, matrix: dict | None = None,
                            fatal_exceptions: tuple[type[BaseException], ...] = ()) -> dict:
    """Un appel ; un second si un calcul est faux, puis l'exemple est retiré."""
    known = {str(f.get("fact_id")) for f in facts if f.get("fact_id")}
    prompt = build_design_prompt(keyword, reader_question, facts, competitors, matrix)
    report: dict = {"design": None, "problems": [], "attempts": 0, "error": None}
    for attempt in range(2):
        report["attempts"] += 1
        try:
            raw = call_fn(prompt, "InformationGainDesign", 0.4)
        except fatal_exceptions:
            raise
        except Exception as exc:
            logger.warning("information_gain: appel en échec : %s", exc)
            report["error"] = str(exc)[:300]
            return report
        data = extract_json_object(raw)
        if not isinstance(data, dict):
            report["error"] = "réponse JSON invalide"
            continue
        design, problems = validate_design(data, known)
        report["problems"] = problems
        report["design"] = design
        if not any(p.startswith("calcul faux") for p in problems):
            return report
    if report["design"] and any(p.startswith("calcul faux") for p in report["problems"]):
        report["design"]["worked_example"] = None
    return report


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _pick(headings: list[str], hints: tuple[str, ...], used: set[int], fallback: int) -> int:
    for i, h in enumerate(headings):
        if i not in used and any(hint in _norm(h) for hint in hints):
            return i
    return fallback


def assign_gain_elements(design: dict | None, headings: list[str]) -> dict:
    """{"intro": {...}, index de section: {...}} : chaque élément conçu va à
    une seule section, choisie d'après son titre."""
    if not design or not headings:
        return {}
    out: dict = {"intro": {k: design.get(k) for k in ("direct_answer", "trap", "promise") if design.get(k)}}
    used: set[int] = set()
    last = len(headings) - 1
    placements = (
        ("decision_tool", ("choisir", "comparer", "compar", "quel", "lequel", "diagnostic", "selon", "tableau"), 0),
        ("worked_example", ("prix", "cout", "budget", "combien", "exemple", "calcul", "tarif"), min(1, last)),
        ("common_mistakes", ("erreur", "piege", "eviter", "limite", "attention", "vigilance"), last),
        ("surprising_fact", ("pourquoi", "comment", "fonctionne"), min(1, last)),
    )
    for key, hints, fallback in placements:
        if not design.get(key):
            continue
        index = _pick(headings, hints, used, fallback)
        used.add(index)
        out.setdefault(index, {})[key] = design[key]
    return out


def format_gain_block(elements: dict) -> str:
    """Consignes de rédaction pour les éléments affectés à une section."""
    if not elements:
        return ""
    lines = ["Éléments à intégrer dans cette partie (conçus avant la rédaction, à rédiger avec tes mots) :"]
    if elements.get("direct_answer"):
        lines.append(f"- Réponse directe : {elements['direct_answer']}")
    if elements.get("trap"):
        lines.append(f"- Piège à poser : {elements['trap']}")
    if elements.get("promise"):
        lines.append(f"- Promesse (une phrase) : {elements['promise']}")
    tool = elements.get("decision_tool")
    if tool:
        lines.append(f"- Outil de décision ({tool.get('type', 'tableau')}) en <table> avec <th> : colonnes "
                     f"{tool.get('columns')} ; lignes {tool.get('rows')}")
    example = elements.get("worked_example")
    if example:
        lines.append(f"- Exemple chiffré : {example.get('situation')} ; calcul montré : "
                     f"{' ; '.join(map(str, example.get('calculation') or []))} ; résultat : {example.get('result')}")
    fact = elements.get("surprising_fact")
    if fact:
        lines.append(f"- Fait surprenant : {fact.get('fact')} [{fact.get('fact_id')}]")
    if elements.get("common_mistakes"):
        lines.append("- Erreurs fréquentes, chacune avec sa conséquence : " + " ; ".join(elements["common_mistakes"]))
    return "\n".join(lines)
