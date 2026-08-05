from __future__ import annotations

"""Score « Présence humaine » — détecte spécifiquement les signaux d'un
texte généré sans contrainte de style : phrases d'ouverture génériques,
tirets cadratins, régularité mécanique des paragraphes, absence de
position tranchée, absence de marqueur de voix humaine, conclusion qui
résume au lieu de clore sur une image. Règles issues du guide de
rédaction éditorial (checklist qualité 90+, voir guide_redaction_complet.md).

100% heuristique, aucun appel LLM — les signaux mesurables mécaniquement
(présence d'un mot, régularité d'une longueur) n'ont pas besoin de
jugement, contrairement à la qualité du raisonnement d'un article."""

import re

from app.services.seo.helpers import strip_html

GENERIC_OPENERS = (
    "dans l'univers numérique actuel", "dans le monde numérique actuel",
    "il est important de", "il est crucial de", "il est essentiel de",
    "force est de constater que", "dans un monde où", "à l'heure du digital",
    "à l'ère du digital", "la présence en ligne est devenue incontournable",
    "nombreux sont ceux qui", "nous allons voir dans cet article",
    "dans cette section", "dans cet article", "il convient de noter",
    "il va sans dire que", "de nos jours",
)

WORTHLESS_FILLER_PHRASES = (
    "il convient de noter que", "comme nous venons de le voir",
    "cela étant dit", "il va sans dire que",
)

EMPTY_SUPERLATIVES = (
    "ultime", "incontournable", "essentiel", "complet", "puissant",
    "booster", "révolutionnaire", "innovant",
)

WORN_EXPRESSIONS = (
    "le contenu est roi", "dans le paysage numérique actuel",
    "passer à la vitesse supérieure", "sortir du lot",
    "se démarquer de la concurrence",
)

HUMAN_MARKERS = (
    "honnêtement", "à bien y réfléchir", "curieusement", "sincèrement",
    "pourtant", "et ce n'est pas anodin", "et ce n'est pas une exagération",
    "et c'est normal", "ce que peu de gens réalisent",
    "vous l'avez peut-être", "c'est bien dommage", "croyez-moi",
    "et c'est presque toujours vrai", "tout compte fait",
    "pour être honnête", "en réalité", "malgré tout",
)

CONCLUSION_STARTERS = (
    "en conclusion", "pour conclure", "pour résumer", "en résumé",
    "nous avons vu que", "en somme",
)


def _extract_paragraphs(content: str) -> list[str]:
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", content, flags=re.IGNORECASE | re.DOTALL)
    return [strip_html(p).strip() for p in paragraphs if strip_html(p).strip()]


def _extract_sections(content: str) -> list[tuple[str, str]]:
    """Découpe le contenu en (titre_h2, texte_de_la_section) — le texte
    couvre tout ce qui suit un H2 jusqu'au prochain H2 (ou la fin)."""
    h2_positions = [
        (m.start(), re.sub(r"<[^>]+>", "", m.group(1)).strip())
        for m in re.finditer(r"<h2[^>]*>(.*?)</h2>", content, re.IGNORECASE | re.DOTALL)
    ]
    if not h2_positions:
        return [("", strip_html(content))]
    sections = []
    for i, (pos, heading) in enumerate(h2_positions):
        end = h2_positions[i + 1][0] if i + 1 < len(h2_positions) else len(content)
        section_html = content[pos:end]
        sections.append((heading, strip_html(section_html)))
    return sections


def score_intro_quality(content: str, word_count: int) -> tuple[float, list[str]]:
    paragraphs = _extract_paragraphs(content)
    if not paragraphs:
        return 50.0, []
    intro_text = " ".join(paragraphs[:2]).lower()
    intro_word_count = len(intro_text.split())

    flags = []
    score = 100.0
    for opener in GENERIC_OPENERS:
        if opener in intro_text:
            score -= 40.0
            flags.append(f"intro_generique:{opener}")
    if word_count and intro_word_count / word_count > 0.10:
        score -= 20.0
        flags.append("intro_trop_longue")
    return max(score, 0.0), flags


def score_vocabulary(content: str) -> tuple[float, list[str]]:
    text = strip_html(content).lower()
    flags = []
    hits = 0
    for phrase in WORTHLESS_FILLER_PHRASES + WORN_EXPRESSIONS:
        if phrase in text:
            hits += 1
            flags.append(f"expression_usee:{phrase}")
    for word in EMPTY_SUPERLATIVES:
        if re.search(rf"\b{re.escape(word)}\b", text):
            hits += 1
            flags.append(f"superlatif_vide:{word}")
    if "—" in content:
        hits += 1
        flags.append("tiret_cadratin_present")
    score = max(100.0 - hits * 15.0, 0.0)
    return score, flags


def score_paragraph_variation(content: str) -> tuple[float, list[str]]:
    paragraphs = _extract_paragraphs(content)
    lengths = [len(p.split()) for p in paragraphs]
    if len(lengths) < 4:
        return 70.0, []

    flags = []
    long_run = 0
    max_run = 0
    for length in lengths:
        bucket = "short" if length <= 15 else "long"
        long_run = long_run + 1 if bucket == "long" else 0
        max_run = max(max_run, long_run)
    if max_run >= 4:
        flags.append("paragraphes_longueur_uniforme")

    # Une phrase courte de rythme peut être un paragraphe entier court ou une
    # phrase brève à l'intérieur d'un paragraphe plus long (ex: "Ce n'est pas
    # une question de goût. C'est une question de comportement utilisateur.")
    # — chercher au niveau phrase, pas seulement au niveau paragraphe complet.
    has_short_punch = False
    for p in paragraphs:
        sentences = [s.strip() for s in re.split(r"[.!?]+", p) if s.strip()]
        if any(len(s.split()) <= 8 for s in sentences):
            has_short_punch = True
            break
    if not has_short_punch:
        flags.append("aucune_phrase_courte_de_rythme")

    score = 100.0
    if max_run >= 4:
        score -= 40.0
    elif max_run == 3:
        score -= 15.0
    if not has_short_punch:
        score -= 15.0
    return max(score, 0.0), flags


def score_human_markers(content: str) -> tuple[float, list[str]]:
    text = strip_html(content).lower()
    count = sum(1 for marker in HUMAN_MARKERS if marker in text)
    flags = []
    if count == 0:
        flags.append("aucun_marqueur_humain")
        return 20.0, flags
    if count == 1:
        return 70.0, flags
    if count <= 4:
        return 100.0, flags
    # Trop de marqueurs redevient mécanique — comme le note le guide, un
    # marqueur à chaque paragraphe est aussi artificiel que zéro marqueur.
    flags.append("marqueurs_humains_en_exces")
    return 60.0, flags


def score_section_positions(content: str) -> tuple[float, list[str]]:
    sections = _extract_sections(content)
    real_sections = [(h, t) for h, t in sections if h]
    if not real_sections:
        return 70.0, []

    # Une position tranchée est approximée par la présence d'un marqueur
    # d'opinion assumée ("mais", "en réalité", "ce n'est pas") combiné à une
    # tournure de contraste — heuristique volontairement permissive : un
    # faux négatif (section réellement tranchée non détectée) est préférable
    # à un faux positif qui pénaliserait à tort un bon article.
    opinion_markers = ("mais si ", "en réalité", "ce n'est pas ", "pas parce que", "c'est probablement le signal")
    sections_without_position = []
    for heading, text in real_sections:
        lowered = text.lower()
        if not any(marker in lowered for marker in opinion_markers):
            sections_without_position.append(heading[:40])

    ratio_missing = len(sections_without_position) / len(real_sections)
    score = max(100.0 - ratio_missing * 100.0, 0.0)
    flags = [f"section_sans_position_tranchee:{h}" for h in sections_without_position[:5]]
    return score, flags


def score_conclusion(content: str, word_count: int) -> tuple[float, list[str]]:
    paragraphs = _extract_paragraphs(content)
    if not paragraphs:
        return 70.0, []
    last_paragraphs = " ".join(paragraphs[-2:]).lower()
    flags = []
    score = 100.0
    for starter in CONCLUSION_STARTERS:
        if starter in last_paragraphs:
            score -= 50.0
            flags.append(f"conclusion_resume:{starter}")
    return max(score, 0.0), flags


def compute_human_presence_score(content: str | None, word_count: int | None = None) -> dict:
    if not content or len(strip_html(content).strip()) < 50:
        return {
            "score": None,
            "confidence": "low",
            "method": "rules",
            "signals": {},
            "flags": ["no_content"],
            "explanation": "Contenu insuffisant pour évaluer la présence humaine.",
            "version": "1.0",
        }

    wc = word_count or len(strip_html(content).split())

    intro_score, intro_flags = score_intro_quality(content, wc)
    vocab_score, vocab_flags = score_vocabulary(content)
    paragraph_score, paragraph_flags = score_paragraph_variation(content)
    marker_score, marker_flags = score_human_markers(content)
    position_score, position_flags = score_section_positions(content)
    conclusion_score, conclusion_flags = score_conclusion(content, wc)

    weights = {
        "intro": 0.20,
        "vocabulaire": 0.20,
        "paragraphes": 0.20,
        "marqueurs_humains": 0.15,
        "position_tranchee": 0.15,
        "conclusion": 0.10,
    }
    values = {
        "intro": intro_score,
        "vocabulaire": vocab_score,
        "paragraphes": paragraph_score,
        "marqueurs_humains": marker_score,
        "position_tranchee": position_score,
        "conclusion": conclusion_score,
    }
    final_score = sum(values[k] * weights[k] for k in weights)

    all_flags = intro_flags + vocab_flags + paragraph_flags + marker_flags + position_flags + conclusion_flags

    signals = {
        key: {
            "value": round(values[key]),
            "weight": weights[key],
            "contribution": round(values[key] * weights[key], 1),
        }
        for key in weights
    }

    return {
        "score": round(final_score),
        "confidence": "high",
        "method": "rules",
        "signals": signals,
        "flags": all_flags,
        "explanation": (
            f"Présence humaine {round(final_score)}/100. "
            + (f"Signaux détectés : {', '.join(all_flags[:6])}." if all_flags else "Aucun signal de texte générique détecté.")
        ),
        "version": "1.0",
    }


def compute_human_presence_score_dict(content: str | None, word_count: int | None = None) -> dict:
    return compute_human_presence_score(content, word_count)
