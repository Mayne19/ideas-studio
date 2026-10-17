"""Juge éditorial v2 : grille sur 100 du rédacteur en chef (2026-10-17),
étalonnée sur les notes humaines (scripts d'étalonnage : gpt/judge-calibration).

Le code mesure ce qui se compte (forme, SEO technique, longueur des phrases,
phrases hachées, citations absentes des faits, équilibre des sources) ; le
modèle ne juge que ce qui demande de la compréhension, avec ces mesures sous
les yeux. Plafonds : une faute grave limite la note à 85, deux ou plus à 75.

Critères (points) :
- exactitude et sources (E-E-A-T) 20, apport d'information et originalité 15,
  lisibilité et clarté 15, réponse et intention 10, introduction 10,
  structure et promesses 10, ton et engagement 5, FAQ 5 : notés par le modèle ;
- SEO technique 5, forme 5 : calculés par le code.
"""
from __future__ import annotations

import logging
import re
from typing import Callable

from app.services.seo.html_text_ops import extract_json_object

logger = logging.getLogger(__name__)

CallFn = Callable[[str, str, float], str]

MODEL_CRITERIA: dict[str, tuple[int, str]] = {
    "accuracy_sources": (20, "Exactitude et sources (E-E-A-T) : faits cités mot pour mot, sources primaires, aucun "
                             "fait inventé, aucune contradiction, équilibre des sources"),
    "information_gain": (15, "Apport d'information et originalité : au moins deux éléments absents des concurrents "
                             "(outil de décision, calcul vérifié, fait contre-intuitif)"),
    "readability": (15, "Lisibilité et clarté : phrases reliées, aucune phrase isolée sans lien avec les autres, "
                        "mots simples, termes techniques expliqués, ni phrases hachées, ni personnification, ni excès "
                        "de modalisateurs, aucune ouverture interdite (« Voici », « Le principe est simple », "
                        "« Le piège consiste à », « Imaginez », « Franchement »), aucune phrase qui commente l'article "
                        "lui-même (« cet article », « les sources consultées », « nous retenons »)"),
    "intent": (10, "Réponse et intention de recherche : réponse dans les 60 premiers mots, besoin réel du lecteur "
                   "couvert"),
    "introduction": (10, "Introduction : l'idée générale part du moment que vit le lecteur et lui donne tout de "
                         "suite quoi faire (jamais une définition ni une explication technique en première phrase) ; "
                         "la problématique découle logiquement de cette idée et décrit le doute concret du lecteur ; "
                         "l'annonce promet un gain précis, pas une liste neutre de sujets"),
    "structure": (10, "Structure et promesses : chaque titre correspond à sa section, nombres annoncés justes, "
                      "aucune répétition, conclusion avant la FAQ"),
    "tone": (5, "Ton et engagement : calme, « vous » qui responsabilise, une scène vécue"),
    "faq": (5, "FAQ : questions absentes du corps, réponses directes"),
}
CODE_CRITERIA: dict[str, tuple[int, str]] = {
    "seo": (5, "SEO technique : titre, meta, slug, un seul lien par source, liens internes"),
    "form": (5, "Forme : mots interdits, tiret long, typographie"),
}
GRAVE_FAULT_TYPES = ("false_fact", "central_contradiction", "competitor_named", "unsourced_health_figure")
CAP_ONE_GRAVE = 85
CAP_TWO_GRAVE = 75
CALIBRATION_STATUS = "non étalonné"  # passe à « étalonné » quand le script d'étalonnage valide les seuils


def split_title(content: str, title: str = "") -> tuple[str, str]:
    """Un article Markdown d'étalonnage commence souvent par « # Titre » : ce
    titre devient le H1 (hors corps), comme dans le CMS."""
    m = re.match(r"\s*#\s+(.+?)\s*\n", content or "")
    if m and not re.search(r"<(p|h2)\b", content, re.IGNORECASE):
        return content[m.end():], title or m.group(1).strip()
    return content, title


def ensure_html(content: str) -> str:
    """Les articles d'étalonnage sont en Markdown ; le juge lit du HTML."""
    if re.search(r"<(p|h2|ul|ol|table)\b", content or "", re.IGNORECASE):
        return content
    import markdown

    return markdown.markdown(content or "", extensions=["tables"])


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip().split()) >= 1]


def measurements(content: str, *, title: str = "", facts: list[dict] | None = None, faq: list[dict] | None = None,
                 meta_title: str = "", meta_description: str = "", slug: str = "") -> dict:
    """Mesures déterministes, sans modèle."""
    from app.services.seo.agent_generation import link_errors, quote_errors, source_balance_errors, structure_errors
    from app.services.seo.html_text_ops import html_to_text

    html = ensure_html(content)
    text = html_to_text(html)
    sentences = _sentences(text)
    lengths = [len(s.split()) for s in sentences] or [0]
    choppy_runs = 0
    run = 0
    for n in lengths:
        run = run + 1 if n <= 6 else 0
        if run == 3:
            choppy_runs += 1
    candidate = {"content_html": html, "facts": facts or []}
    form_faults = structure_errors(html, title or "Article")
    seo_faults = list(link_errors(html))
    if meta_title and len(meta_title) > 60:
        seo_faults.append(f"meta title de {len(meta_title)} caractères (60 au plus)")
    if meta_description and not 120 <= len(meta_description) <= 165:
        seo_faults.append(f"meta description de {len(meta_description)} caractères (120 à 165)")
    if slug and (len(slug) > 75 or not re.fullmatch(r"[a-z0-9-]+", slug)):
        seo_faults.append(f"slug « {slug} » non conforme")
    return {
        "words": len(text.split()),
        "sentences": len(sentences),
        "avg_sentence_words": round(sum(lengths) / max(len(lengths), 1), 1),
        "long_sentences": sum(1 for n in lengths if n > 30),
        "choppy_runs": choppy_runs,
        "quote_faults": quote_errors(candidate) if facts else [],
        "balance_faults": source_balance_errors(candidate) if facts else [],
        "form_faults": form_faults,
        "seo_faults": seo_faults,
        "faq_count": len(faq or []),
    }


def code_scores(measured: dict) -> dict:
    form_max, seo_max = CODE_CRITERIA["form"][0], CODE_CRITERIA["seo"][0]
    return {
        "form": {"score": max(0.0, form_max - 1.5 * len(measured["form_faults"])), "max": form_max,
                 "evidence": " | ".join(measured["form_faults"]) or "aucune faute de forme"},
        "seo": {"score": max(0.0, seo_max - 1.0 * len(measured["seo_faults"])), "max": seo_max,
                "evidence": " | ".join(measured["seo_faults"]) or "aucune faute SEO technique"},
    }


def build_prompt(content: str, *, title: str, keyword: str, measured: dict, facts: list[str],
                 competitors: list[str], faq: list[dict]) -> str:
    from app.services.seo.editorial_judge import article_digest

    criteria = "\n".join(f"- {k} (sur {pts}) : {desc}" for k, (pts, desc) in MODEL_CRITERIA.items())
    faq_lines = "\n".join(f"- Q : {f.get('question', '')}\n  R : {f.get('answer', '')}" for f in faq or []) or "- aucune"
    fact_block = "\n".join(f"- {f}" for f in facts[:40]) or (
        "- aucune liste fournie : juge les sources d'après les liens et attributions présents dans l'article. "
        "N'exige aucune citation mot pour mot et ne retire aucun point pour l'absence de liste de faits.")
    return "\n".join([
        "Tu es le rédacteur en chef d'un site éditorial français. Tu notes un article de blog avec une grille stricte, "
        "pour un lecteur débutant qui veut une réponse fiable et agréable à lire. Un article noté 90 est publiable "
        "tel quel ; 80 est bon mais a des défauts visibles ; 60 est un contenu moyen du web.",
        f"Mot-clé : {keyword}", f"Titre : {title}", "",
        "Critères à noter (entiers, de 0 au maximum indiqué), avec une preuve courte tirée du texte :", criteria, "",
        "Fautes graves à lister (chacune limite la note finale) : false_fact (fait faux), central_contradiction "
        "(contradiction sur le conseil central), competitor_named (site concurrent nommé ou lié), "
        "unsourced_health_figure (chiffre de santé sans source). Un nombre obtenu par un calcul montré ou présenté "
        "comme exemple n'est pas non sourcé. N'invente pas de faute : en cas de doute, ce n'en est pas une.", "",
        "Mesures du code (fiables, utilise-les comme preuves) :",
        f"- {measured['words']} mots, {measured['sentences']} phrases, {measured['avg_sentence_words']} mots par "
        f"phrase en moyenne, {measured['long_sentences']} phrases de plus de 30 mots, {measured['choppy_runs']} "
        "séries d'au moins trois phrases très courtes (effet haché)",
        f"- citations absentes des faits : {' | '.join(measured['quote_faults']) or 'aucune'}",
        f"- équilibre des sources : {' | '.join(measured['balance_faults']) or 'correct'}", "",
        "Faits vérifiés de l'article (citation exacte et source) :", fact_block, "",
        f"Concurrents (ne doivent jamais être nommés ni liés) : {', '.join(competitors) or 'non fournis'}", "",
        "FAQ :", faq_lines, "",
        "Réponds uniquement par ce JSON :",
        '{"criteria": {"accuracy_sources": {"score": 0, "evidence": "..."}, "information_gain": {...}, '
        '"readability": {...}, "intent": {...}, "introduction": {...}, "structure": {...}, "tone": {...}, '
        '"faq": {...}}, "grave_faults": [{"type": "false_fact", "passage": "texte exact", "detail": "..."}], '
        '"summary": "deux phrases"}', "",
        "Article :", article_digest(ensure_html(content)),
    ])


def apply_caps(total: float, grave_faults: list[dict]) -> tuple[float, dict]:
    n = len(grave_faults)
    cap = CAP_TWO_GRAVE if n >= 2 else CAP_ONE_GRAVE if n == 1 else None
    return (min(total, cap) if cap is not None else total), {"grave_faults": n, "cap": cap}


def judge_v2(content: str, call_fn: CallFn, *, title: str = "", keyword: str = "", facts: list[dict] | None = None,
             competitors: list[str] | None = None, faq: list[dict] | None = None, meta_title: str = "",
             meta_description: str = "", slug: str = "") -> dict:
    """Note sur 100 : {"total", "criteria", "caps", "grave_faults", "measurements", "status"} ;
    {"error": ...} si l'appel ou le JSON échoue."""
    from app.services.seo.agent_generation import fact_lines

    content, title = split_title(content, title)
    measured = measurements(content, title=title, facts=facts, faq=faq, meta_title=meta_title,
                            meta_description=meta_description, slug=slug)
    prompt = build_prompt(content, title=title, keyword=keyword, measured=measured,
                          facts=fact_lines({"facts": facts or []}), competitors=competitors or [], faq=faq or [])
    try:
        data = extract_json_object(call_fn(prompt, "Juge éditorial v2", 0.1)) or {}
    except Exception as exc:
        logger.warning("judge_v2 : appel en échec : %s", exc)
        return {"error": str(exc)[:300], "measurements": measured}
    raw = data.get("criteria") if isinstance(data.get("criteria"), dict) else {}
    if not raw:
        return {"error": "JSON du juge inexploitable", "measurements": measured}
    criteria: dict[str, dict] = {}
    for key, (pts, _desc) in MODEL_CRITERIA.items():
        item = raw.get(key) if isinstance(raw.get(key), dict) else {}
        try:
            score = float(item.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        criteria[key] = {"score": max(0.0, min(float(pts), score)), "max": pts,
                         "evidence": str(item.get("evidence") or "")[:400]}
    criteria |= code_scores(measured)
    grave = [{"type": str(g.get("type")), "passage": str(g.get("passage") or "")[:300],
              "detail": str(g.get("detail") or "")[:300]}
             for g in data.get("grave_faults") or [] if isinstance(g, dict) and g.get("type") in GRAVE_FAULT_TYPES]
    raw_total = round(sum(c["score"] for c in criteria.values()), 1)
    total, caps = apply_caps(raw_total, grave)
    return {"total": round(total, 1), "raw_total": raw_total, "criteria": criteria, "caps": caps,
            "grave_faults": grave, "measurements": measured, "summary": str(data.get("summary") or "")[:600],
            "status": CALIBRATION_STATUS}
