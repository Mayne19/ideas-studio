from __future__ import annotations

"""Prompt de la FAQ (A11, chaîne v2 étape 4).

Avant : la FAQ ne voyait que les 1 500 premiers caractères de l'article et
ignorait les « Autres questions posées » (PAA) renvoyées par Serper. Ici les
questions viennent d'abord de la SERP réelle (avec l'extrait de réponse de
Google comme matière), et le modèle voit un résumé de TOUT l'article (chaque
H2 et son premier paragraphe) pour ne pas répéter ce qui est déjà traité.
"""

import html as html_lib
import re

_H2_SPLIT_RE = re.compile(r"(<h2\b[^>]*>.*?</h2>)", re.IGNORECASE | re.DOTALL)
_P_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def article_digest(content: str, limit: int = 2800, per_section: int = 260) -> str:
    """Résumé structurel : introduction puis chaque H2 avec le début de son
    premier paragraphe. Couvre tout l'article, fin comprise."""
    parts = _H2_SPLIT_RE.split(content or "")
    lines: list[str] = []
    intro = _P_RE.search(parts[0]) if parts else None
    if intro:
        lines.append(f"Introduction : {_text(intro.group(1))[:per_section]}")
    for i in range(1, len(parts) - 1, 2):
        heading = _text(parts[i])
        first = _P_RE.search(parts[i + 1])
        body = _text(first.group(1))[:per_section] if first else ""
        lines.append(f"## {heading}" + (f" : {body}" if body else ""))
    return "\n".join(lines)[:limit]


def select_faq_questions(paa: list[dict], h2_texts: list[str], extra_questions: list[str] | None = None,
                         limit: int = 6) -> list[dict]:
    """Questions PAA (avec extrait) non déjà traitées par un H2, complétées
    par d'autres questions réelles si la SERP n'en fournit pas assez."""
    from app.services.seo.section_writer import headings_match

    selected: list[dict] = []
    seen: set[str] = set()
    for item in paa or []:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        if not question or question.lower() in seen:
            continue
        if any(headings_match(question, h) for h in h2_texts):
            continue
        seen.add(question.lower())
        selected.append({"question": question, "snippet": str(item.get("snippet") or "").strip(),
                         "url": str(item.get("url") or ""), "source": "people_also_ask"})
    for question in extra_questions or []:
        question = str(question or "").strip()
        if not question or question.lower() in seen or any(headings_match(question, h) for h in h2_texts):
            continue
        seen.add(question.lower())
        selected.append({"question": question, "snippet": "", "url": "", "source": "human_insights"})
    return selected[:limit]


def build_faq_prompt(title: str, keyword: str, content: str, questions: list[dict],
                     pains: list[str] | None = None) -> str:
    lines = [
        "Génère 3 à 5 questions fréquentes (FAQ) pour cet article.",
        f"Titre : {title}",
        f"Mot-clé principal : {keyword}",
        "",
        "Résumé de l'article (chaque section et son début) :",
        article_digest(content),
    ]
    if questions:
        lines += ["", "Questions réellement posées sur Google (« Autres questions posées ») : reprends-les "
                      "en priorité, reformulées si besoin. L'extrait est la réponse visible sur Google : "
                      "il peut servir de matière, sans le copier ni inventer de chiffre absent :"]
        for q in questions:
            line = f"- {q['question']}"
            if q.get("snippet"):
                line += f"\n  Extrait : {q['snippet'][:300]}"
            lines.append(line)
    if pains:
        lines += ["", "Difficultés réelles des utilisateurs :"] + [f"- {p}" for p in pains[:5]]
    lines += [
        "",
        "Règles strictes :",
        "- Chaque réponse : 1 à 4 phrases maximum",
        "- Les questions ne doivent pas répéter les titres H2 de l'article",
        "- Une réponse ne contredit jamais l'article",
        "- Réponses directes, sans formule introductive",
        "",
        'Réponds uniquement avec un objet JSON au format {"faq":[{"question":"...","answer":"..."}]}.',
    ]
    return "\n".join(lines)
