from __future__ import annotations

"""Garde-fous déterministes appliqués après la génération du contenu par le
writer LLM — le prompt (seo_generation_orchestrator._generate_content)
demande déjà un seul H1, pas de saut de niveau de titre et une plage de mots,
mais rien ne garantissait que le modèle respecte ces instructions. Ce module
corrige/rapporte ce que le LLM ignore, sans nouvel appel LLM."""

import re

_H_TAG_RE = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)


def strip_duplicate_h1(content: str, title: str | None) -> str:
    """Le titre de l'article vit déjà dans son propre champ (draft.title) —
    un <h1> dans le corps du contenu est donc toujours un doublon (que le
    writer LLM ignore régulièrement malgré l'instruction). On retire tout
    <h1>, en promouvant un éventuel deuxième <h1> résiduel en <h2> plutôt que
    de le supprimer (peut porter du contenu réel plutôt qu'être un pur doublon
    du titre)."""
    if not content or "<h1" not in content.lower():
        return content

    matches = list(_H_TAG_RE.finditer(content))
    h1_matches = [m for m in matches if m.group(1) == "1"]
    if not h1_matches:
        return content

    result = content
    for match in reversed(h1_matches):
        inner_text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        is_title_duplicate = not title or inner_text.strip().lower() == title.strip().lower()
        replacement = "" if is_title_duplicate else f"<h2>{match.group(2)}</h2>"
        result = result[: match.start()] + replacement + result[match.end() :]
    return result


def fix_heading_hierarchy(content: str) -> str:
    """Corrige les sauts de niveau de titre invalides (H2 -> H4 sans H3
    intermédiaire, H3 -> H5, etc.) en ramenant chaque titre au niveau
    immédiatement inférieur au précédent le plus proche. Ne touche jamais un
    H2 (niveau de section racine) ni un titre déjà cohérent."""
    if not content:
        return content

    matches = list(_H_TAG_RE.finditer(content))
    if not matches:
        return content

    result = content
    offset = 0
    last_level = 2
    for match in matches:
        level = int(match.group(1))
        if level > 2 and level > last_level + 1:
            corrected_level = last_level + 1
            start, end = match.start() + offset, match.end() + offset
            new_tag = f"<h{corrected_level}>{match.group(2)}</h{corrected_level}>"
            result = result[:start] + new_tag + result[end:]
            offset += len(new_tag) - (end - start)
            level = corrected_level
        last_level = level
    return result


def check_word_count_compliance(word_count: int, wc_min: int | None, wc_max: int | None) -> dict:
    """Rapporte un dépassement de la plage configurée — ne modifie jamais le
    contenu (raccourcir/rallonger un article automatiquement dégraderait sa
    qualité éditoriale plus sûrement qu'un dépassement de volume ne le fait)."""
    if not wc_min and not wc_max:
        return {"status": "no_target", "word_count": word_count}
    if wc_min and word_count < wc_min:
        return {
            "status": "under_minimum", "word_count": word_count,
            "target_min": wc_min, "target_max": wc_max,
            "deviation_pct": round((wc_min - word_count) / wc_min * 100, 1),
        }
    if wc_max and word_count > wc_max:
        return {
            "status": "over_maximum", "word_count": word_count,
            "target_min": wc_min, "target_max": wc_max,
            "deviation_pct": round((word_count - wc_max) / wc_max * 100, 1),
        }
    return {"status": "within_range", "word_count": word_count, "target_min": wc_min, "target_max": wc_max}


def apply_structure_guards(content: str, title: str | None) -> str:
    """Point d'entrée unique : applique les corrections déterministes dans
    l'ordre (dédoublonnage H1 d'abord, puis cohérence de hiérarchie sur le
    résultat)."""
    content = strip_duplicate_h1(content, title)
    content = fix_heading_hierarchy(content)
    return content
