from __future__ import annotations

"""Validateur de structure déterministe (demande du fondateur).

Contrôle le HTML final contre les règles éditoriales de
docs/GUIDE-REDACTION-EDITORIAL.md et des garde-fous existants
(content_structure_guard, editorial_quality_gate, format_expectations) :
un seul H1 (le titre, jamais dans le corps), hiérarchie H2/H3, longueur des
paragraphes et des phrases, variation des paragraphes, longueur de
l'introduction, listes et tableaux, équilibre des sections, composants
attendus selon le format recommandé.

Chaque règle produit pass/fail et des emplacements ({unit, excerpt,
detail}). Les règles `hard` peuvent déclencher une correction ciblée par
section (voir structure_fixer). Aucun appel LLM ici.
"""

import re
from dataclasses import dataclass

from app.services.seo.html_text_ops import html_to_text, split_units, unit_heading

HARD = "hard"
WARNING = "warning"

# Seuils (guide §1.1, §1.5, §1.7 et prompt système du rédacteur :
# « paragraphes courts, 1 à 4 phrases »).
MAX_SENTENCES_PER_PARAGRAPH = 5
MAX_WORDS_PER_PARAGRAPH = 120
MAX_WORDS_PER_SENTENCE = 45
LONG_SENTENCE_WORDS = 30
LONG_SENTENCE_SHARE = 0.25
UNIFORM_RUN = 4
UNIFORM_TOLERANCE = 0.2
INTRO_MAX_SHARE = 0.10
INTRO_MIN_ARTICLE_WORDS = 600  # en dessous, la règle des 10 % est trop serrée
INTRO_MAX_WORDS_SHORT = 120
MAX_LIST_ITEMS = 10
MAX_LIST_ITEM_WORDS = 40
SECTION_MIN_WORDS = 60
SECTION_BALANCE_RATIO = 3.0

# Guide §1.1 : ouvertures d'introduction interdites.
GENERIC_INTRO_OPENERS = (
    "dans l'univers numérique", "il est important de", "force est de constater", "dans un monde où",
    "à l'heure du digital", "la présence en ligne est devenue", "nombreux sont ceux qui",
    "nous allons voir", "dans cet article",
)
# Guide §1.3 : superlatifs vides et expressions usées (zéro occurrence).
BANNED_WORDS = (
    "ultime", "incontournable", "incontournables", "révolutionnaire", "révolutionnaires", "booster",
    "innovant", "innovante", "innovants", "innovantes",
)
BANNED_EXPRESSIONS = (
    "le contenu est roi", "dans le paysage numérique actuel", "à l'ère du digital",
    "passer à la vitesse supérieure", "sortir du lot", "se démarquer de la concurrence",
    # Retours du fondateur (2026-10-16) : marqueurs de texte généré.
    "imaginez", "franchement", "curieusement", "c'est ce qui fait la différence", "le saviez-vous",
)
# Guide §1.10 : ouvertures de conclusion interdites.
CONCLUSION_OPENERS = ("en conclusion", "pour résumer", "pour conclure", "en résumé", "nous avons vu que")

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[\"«(\[]?[A-ZÀ-ÖØ-Ý0-9])")
_P_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_HEADING_RE = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_LIST_RE = re.compile(r"<(ul|ol)\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
_LI_RE = re.compile(r"<li\b[^>]*>(.*?)</li>", re.IGNORECASE | re.DOTALL)
_TABLE_RE = re.compile(r"<table\b[^>]*>(.*?)</table>", re.IGNORECASE | re.DOTALL)
_TR_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
_CELL_RE = re.compile(r"<(td|th)\b([^>]*)>", re.IGNORECASE)
_FIGURE_RE = re.compile(r"<figure\b.*?</figure>", re.IGNORECASE | re.DOTALL)
_WORD_RE = re.compile(r"\w+(?:['’-]\w+)*", re.UNICODE)


def _words(text: str) -> int:
    return len(_WORD_RE.findall(text or ""))


def split_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()] if text else []


def _excerpt(text: str, limit: int = 90) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


@dataclass
class Unit:
    key: str        # "intro" ou "section:<n>"
    heading: str
    html: str

    @property
    def label(self) -> str:
        return "Introduction" if self.key == "intro" else self.heading


def article_units(content: str) -> list[Unit]:
    content = _FIGURE_RE.sub("", content or "")
    units = split_units(content)
    out = [Unit("intro", "", units[0])]
    for i, unit in enumerate(units[1:], start=1):
        out.append(Unit(f"section:{i}", unit_heading(unit), unit))
    return out


def _loc(unit: Unit, detail: str, excerpt: str = "") -> dict:
    return {"unit": unit.key, "section": unit.label, "detail": detail, "excerpt": _excerpt(excerpt)}


def _rule(rule: str, label: str, severity: str, violations: list[dict], fixable: bool = True) -> dict:
    return {
        "rule": rule, "label": label, "severity": severity, "passed": not violations,
        "violations": violations, "section_fixable": fixable,
    }


# ── Règles ───────────────────────────────────────────────────────────────────

def check_h1(content: str, title: str | None) -> dict:
    violations = []
    h1s = re.findall(r"<h1\b[^>]*>(.*?)</h1>", content or "", re.IGNORECASE | re.DOTALL)
    if not (title or "").strip():
        violations.append({"unit": "title", "section": "Titre", "detail": "Titre (H1) absent", "excerpt": ""})
    for h1 in h1s:
        violations.append({"unit": "body", "section": "Corps", "detail": "H1 dans le corps : le titre est déjà le H1",
                           "excerpt": _excerpt(html_to_text(h1))})
    return _rule("single_h1", "Un seul H1 (le titre), jamais dans le corps", HARD, violations, fixable=False)


def check_heading_hierarchy(content: str) -> dict:
    violations = []
    previous = 1
    seen_h2 = False
    for m in _HEADING_RE.finditer(_FIGURE_RE.sub("", content or "")):
        level = int(m.group(1))
        text = html_to_text(m.group(2))
        if level == 1:
            continue
        if level >= 5:
            violations.append({"unit": "body", "section": text, "detail": f"H{level} interdit (H2 et H3 seulement)",
                               "excerpt": _excerpt(text)})
        if level == 3 and not seen_h2:
            violations.append({"unit": "body", "section": text, "detail": "H3 sans H2 parent", "excerpt": _excerpt(text)})
        if level > previous + 1:
            violations.append({"unit": "body", "section": text,
                               "detail": f"Niveau sauté : H{previous} puis H{level}", "excerpt": _excerpt(text)})
        if level == 2:
            seen_h2 = True
        previous = level
    return _rule("heading_hierarchy", "Hiérarchie H2/H3 sans saut de niveau", HARD, violations, fixable=False)


def check_isolated_h3(units: list[Unit]) -> dict:
    violations = []
    for unit in units[1:]:
        n = len(re.findall(r"<h3\b", unit.html, re.IGNORECASE))
        if n == 1:
            violations.append(_loc(unit, "Un seul H3 dans la section (0 ou au moins 2)"))
    return _rule("isolated_h3", "Pas de H3 isolé", WARNING, violations)


def check_verbal_tics(units: list[Unit]) -> dict:
    """Chaque tic de langage (« concrètement », « en réalité »…) au plus
    MAX_TIC_OCCURRENCES fois dans tout l'article, titres compris : au-delà,
    le lecteur « sent » le texte généré."""
    from app.services.seo.content_structure_guard import MAX_TIC_OCCURRENCES, VERBAL_TICS

    seen: dict[str, int] = {}
    violations = []
    for unit in units:
        text = html_to_text(unit.html).lower()
        for tic in VERBAL_TICS:
            for _ in re.finditer(r"(?<![\w'])" + re.escape(tic) + r"(?![\w'])", text):
                seen[tic] = seen.get(tic, 0) + 1
                if seen[tic] > MAX_TIC_OCCURRENCES:
                    violations.append(_loc(
                        unit, f"Tic de langage répété « {tic} » : le remplacer par une vraie liaison logique "
                              "(cause, conséquence, exemple) ou le supprimer", tic,
                    ))
    return _rule("verbal_tics", "Tics de langage une fois au plus", HARD, violations)


def check_h2_lead_paragraph(units: list[Unit]) -> dict:
    """Un H2 n'est jamais suivi directement d'un H3 : au moins un paragraphe
    annonce d'abord la réponse de la section (aussi contrôlé par la
    checklist SEO finale, structure_valid)."""
    violations = []
    for unit in units[1:]:
        after_h2 = re.sub(r"^\s*<h2\b[^>]*>.*?</h2>", "", unit.html, count=1, flags=re.IGNORECASE | re.DOTALL)
        if re.match(r"\s*<h3\b", after_h2, re.IGNORECASE):
            violations.append(_loc(
                unit, "H2 suivi directement d'un H3 : ajouter sous le H2 un court paragraphe qui répond "
                "à la question de la section avec les informations déjà présentes",
            ))
    return _rule("h2_lead_paragraph", "Un paragraphe entre chaque H2 et son premier H3", HARD, violations)


def _paragraphs(unit: Unit) -> list[str]:
    return [t for t in (html_to_text(m.group(1)) for m in _P_RE.finditer(unit.html)) if t]


def check_paragraph_length(units: list[Unit]) -> dict:
    violations = []
    for unit in units:
        for para in _paragraphs(unit):
            n_sent, n_words = len(split_sentences(para)), _words(para)
            if n_sent > MAX_SENTENCES_PER_PARAGRAPH or n_words > MAX_WORDS_PER_PARAGRAPH:
                violations.append(_loc(unit, f"{n_sent} phrases, {n_words} mots "
                                             f"(max {MAX_SENTENCES_PER_PARAGRAPH} phrases / {MAX_WORDS_PER_PARAGRAPH} mots)", para))
    return _rule("paragraph_length", "Paragraphes courts", HARD, violations)


def check_sentence_length(units: list[Unit]) -> tuple[dict, dict]:
    hard, soft = [], []
    total = long_count = 0
    for unit in units:
        unit_long = 0
        unit_total = 0
        for para in _paragraphs(unit):
            for sentence in split_sentences(para):
                n = _words(sentence)
                unit_total += 1
                if n > MAX_WORDS_PER_SENTENCE:
                    hard.append(_loc(unit, f"Phrase de {n} mots (max {MAX_WORDS_PER_SENTENCE})", sentence))
                if n > LONG_SENTENCE_WORDS:
                    unit_long += 1
        total += unit_total
        long_count += unit_long
        if unit_total >= 4 and unit_long / unit_total > LONG_SENTENCE_SHARE:
            soft.append(_loc(unit, f"{unit_long}/{unit_total} phrases de plus de {LONG_SENTENCE_WORDS} mots"))
    return (
        _rule("sentence_length", f"Aucune phrase de plus de {MAX_WORDS_PER_SENTENCE} mots", HARD, hard),
        _rule("long_sentence_share", "Peu de phrases longues", WARNING, soft),
    )


def check_paragraph_variation(units: list[Unit]) -> dict:
    """Guide §1.5 : jamais 4 paragraphes consécutifs de longueur identique."""
    violations = []
    for unit in units:
        lengths = [_words(p) for p in _paragraphs(unit)]
        for i in range(len(lengths) - UNIFORM_RUN + 1):
            run = lengths[i:i + UNIFORM_RUN]
            mean = sum(run) / UNIFORM_RUN
            if mean >= 15 and all(abs(x - mean) <= UNIFORM_TOLERANCE * mean for x in run):
                violations.append(_loc(unit, f"{UNIFORM_RUN} paragraphes consécutifs de longueur proche ({run} mots)"))
                break
    return _rule("paragraph_variation", "Longueur des paragraphes variée", HARD, violations)


def check_intro(units: list[Unit], total_words: int) -> tuple[dict, dict]:
    intro = units[0]
    text = html_to_text(intro.html)
    words = _words(text)
    length_violations = []
    if not text:
        length_violations.append(_loc(intro, "Introduction absente"))
    elif total_words >= INTRO_MIN_ARTICLE_WORDS and words > INTRO_MAX_SHARE * total_words:
        length_violations.append(_loc(intro, f"{words} mots, soit plus de 10 % de l'article ({total_words} mots)"))
    elif total_words < INTRO_MIN_ARTICLE_WORDS and words > INTRO_MAX_WORDS_SHORT:
        length_violations.append(_loc(intro, f"{words} mots (max {INTRO_MAX_WORDS_SHORT} pour un article court)"))
    lower = text.lower()
    generic = [_loc(intro, f"Ouverture générique : « {o} »", text) for o in GENERIC_INTRO_OPENERS if o in lower]
    return (
        _rule("intro_length", "Introduction de 10 % du texte au plus", HARD, length_violations),
        _rule("intro_generic_opening", "Introduction sans ouverture générique", HARD, generic),
    )


def check_em_dash(units: list[Unit]) -> dict:
    violations = []
    for unit in units:
        text = html_to_text(unit.html)
        if "—" in text:
            idx = text.index("—")
            violations.append(_loc(unit, f"{text.count('—')} tiret(s) cadratin(s)", text[max(0, idx - 40): idx + 40]))
    return _rule("no_em_dash", "Aucun tiret cadratin", HARD, violations)


def check_banned_vocabulary(units: list[Unit], title: str | None = None) -> dict:
    violations = []
    pattern = re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in BANNED_WORDS) + r")(?![\w-])", re.IGNORECASE)
    for unit in units:
        text = html_to_text(unit.html)
        found = sorted({m.group(1).lower() for m in pattern.finditer(text)})
        found += [e for e in BANNED_EXPRESSIONS if e in text.lower()]
        if found:
            violations.append(_loc(unit, "Vocabulaire banni : " + ", ".join(found)))
    if title:
        found = sorted({m.group(1).lower() for m in pattern.finditer(title)})
        if found:
            violations.append({"unit": "title", "section": "Titre", "detail": "Vocabulaire banni : " + ", ".join(found),
                               "excerpt": _excerpt(title)})
    return _rule("banned_vocabulary", "Ni superlatif vide ni expression usée", HARD, violations)


def check_vous_saturation(units: list[Unit]) -> dict:
    """Guide §1.7 : jamais 3 « vous » consécutifs (3 phrases de suite qui
    commencent par « vous ») dans le même paragraphe."""
    violations = []
    for unit in units:
        for para in _paragraphs(unit):
            run = 0
            for sentence in split_sentences(para):
                run = run + 1 if re.match(r"^\W*vous\b", sentence, re.IGNORECASE) else 0
                if run >= 3:
                    violations.append(_loc(unit, "3 phrases consécutives commencent par « vous »", para))
                    break
    return _rule("vous_saturation", "Pas trois « vous » d'affilée", HARD, violations)


def check_conclusion_opening(units: list[Unit]) -> dict:
    violations = []
    if len(units) > 1:
        last = units[-1]
        paras = _paragraphs(last)
        first = paras[0].lower() if paras else ""
        for opener in CONCLUSION_OPENERS:
            if first.startswith(opener):
                violations.append(_loc(last, f"La fin commence par « {opener} »", paras[0]))
    return _rule("conclusion_opening", "Fin sans « En conclusion » ni résumé", HARD, violations)


def check_lists(units: list[Unit]) -> dict:
    violations = []
    for unit in units:
        for m in _LIST_RE.finditer(unit.html):
            items = [html_to_text(i) for i in _LI_RE.findall(m.group(2))]
            if len(items) < 2:
                violations.append(_loc(unit, "Liste d'un seul élément", " ".join(items)))
            if len(items) > MAX_LIST_ITEMS:
                violations.append(_loc(unit, f"Liste de {len(items)} éléments (max {MAX_LIST_ITEMS})", items[0]))
            for item in items:
                if _words(item) > MAX_LIST_ITEM_WORDS:
                    violations.append(_loc(unit, f"Élément de liste de {_words(item)} mots (max {MAX_LIST_ITEM_WORDS})", item))
    return _rule("list_format", "Listes de 2 à 10 éléments courts", WARNING, violations)


def check_tables(units: list[Unit]) -> dict:
    violations = []
    for unit in units:
        for m in _TABLE_RE.finditer(unit.html):
            rows = _TR_RE.findall(m.group(1))
            if len(rows) < 2:
                violations.append(_loc(unit, "Tableau de moins de 2 lignes"))
                continue
            if "<th" not in m.group(1).lower():
                violations.append(_loc(unit, "Tableau sans ligne d'en-tête (<th>)"))
            widths = set()
            for row in rows:
                width = 0
                for cell in _CELL_RE.finditer(row):
                    span = re.search(r"colspan\s*=\s*[\"']?(\d+)", cell.group(2) or "", re.IGNORECASE)
                    width += int(span.group(1)) if span else 1
                widths.add(width)
            if len(widths) > 1:
                violations.append(_loc(unit, f"Nombre de colonnes irrégulier ({sorted(widths)})"))
    return _rule("table_format", "Tableaux avec en-tête et colonnes régulières", WARNING, violations)


def check_section_balance(units: list[Unit]) -> dict:
    violations = []
    sections = units[1:]
    counts = [_words(html_to_text(u.html)) - _words(u.heading) for u in sections]
    if sections:
        median = sorted(counts)[len(counts) // 2]
        for unit, count in zip(sections, counts):
            if count < SECTION_MIN_WORDS:
                violations.append(_loc(unit, f"Section de {count} mots (min {SECTION_MIN_WORDS})"))
            elif median and count > SECTION_BALANCE_RATIO * median:
                violations.append(_loc(unit, f"Section de {count} mots, plus de {SECTION_BALANCE_RATIO:g} fois la médiane ({median})"))
    return _rule("section_balance", "Sections équilibrées", WARNING, violations, fixable=False)


# Composants attendus par format recommandé (audit §4.2, version minimale).
_FORMAT_COMPONENTS = {
    "comparison": ("table", "Un tableau comparatif <table>"),
    "how_to": ("steps", "Des étapes en liste numérotée <ol> (ou des H3 numérotés)"),
    "price_guide": ("table", "Un tableau des fourchettes de prix <table>"),
    "list": ("items", "Au moins 3 éléments présentés en H3 ou en liste"),
}


def _component_section(units: list[Unit], hints: tuple[str, ...]) -> Unit | None:
    sections = units[1:]
    for unit in sections:
        if any(h in unit.heading.lower() for h in hints):
            return unit
    return max(sections, key=lambda u: _words(html_to_text(u.html)), default=None)


def check_required_elements(units: list[Unit], content: str, recommended_format: str | None) -> dict:
    violations = []
    fmt = (recommended_format or "").strip()
    lower = (content or "").lower()
    if fmt in ("comparison", "price_guide") and "<table" not in lower:
        target = _component_section(units, ("compar", "tableau", "récap", "critère", "verdict", "versus", " vs",
                                            "prix", "coût", "tarif", "budget"))
        what = "comparatif" if fmt == "comparison" else "des fourchettes de prix par scénario"
        violations.append(_loc(target, f"Tableau {what} absent : ajouter un tableau <table> {what}")
                          if target else {"unit": "body", "section": "", "detail": f"Tableau {what} absent", "excerpt": ""})
    elif fmt == "how_to":
        numbered_h3 = len(re.findall(r"<h3\b[^>]*>\s*(?:[ée]tape\s*)?\d", content or "", re.IGNORECASE))
        if "<ol" not in lower and numbered_h3 < 2:
            target = _component_section(units, ("étape", "etape", "comment", "méthode", "procédure"))
            violations.append(_loc(target, "Guide pratique sans étapes numérotées : présenter les étapes en <ol>")
                              if target else {"unit": "body", "section": "", "detail": "Étapes numérotées absentes", "excerpt": ""})
    elif fmt == "list":
        h3 = len(re.findall(r"<h3\b", content or "", re.IGNORECASE))
        items = len(_LI_RE.findall(content or ""))
        if h3 < 3 and items < 3:
            violations.append({"unit": "body", "section": "", "detail": "Format liste avec moins de 3 éléments", "excerpt": ""})
    label = _FORMAT_COMPONENTS.get(fmt, ("", "Composants du format"))[1]
    return _rule("required_elements", f"Composant attendu du format : {label}", HARD, violations,
                 fixable=fmt in ("comparison", "price_guide", "how_to"))


# ── Point d'entrée ───────────────────────────────────────────────────────────

def validate_structure(content: str, title: str | None = None, recommended_format: str | None = None) -> dict:
    """Artefact `structure_report` : une entrée par règle (pass/fail,
    sévérité, emplacements) et un résumé."""
    units = article_units(content)
    total_words = _words(html_to_text(_FIGURE_RE.sub("", content or "")))
    sentence_hard, sentence_soft = check_sentence_length(units)
    intro_length, intro_generic = check_intro(units, total_words)
    rules = [
        check_h1(content, title),
        check_heading_hierarchy(content),
        check_isolated_h3(units),
        check_h2_lead_paragraph(units),
        check_verbal_tics(units),
        check_paragraph_length(units),
        sentence_hard,
        sentence_soft,
        check_paragraph_variation(units),
        intro_length,
        intro_generic,
        check_em_dash(units),
        check_banned_vocabulary(units, title),
        check_vous_saturation(units),
        check_conclusion_opening(units),
        check_lists(units),
        check_tables(units),
        check_section_balance(units),
        check_required_elements(units, content, recommended_format),
    ]
    hard_failed = [r["rule"] for r in rules if not r["passed"] and r["severity"] == HARD]
    warnings = [r["rule"] for r in rules if not r["passed"] and r["severity"] == WARNING]
    return {
        "status": "fail" if hard_failed else "pass",
        "hard_failures": len(hard_failed),
        "warning_count": len(warnings),
        "failed_hard_rules": hard_failed,
        "failed_warning_rules": warnings,
        "passed_count": sum(1 for r in rules if r["passed"]),
        "rule_count": len(rules),
        "recommended_format": recommended_format or "",
        "stats": {"words": total_words, "sections": len(units) - 1, "intro_words": _words(html_to_text(units[0].html))},
        "rules": rules,
    }


def failing_units(report: dict) -> dict[str, list[str]]:
    """{unit_key: [détails]} des règles dures corrigeables par section."""
    out: dict[str, list[str]] = {}
    for rule in report.get("rules") or []:
        if rule.get("passed") or rule.get("severity") != HARD or not rule.get("section_fixable"):
            continue
        for v in rule.get("violations") or []:
            unit = v.get("unit") or ""
            if unit == "intro" or unit.startswith("section:"):
                detail = f"{rule['label']} : {v.get('detail', '')}"
                if v.get("excerpt"):
                    detail += f" (« {v['excerpt']} »)"
                out.setdefault(unit, []).append(detail)
    return out
