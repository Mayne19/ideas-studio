from __future__ import annotations

"""Garde-fous déterministes appliqués après la génération du contenu par le
writer LLM — le prompt (seo_generation_orchestrator._generate_content)
demande déjà un seul H1, pas de saut de niveau de titre et une plage de mots,
mais rien ne garantissait que le modèle respecte ces instructions. Ce module
corrige/rapporte ce que le LLM ignore, sans nouvel appel LLM."""

import re

_H_TAG_RE = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)

# Connecteurs de transition bannis par le prompt du writer (liste "Vocabulaire
# interdit", seo_generation_orchestrator._generate_content) : les récompenser
# dans un score (marqueurs de voix humaine, nuance EEAT, variété des connecteurs)
# contredirait directement la consigne donnée au rédacteur. Liste unique partagée
# par content_structure_guard, human_presence_service, eeat_service et
# article_reviewer_service pour rester synchronisée avec le prompt.
TRANSITION_BLACKLIST = (
    "en outre", "de plus", "par ailleurs", "néanmoins", "toutefois",
    "ainsi", "dès lors", "en somme", "en définitive", "d'autre part",
    "à cet égard", "en effet", "effectivement", "notamment", "de surcroît",
    "qui plus est", "honnêtement", "en réalité", "pourtant", "à bien y réfléchir",
)


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


_GENERIC_OPENERS = (
    "il est important de", "il est crucial de", "il est essentiel de",
    "dans cette section", "dans cet article", "nous allons voir",
    "force est de constater", "il va sans dire que", "de nos jours",
    "il convient de noter",
)
_H2_GENERIC_FIRST_WORDS = ("il", "dans", "nous", "cette")


def check_style_compliance(content: str) -> dict:
    """Signaux de style mesurables mécaniquement (checklist qualité 90+
    demandée par l'utilisateur) — ne corrige rien automatiquement, contraire-
    ment aux garde-fous structurels : reformuler une phrase creuse ou varier
    un rythme de paragraphe demande un jugement éditorial qu'une regex ne
    peut pas fournir sans risquer de dégrader le texte. Sert à qualifier
    l'article et, potentiellement, à nourrir une future itération
    d'auto-amélioration ciblée sur le style plutôt que sur les scores SEO."""
    if not content:
        return {"status": "empty", "issues": []}

    text_only = re.sub(r"<[^>]+>", " ", content)
    issues: list[str] = []

    if "—" in content:
        issues.append("tiret_cadratin_present")

    paragraphs = [p.strip() for p in re.findall(r"<p>(.*?)</p>", content, re.DOTALL) if re.sub(r"<[^>]+>", "", p).strip()]
    lengths = [len(re.sub(r"<[^>]+>", "", p).split()) for p in paragraphs]
    if len(lengths) >= 4:
        long_run = 0
        for length in lengths:
            bucket = "short" if length <= 15 else "long"
            long_run = long_run + 1 if bucket == "long" else 0
            if long_run >= 4:
                issues.append("paragraphes_longueur_uniforme")
                break

    for match in re.finditer(r"<h2[^>]*>(.*?)</h2>", content, re.IGNORECASE | re.DOTALL):
        heading_text = re.sub(r"<[^>]+>", "", match.group(1)).strip().lower()
        first_word = heading_text.split(" ", 1)[0] if heading_text else ""
        if first_word in _H2_GENERIC_FIRST_WORDS:
            issues.append(f"titre_section_generique:{heading_text[:40]}")

    lower_text = text_only.lower()
    for opener in _GENERIC_OPENERS:
        if opener in lower_text:
            issues.append(f"ouverture_generique:{opener}")

    # Connecteurs de transition bannis en début de phrase/paragraphe — le prompt
    # du writer les interdit ("Vocabulaire interdit"), les détecter ici permet
    # au réviseur (score_forbidden_absence) de les rendre bloquants, sans quoi
    # l'article pourrait passer toutes les passes de score en les conservant.
    transition_pattern = (
        "(" + "|".join(re.escape(c) for c in TRANSITION_BLACKLIST) + r")(?:[,:]|\.|!|\?)"
    )
    found_transitions: list[str] = []
    # début de texte ou après une ponctuation forte (phrase) — re.MULTILINE pour
    # couvrir aussi les débuts de ligne issus de la suppression des balises
    for match in re.finditer(r"(?:^|[.!?]\s+)\s*" + transition_pattern, text_only, re.IGNORECASE | re.MULTILINE):
        found_transitions.append(match.group(1).lower())
    # ouverture directe d'un paragraphe HTML (le writer est contraint à <p>)
    for match in re.finditer(r"<p[^>]*>\s*" + transition_pattern, content, re.IGNORECASE):
        found_transitions.append(match.group(1).lower())
    for connector in sorted(set(found_transitions)):
        issues.append(f"transition_creuse:{connector}")

    # Empilement : 2 phrases consécutives ouvertes par un connecteur banni (le
    # prompt interdit déjà tout connecteur de transition si un autre a été
    # utilisé dans les 3 phrases précédentes).
    sentences = [s.strip() for s in re.split(r"[.!?]+", text_only) if s.strip()]
    transition_run = 0
    for sentence in sentences:
        first_three = " ".join(sentence.split()[:3]).lower()
        if any(first_three.startswith(conn) for conn in TRANSITION_BLACKLIST):
            transition_run += 1
            if transition_run >= 2:
                issues.append("empilement_transitions")
                break
        else:
            transition_run = 0

    return {
        "status": "checked",
        "issues": issues,
        "paragraph_count": len(paragraphs),
        "issue_count": len(issues),
    }


def apply_structure_guards(content: str, title: str | None) -> str:
    """Point d'entrée unique : applique les corrections déterministes dans
    l'ordre (dédoublonnage H1 d'abord, puis cohérence de hiérarchie sur le
    résultat)."""
    content = strip_duplicate_h1(content, title)
    content = fix_heading_hierarchy(content)
    return content


def inject_missing_external_links(content: str, external_links_plan: dict | None) -> str:
    """Complète le maillage externe : si un lien du plan (construit en amont par
    external_link_service) n'apparaît nulle part dans le contenu, on l'ajoute
    sous forme d'un paragraphe neutre en fin d'article. Garde-fou mécanique
    (comme strip_duplicate_h1/fix_heading_hierarchy) : pas d'insertion
    "intelligente" par mot-clé — un ajout en fin d'article est préférable à un
    placement incohérent. Ne modifie rien si le contenu ou le plan est vide."""
    if not content or not external_links_plan:
        return content
    links = external_links_plan.get("links") or []
    missing = [l for l in links if isinstance(l, dict) and l.get("url") and l["url"] not in content]
    if not missing:
        return content
    additions = []
    for link in missing[:2]:  # cap à 2, pas de saturation
        anchor = (link.get("anchor_text") or "cette source").strip()
        additions.append(
            f'<p>Pour aller plus loin, voir <a href="{link["url"]}" '
            f'target="_blank" rel="nofollow">{anchor}</a>.</p>'
        )
    insertion_point = content.rfind("</p>")
    if insertion_point == -1:
        return content + "".join(additions)
    insertion_point += len("</p>")
    return content[:insertion_point] + "".join(additions) + content[insertion_point:]


_MARKDOWN_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_PARENTHETICAL_NOTE_RE = re.compile(r"\s*\([^)]*\bcaractères?\b[^)]*\)\s*$", re.IGNORECASE)


def clean_meta_text(raw: str | None, max_length: int) -> str:
    """Isole la vraie meta value d'une réponse LLM qui inclut souvent son
    raisonnement complet malgré la consigne ("Écris un meta title...") — un
    prompt sans contrainte de format explicite laisse le modèle répondre avec
    une intro ("Voici une proposition..."), le résultat en gras Markdown, puis
    une analyse ("**Analyse :**\n* Longueur : ..."), observé en production sur
    meta_title et meta_description. La ligne en gras (**...**) est presque
    toujours le vrai contenu demandé dans ce genre de réponse structurée —
    priorité sur elle ; à défaut, repli sur la première ligne de contenu qui
    n'est ni une intro/en-tête d'analyse ni une puce."""
    if not raw:
        return ""
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]

    bold_match = re.search(r"\*\*(.+?)\*\*", raw, re.DOTALL)
    if bold_match:
        candidate = _PARENTHETICAL_NOTE_RE.sub("", bold_match.group(1).strip())
        candidate = candidate.strip(" \"'")
        if candidate:
            return candidate[:max_length]

    for line in lines:
        if line in ("---", "***"):
            continue
        if re.match(r"^(\*\*)?(voici|analyse|longueur|mot-clé|note)\s*[:.]?", line, re.IGNORECASE):
            continue
        if line.startswith(("*", "-", "•")):
            continue
        cleaned = _MARKDOWN_BOLD_RE.sub(r"\1", line)
        cleaned = _PARENTHETICAL_NOTE_RE.sub("", cleaned)
        cleaned = cleaned.strip(" \"'")
        if cleaned:
            return cleaned[:max_length]
    return ""
