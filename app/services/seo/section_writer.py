from __future__ import annotations

"""Rédaction section par section.

Demander l'article entier en un seul appel à un modèle bon marché
(deepseek-v4-flash) produisait des articles incomplets : 3 sections sur 5,
pas de fin, sans que rien ne le détecte. Ici l'introduction, chaque H2 du plan
et la fin éventuelle sont rédigés par des appels courts et séquentiels, puis
assemblés de façon déterministe : chaque H2 du plan est posé par le code, pas
par le modèle. Un garde-fou de complétude régénère uniquement une section
absente.

Le module est indépendant de l'orchestrateur : il reçoit une fonction
`write_fn(prompt, step, temperature) -> str` (testable avec un faux provider).
"""

import html as html_lib
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Callable

from app.core.utils import calculate_word_count

logger = logging.getLogger(__name__)

WriteFn = Callable[[str, str, float], str]

MAX_ATTEMPTS_PER_UNIT = 2
MAX_EXTERNAL_LINKS = 3
# Formats qui méritent une fin explicite (verdict, prochaine étape).
CLOSING_FORMATS = ("comparison", "price_guide", "how_to", "list")

# Composant obligatoire du format (vérifié par structure_validator, règle
# required_elements) : demandé dès la rédaction, à une seule section, plutôt
# que laissé à la passe de correction.
FORMAT_COMPONENT_INSTRUCTIONS = {
    "comparison": (
        "Obligatoire dans cette section : un tableau comparatif <table> avec une ligne d'en-tête <th>, "
        "3 à 6 lignes, construit uniquement avec les chiffres et faits fournis (aucun chiffre inventé), "
        "précédé d'une phrase qui dit ce qu'il compare."
    ),
    "price_guide": (
        "Obligatoire dans cette section : un tableau <table> des fourchettes de prix par scénario ou profil "
        "(ligne d'en-tête <th>, 3 à 6 lignes, uniquement les chiffres de référence et les faits fournis), puis "
        "un exemple chiffré complet : un cas concret dont on additionne chaque poste jusqu'au total, calcul juste."
    ),
    "how_to": "Obligatoire dans cette section : les étapes en liste numérotée <ol>, une action concrète par étape.",
    "list": (
        "Obligatoire dans cette section : pour chaque élément présenté, pour qui il convient, sa limite "
        "principale et son prix s'il figure dans les faits."
    ),
    "explainer": (
        "Obligatoire dans cette section : un exemple concret qui montre le concept en situation réelle, "
        "puis la confusion la plus courante à éviter."
    ),
}
_COMPONENT_HINTS = {
    "comparison": ("compar", "tableau", "récap", "critère", "versus", " vs", " ou ", "formule", "quelle"),
    "price_guide": ("prix", "coût", "cout", "tarif", "budget", "combien", "fourchette"),
    "how_to": ("étape", "etape", "comment", "méthode", "procédure"),
    "list": ("liste", "sélection", "outils", "meilleur", "top"),
    "explainer": ("exemple", "concrètement", "fonctionne", "comment ça"),
}


def component_section_index(sections: list, fmt: str) -> int | None:
    """Section qui doit porter le composant du format : la première dont le
    titre l'annonce, sinon la première section."""
    # Liste : la consigne vaut pour chaque élément, donc chaque section.
    if fmt not in FORMAT_COMPONENT_INSTRUCTIONS or fmt == "list" or not sections:
        return None
    hints = _COMPONENT_HINTS[fmt]
    for i, section in enumerate(sections):
        if any(h in f" {section.heading.lower()} " for h in hints):
            return i
    return 0
_CLOSING_HINTS = (
    "conclusion", "verdict", "recommandation", "prochaine étape", "par où commencer",
    "que choisir", "lequel choisir", "en pratique", "notre avis",
)
_BLOCK_END_RE = re.compile(r"</(?:p|ul|ol|table|blockquote|h3)>\s*$", re.IGNORECASE)
_H2_RE = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


@dataclass
class OutlineSection:
    heading: str
    purpose: str = ""
    key_points: list[str] = field(default_factory=list)
    reader_value: str = ""
    subheadings: list[str] = field(default_factory=list)


# ── Utilitaires HTML ─────────────────────────────────────────────────────────

def normalize_heading(text: str) -> str:
    text = html_lib.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"^\s*(?:[ée]tape\s+)?\d{1,2}\s*[.):\-–]\s*", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def headings_match(a: str, b: str) -> bool:
    na, nb = normalize_heading(a), normalize_heading(b)
    if not na or not nb:
        return False
    return na == nb or SequenceMatcher(None, na, nb).ratio() >= 0.85


def extract_h2_texts(content: str) -> list[str]:
    return [re.sub(r"<[^>]+>", " ", m.group(1)).strip() for m in _H2_RE.finditer(content or "")]


def lost_h2s(before: str, after: str) -> list[str]:
    """H2 présents dans `before` et absents de `after` (passe de réécriture)."""
    after_h2 = extract_h2_texts(after)
    return [h for h in extract_h2_texts(before) if not any(headings_match(h, a) for a in after_h2)]


_HTML_BLOCK_RE = re.compile(r"<(?:p|ul|ol|table|blockquote)\b", re.IGNORECASE)


def clean_unit_html(raw: str) -> str:
    """Nettoie une sortie de modèle : backticks, Markdown résiduel, <h1>,
    texte brut sans balise."""
    text = (raw or "").strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text).strip()
    text = re.sub(r"<h1\b[^>]*>.*?</h1>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"^#\s+.+$", "", text, flags=re.MULTILINE)
    if not _HTML_BLOCK_RE.search(text):
        # Sortie en Markdown (ou texte brut), fréquente chez certains modèles
        # (ex. Gemini) : sans conversion complète, les paragraphes restent
        # nus et le contrôle de troncature efface toute la section.
        import markdown

        text = markdown.markdown(text, extensions=["tables", "sane_lists"])
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return text.strip()


def looks_truncated(content: str) -> bool:
    """Sortie coupée : ne se termine pas par la fermeture d'un bloc, ou le
    dernier paragraphe s'arrête sans ponctuation finale."""
    content = (content or "").strip()
    if not content:
        return True
    if not _BLOCK_END_RE.search(content):
        return True
    paragraphs = re.findall(r"<p\b[^>]*>(.*?)</p>\s*$", content, re.IGNORECASE | re.DOTALL)
    if paragraphs:
        last = re.sub(r"<[^>]+>", "", paragraphs[-1]).strip()
        if last and last[-1] not in ".!?:…»)\"":
            return True
    return False


def trim_incomplete_tail(content: str) -> str:
    """Coupe une sortie tronquée après le dernier bloc complet."""
    ends = [m.end() for m in re.finditer(r"</(?:p|ul|ol|table|blockquote)>", content or "", re.IGNORECASE)]
    return content[: ends[-1]].strip() if ends else ""


def last_paragraph_text(content: str, limit: int = 400) -> str:
    paragraphs = re.findall(r"<p\b[^>]*>(.*?)</p>", content or "", re.IGNORECASE | re.DOTALL)
    if not paragraphs:
        return ""
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", paragraphs[-1])).strip()
    return text[-limit:]


def _strip_headings(content: str, levels: str = "2-6") -> str:
    return re.sub(rf"<h[{levels}]\b[^>]*>.*?</h[{levels}]>", "", content, flags=re.IGNORECASE | re.DOTALL).strip()


def _demote_extra_h2(content: str) -> str:
    return re.sub(r"<h2\b([^>]*)>(.*?)</h2>", r"<h3\1>\2</h3>", content, flags=re.IGNORECASE | re.DOTALL)


# ── Plan ─────────────────────────────────────────────────────────────────────

def group_outline_sections(outline: dict | None) -> list[OutlineSection]:
    """Un OutlineSection par H2 ; les entrées H3 du plan deviennent des
    sous-parties de la section H2 qui les précède (et non des H2 séparés)."""
    groups: list[OutlineSection] = []
    for raw in (outline or {}).get("sections") or []:
        if not isinstance(raw, dict) or not str(raw.get("heading") or "").strip():
            continue
        # Sans tic dès le plan : le titre écrit reste identique au plan (sinon
        # le contrôle de complétude croit la section absente et la réécrit).
        from app.services.seo.content_structure_guard import strip_tics
        heading = strip_tics(str(raw["heading"]).strip())
        try:
            level = int(raw.get("level") or 2)
        except (TypeError, ValueError):
            level = 2
        if level >= 3 and groups:
            groups[-1].subheadings.append(heading)
            continue
        groups.append(OutlineSection(
            heading=heading,
            purpose=str(raw.get("purpose") or ""),
            key_points=[str(k) for k in (raw.get("key_points") or []) if str(k).strip()],
            reader_value=str(raw.get("reader_value") or ""),
        ))
    return groups


def compute_words_per_section(n_sections: int, wc_min: int | None, wc_max: int | None) -> int | None:
    if n_sections <= 0:
        return None
    if wc_min and wc_max:
        total = (int(wc_min) + int(wc_max)) // 2
    elif wc_max:
        total = int(int(wc_max) * 0.8)
    elif wc_min:
        total = int(int(wc_min) * 1.15)
    else:
        return None
    body = max(total - 180, total // 2)  # introduction et fin
    return max(120, min(450, body // n_sections))


def build_section_brief(brief: dict) -> str:
    """Brief compact répété dans chaque appel : l'essentiel seulement. Les
    faits n'y sont plus : chaque section reçoit les siens (voir
    assign_facts_to_sections), sinon les mêmes faits se répètent partout."""
    lines = ["=== BRIEF ==="]
    for label, key in (
        ("Titre", "title"), ("Mot-clé principal", "keyword"), ("Audience", "audience"),
        ("Format", "recommended_format"), ("Angle", "main_angle"),
    ):
        if brief.get(key):
            lines.append(f"{label} : {brief[key]}")
    lines.append(f"Question réelle du lecteur : {brief.get('reader_real_question') or brief.get('title', '')}")
    if brief.get("expected_answer"):
        lines.append(f"Réponse attendue : {brief['expected_answer']}")
    differentiation = str(brief.get("differentiation") or "").strip()
    if differentiation:
        lines.append(f"Ce qui distingue cet article : {differentiation}")
    if brief.get("must_include"):
        lines.append("À inclure dans l'article : " + " ; ".join(str(x) for x in brief["must_include"][:6]))
    if brief.get("must_avoid"):
        lines.append("À éviter : " + " ; ".join(str(x) for x in brief["must_avoid"][:6]))
    questions: list[str] = []
    for q in list(brief.get("sub_questions") or []) + list(brief.get("related_questions") or []):
        q = str(q).strip()
        if q and q.lower() not in {x.lower() for x in questions}:
            questions.append(q)
    if questions:
        lines.append("Questions que le lecteur se pose aussi (y répondre là où elles ont leur place) : "
                     + " ; ".join(questions[:6]))
    secondary = [str(k).strip() for k in (brief.get("secondary_keywords") or []) if str(k).strip()]
    if secondary:
        lines.append("Mots-clés secondaires (à placer seulement s'ils sont naturels) : " + ", ".join(secondary[:8]))
    return "\n".join(lines)


# ── Faits par section ────────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_STOPWORDS = {
    "avec", "dans", "pour", "plus", "moins", "sont", "être", "fait", "faire", "cette", "votre", "vous",
    "leur", "leurs", "comme", "mais", "tout", "tous", "quel", "quelle", "quels", "quelles", "comment",
    "pourquoi", "entre", "selon", "sans", "sous", "chez", "the", "and", "for", "with", "from",
}


def _tokens(text: str) -> set[str]:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return {t for t in _TOKEN_RE.findall(text) if len(t) >= 4 and t not in _STOPWORDS}


def collect_writer_facts(brief: dict, limit: int = 30) -> list[dict]:
    """Faits disponibles pour le rédacteur, au format commun
    {fact_id, claim, figure, url, quote, usage_hint, date_or_as_of}. Le
    registre fact_ledger est prioritaire ; à défaut, les evidence_items."""
    facts: list[dict] = []
    ledger = brief.get("fact_ledger") or []
    if ledger:
        for item in ledger:
            if isinstance(item, dict) and item.get("claim"):
                facts.append({
                    "fact_id": str(item.get("fact_id") or f"F{len(facts) + 1}"),
                    "claim": str(item["claim"]).strip(),
                    "figure": str(item.get("figure") or "").strip(),
                    "url": str(item.get("url") or "").strip(),
                    "quote": str(item.get("quote_verbatim") or "").strip(),
                    "usage_hint": str(item.get("usage_hint") or "").strip(),
                    "date_or_as_of": str(item.get("date_or_as_of") or "").strip(),
                })
    else:
        for item in brief.get("evidence_items") or []:
            if isinstance(item, dict) and item.get("fact"):
                facts.append({
                    "fact_id": f"F{len(facts) + 1}",
                    "claim": str(item["fact"]).strip(),
                    "figure": str(item.get("figure") or "").strip(),
                    "url": str(item.get("source_url") or "").strip(),
                    "quote": "",
                    "usage_hint": str(item.get("usage_hint") or "").strip(),
                    "date_or_as_of": "",
                })
    return facts[:limit]


def _section_text(section: "OutlineSection") -> str:
    return " ".join([section.heading, section.purpose, section.reader_value,
                     *section.key_points, *section.subheadings])


def assign_facts_to_sections(
    facts: list[dict],
    sections: list["OutlineSection"],
    *,
    reader_question: str = "",
    per_section: int = 4,
    intro_count: int = 2,
) -> dict:
    """Attribue chaque fait à UNE section (celle dont le titre, le rôle et
    les points clés recoupent le mieux le fait et son usage_hint), au plus
    `per_section` faits par section. Un fait sans aucun recoupement n'est
    attribué à aucune section plutôt que d'être plaqué au hasard.
    L'introduction reçoit en plus les faits qui répondent le mieux à la
    question du lecteur.
    Retourne {"intro": [...], 0: [...], 1: [...], ..., "unassigned": [...]}."""
    result: dict = {"intro": [], "unassigned": []}
    for i in range(len(sections)):
        result[i] = []
    if not facts:
        return result
    section_tokens = [_tokens(_section_text(s)) for s in sections]
    heading_tokens = [_tokens(s.heading) for s in sections]
    scored: list[tuple[float, int, int]] = []
    for fi, fact in enumerate(facts):
        fact_tokens = _tokens(f"{fact.get('claim', '')} {fact.get('figure', '')}")
        hint = fact.get("usage_hint") or ""
        hint_tokens = _tokens(hint)
        for si in range(len(sections)):
            score = len(fact_tokens & section_tokens[si])
            score += len(hint_tokens & section_tokens[si]) + 2 * len(hint_tokens & heading_tokens[si])
            if hint and headings_match(hint, sections[si].heading):
                score += 5
            if score > 0:
                scored.append((score, fi, si))
    scored.sort(key=lambda t: (-t[0], t[1], t[2]))
    assigned: set[int] = set()
    for _score, fi, si in scored:
        if fi in assigned or len(result[si]) >= per_section:
            continue
        result[si].append(facts[fi])
        assigned.add(fi)
    result["unassigned"] = [f for i, f in enumerate(facts) if i not in assigned]
    if intro_count and reader_question:
        q_tokens = _tokens(reader_question)
        ranked = sorted(
            (
                (len(_tokens(f"{f.get('claim', '')} {f.get('usage_hint', '')}") & q_tokens), i)
                for i, f in enumerate(facts)
            ),
            key=lambda t: (-t[0], t[1]),
        )
        result["intro"] = [facts[i] for score, i in ranked[:intro_count] if score > 0]
    return result


def format_facts_block(facts: list[dict]) -> str:
    if not facts:
        return ""
    lines = ["Faits vérifiés pour cette partie (à utiliser seulement s'ils aident à répondre, sans les déformer) :"]
    for fact in facts:
        line = f"- [{fact.get('fact_id', '')}] {fact.get('claim', '')}"
        if fact.get("figure") and fact["figure"] not in line:
            line += f" (chiffre : {fact['figure']})"
        if fact.get("date_or_as_of"):
            line += f" (date : {fact['date_or_as_of']})"
        if fact.get("url"):
            line += f" (source : {fact['url']})"
        lines.append(line)
    lines.append(
        "Quand une phrase s'appuie sur un de ces faits, termine-la par son identifiant entre crochets, "
        "juste avant le point : « … coûte 14 $ par mois [F3]. ». Jamais d'identifiant inventé."
    )
    return "\n".join(lines)


def already_said(article_so_far: str, limit: int = 1200) -> str:
    """Première phrase de chaque paragraphe déjà écrit : ce que la suite ne
    doit pas répéter (les sections écrites isolément redisaient l'intro)."""
    from app.services.seo.html_text_ops import split_units, text_blocks, unit_heading

    items: list[str] = []
    for index, unit in enumerate(split_units(article_so_far or "")):
        firsts = [re.split(r"(?<=[.!?])\s+", b)[0] for b in text_blocks(unit)[:3]]
        if firsts:
            label = "Introduction" if index == 0 else unit_heading(unit)
            items.append(f"[{label}] " + " ".join(firsts))
    return " ".join(items)[:limit]


# ── Marqueurs de faits ───────────────────────────────────────────────────────

_FACT_MARKER_RE = re.compile(r"\s*\[\s*(F\d{1,3}(?:\s*[,;]\s*F\d{1,3})*)\s*\]")
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?…])\s+")
_EMPTY_INLINE_RE = re.compile(r"\s*<(strong|em|b|i|sup|span)\b[^>]*>\s*</\1>", re.IGNORECASE)


def strip_fact_markers(html: str, known_ids: set[str] | None = None) -> tuple[str, list[dict]]:
    """Retire les marqueurs [F3] posés par le rédacteur et renvoie, pour
    chacun, la phrase qui le porte : trace pour le futur vérificateur de
    faits (A7) et pour le placement des citations. Un identifiant absent du
    registre est signalé (known=False), jamais conservé dans le texte."""
    markers: list[dict] = []
    for match in _FACT_MARKER_RE.finditer(html or ""):
        before = re.sub(r"<[^>]+>", " ", (html or "")[: match.start()])
        before = re.sub(r"\s+", " ", html_lib.unescape(before)).strip()[-500:]
        sentence = _SENTENCE_BOUNDARY_RE.split(before)[-1] if before else ""
        for fact_id in re.findall(r"F\d{1,3}", match.group(1)):
            markers.append({
                "fact_id": fact_id,
                "sentence": sentence,
                "known": known_ids is None or fact_id in known_ids,
            })
    cleaned = _FACT_MARKER_RE.sub("", html or "")
    # Marqueur mis en forme par le modèle (<strong>[F3]</strong>) : la balise
    # vide restante laisserait une espace avant la ponctuation.
    cleaned = _EMPTY_INLINE_RE.sub("", cleaned)
    return cleaned, markers


# ── Rédacteur ────────────────────────────────────────────────────────────────

class SectionWriter:
    def __init__(
        self,
        write_fn: WriteFn,
        brief_text: str,
        sections: list[OutlineSection],
        *,
        fmt: str = "",
        words_per_section: int | None = None,
        external_links: list[dict] | None = None,
        internal_links: list[dict] | None = None,
        conclusion_title: str = "",
        style_example: str = "",
        fatal_exceptions: tuple[type[BaseException], ...] = (),
        max_attempts: int = MAX_ATTEMPTS_PER_UNIT,
        section_facts: dict | None = None,
        gain_elements: dict | None = None,
    ):
        self.write_fn = write_fn
        # Éléments de gain d'information affectés ("intro" et index de section).
        self.gain_elements = gain_elements or {}
        # Faits attribués par section (assign_facts_to_sections) : clés
        # "intro" et index de section.
        self.section_facts = section_facts or {}
        self.known_fact_ids = {
            str(f.get("fact_id")) for facts in self.section_facts.values() if isinstance(facts, list)
            for f in facts if isinstance(f, dict) and f.get("fact_id")
        }
        self.brief_text = brief_text
        self.sections = sections
        self.fmt = fmt or ""
        self.words_per_section = words_per_section
        self.external_links = [
            link for link in (external_links or [])
            if isinstance(link, dict) and link.get("url")
            and (link.get("excerpt") or link.get("domain_tier") == "strong")
        ][:5]
        self.internal_links = [link for link in (internal_links or []) if isinstance(link, dict) and link.get("target_url")][:3]
        self.conclusion_title = (conclusion_title or "").strip()
        self.style_example = style_example
        self.fatal_exceptions = fatal_exceptions
        self.max_attempts = max(1, max_attempts)
        self.closing_html = ""
        self.report: dict = {"units": [], "regenerated": [], "missing": [], "fact_markers": []}
        self._consecutive_failures = 0

    # ── Appels ──────────────────────────────────────────────────────────

    def _call(self, prompt: str, step: str, temperature: float, min_words: int) -> str:
        """Appelle le modèle avec relance si la sortie est vide, trop courte
        ou tronquée. Retourne la meilleure sortie exploitable ou ""."""
        best = ""
        best_markers: list[dict] = []
        attempts = 0
        for attempt in range(1, self.max_attempts + 1):
            attempts = attempt
            try:
                raw = self.write_fn(prompt, f"{step}#{attempt}" if attempt > 1 else step, temperature)
            except self.fatal_exceptions:
                raise
            except Exception as exc:
                logger.warning("section_writer: %s tentative %s échouée : %s", step, attempt, exc)
                continue
            # Marqueurs [F#] retirés avant tout contrôle : un paragraphe qui
            # finit par « [F3] » passerait sinon pour tronqué.
            text, markers = strip_fact_markers(clean_unit_html(raw), self.known_fact_ids)
            truncated = looks_truncated(text)
            if truncated:
                text = trim_incomplete_tail(text)
            words = calculate_word_count(text)
            if words > calculate_word_count(best):
                best = text
                best_markers = markers
            if not truncated and words >= min_words:
                break
        for marker in best_markers:
            self.report["fact_markers"].append({**marker, "unit": step})
        ok = bool(best)
        self.report["units"].append({
            "step": step, "attempts": attempts, "words": calculate_word_count(best), "ok": ok,
        })
        self._consecutive_failures = 0 if ok else self._consecutive_failures + 1
        return best

    def _used_urls(self, content: str) -> set[str]:
        return {m.group(1).strip() for m in _HREF_RE.finditer(content or "")}

    def _outline_list(self, current: int | None = None) -> str:
        lines = []
        for i, s in enumerate(self.sections):
            marker = "  ← ta section" if i == current else ""
            lines.append(f"- {s.heading}{marker}")
        return "Plan de l'article :\n" + "\n".join(lines)

    def _links_block(self, article_so_far: str) -> str:
        used = self._used_urls(article_so_far)
        parts: list[str] = []
        internal = [link for link in self.internal_links if link["target_url"] not in used]
        if internal:
            parts.append(
                "Liens internes du site (place-en un ici seulement s'il a sa place naturelle dans cette "
                "section, chaque lien une seule fois dans l'article, sans rel='nofollow') :"
            )
            for link in internal:
                anchor = (link.get("anchor_text") or "").strip()
                parts.append(f"- {link['target_url']}" + (f" (sujet : {anchor})" if anchor else ""))
        external_used = sum(1 for link in self.external_links if link["url"] in used)
        external = [link for link in self.external_links if link["url"] not in used]
        if external and external_used < MAX_EXTERNAL_LINKS:
            parts.append(
                "Sources fiables : l'article doit en citer 1 à 3 au total. Dans cette section, cite au plus "
                "une source, seulement si son extrait soutient une de tes phrases. Le lien porte sur un "
                "groupe de mots naturel de la phrase (jamais « cliquez ici », « source » ni l'URL) : "
                "<a href='URL' target='_blank' rel='nofollow'>groupe de mots</a>. N'invente aucune URL."
            )
            for link in external[:4]:
                excerpt = (link.get("excerpt") or "").strip()
                title = (link.get("anchor_text") or "").strip()
                desc = f"« {excerpt} »" if excerpt else title
                parts.append(f"- {link['url']} : {desc}")
        return "\n".join(parts)

    def _common_rules(self) -> list[str]:
        return [
            "- Tout chiffre, prix, date ou nom d'étude repris d'une source doit figurer dans les faits vérifiés "
            "ou les extraits fournis.",
            "- Tu peux calculer un nouveau chiffre à partir de ces faits (pourcentage d'un montant, coût par "
            "unité, total) : montre le calcul en une phrase pour que le lecteur puisse le refaire.",
            "- Tu peux construire un exemple hypothétique avec des montants ronds (« Prenons un loyer de 600 € »), "
            "à condition de l'annoncer clairement comme un exemple.",
            "- N'invente aucun témoignage, cas client, anecdote vécue ni propos attribué à quelqu'un "
            "(« un freelance le confirme », « un client nous a dit ») : présente le raisonnement directement.",
            "- HTML simple uniquement : <h2>, <h3>, <p>, <ul>, <ol>, <li>, <table>, <blockquote>, <strong>, "
            "<em>, <a>. Pas de Markdown, pas de <h1>.",
        ]

    # ── Unités ──────────────────────────────────────────────────────────

    def write_intro(self) -> str:
        prompt_parts = [
            self.brief_text, "", self._outline_list(), "",
            "Rédige uniquement l'introduction de l'article (le texte placé avant le premier <h2>) :",
            "- Trois paragraphes <p> courts, dans cet ordre, environ 90 à 140 mots au total, aucun titre :",
            "  1. La réponse directe, adaptée à ce que le lecteur veut obtenir (son but, sa contrainte), avec la "
            "recommandation concrète qui en découle ; une phrase peut annoncer qu'il existe d'autres cas traités "
            "plus bas, pour donner envie de lire la suite.",
            "  2. Le problème concret : le piège, le risque ou l'enjeu que le lecteur ne voit pas encore, avec un "
            "fait précis tiré des faits vérifiés.",
            "  3. Une seule phrase qui annonce concrètement ce que l'article lui donne (« Ce comparatif vous donne, "
            "pour chacun des 8 outils, … puis un modèle prêt à copier »), sans « vous découvrirez » ni reprise du titre.",
            "- Les phrases s'enchaînent : chacune découle de la précédente.",
            "- Test du débutant : quelqu'un qui ne connaît rien au sujet comprend la première phrase sans "
            "relire ; pas de jargon ni de formule abstraite (« architecture découplée », « arbitrer »).",
            "- Ni question rhétorique ni « Imaginez » pour commencer.",
            *self._common_rules(),
        ]
        facts_block = format_facts_block(self.section_facts.get("intro") or [])
        if facts_block:
            prompt_parts += ["", facts_block]
        from app.services.seo.information_gain_designer import format_gain_block
        gain_block = format_gain_block(self.gain_elements.get("intro") or {})
        if gain_block:
            prompt_parts += ["", gain_block]
        if self.style_example:
            prompt_parts += ["", self.style_example]
        prompt_parts.append("\nRetourne uniquement le HTML de l'introduction.")
        text = self._call("\n".join(prompt_parts), "WritingPass_Intro", 0.7, min_words=25)
        return _strip_headings(text)

    def _section_prompt(self, index: int, previous_html: str, article_so_far: str) -> str:
        section = self.sections[index]
        n = len(self.sections)
        parts = [self.brief_text, "", self._outline_list(index), ""]
        parts.append(f"Rédige uniquement la section {index + 1} sur {n} : « {section.heading} ».")
        if section.purpose:
            parts.append(f"Rôle de la section : {section.purpose}")
        if section.key_points:
            parts.append("Points à couvrir : " + " ; ".join(section.key_points[:6]))
        if section.reader_value:
            parts.append(f"Ce que le lecteur doit en retirer : {section.reader_value}")
        if section.subheadings:
            parts.append(
                "Sous-parties prévues, en <h3> dans cet ordre, chacune précédée d'au moins un paragraphe "
                "sous le <h2> : " + " ; ".join(section.subheadings)
            )
        else:
            parts.append(
                "Ajoute des <h3> seulement si la section regroupe plusieurs sous-points distincts "
                "(jamais un seul <h3>)."
            )
        parts.append(
            "Le titre est une promesse : la première phrase de la section la tient, et la section ne traite que "
            "ce que le titre annonce (rien de plus, rien d'un autre sujet)."
        )
        already = already_said(article_so_far)
        if already:
            parts.append("Déjà dit plus haut dans l'article (ne le répète pas, appuie-toi dessus) : " + already)
        last = last_paragraph_text(previous_html)
        if last:
            parts.append(f"Fin du texte précédent (enchaîne sans le répéter) : « {last} »")
        if self.words_per_section:
            parts.append(f"Longueur visée : environ {self.words_per_section} mots, moins si le point est simple.")
        component_index = component_section_index(self.sections, self.fmt)
        if index == component_index or self.fmt == "list":
            parts.append(FORMAT_COMPONENT_INSTRUCTIONS[self.fmt])
        elif component_index is not None and self.fmt in ("comparison", "price_guide"):
            parts.append(
                f"Pas de tableau dans cette section : le tableau de l'article est dans la section "
                f"« {self.sections[component_index].heading} »."
            )
        parts += [
            "",
            "Consignes :",
            f"- Commence exactement par <h2>{html_lib.escape(section.heading, quote=False)}</h2> puis entre "
            "directement dans le sujet, sans répéter l'introduction ni annoncer ce que la section va dire.",
            "- Aucun autre <h2>. Ne traite pas le contenu des autres sections du plan.",
            "- Pas de phrase de résumé ni de « En conclusion » en fin de section.",
            *self._common_rules(),
        ]
        facts_block = format_facts_block(self.section_facts.get(index) or [])
        if facts_block:
            parts += ["", facts_block]
        from app.services.seo.information_gain_designer import format_gain_block
        gain_block = format_gain_block(self.gain_elements.get(index) or {})
        if gain_block:
            parts += ["", gain_block]
        links = self._links_block(article_so_far)
        if links:
            parts += ["", links]
        if index == 0 and self.style_example:
            parts += ["", self.style_example]
        parts.append("\nRetourne uniquement le HTML de cette section.")
        return "\n".join(parts)

    def write_section(self, index: int, previous_html: str = "", article_so_far: str = "") -> str:
        """Rédige la section `index` ; renvoie "" si aucune sortie exploitable.
        Le <h2> est toujours posé par le code, avec le titre exact du plan."""
        section = self.sections[index]
        prompt = self._section_prompt(index, previous_html, article_so_far)
        min_words = max(40, int((self.words_per_section or 120) * 0.35))
        text = self._call(prompt, f"WritingPass_Section_{index + 1}", 0.7, min_words=min_words)
        if not text:
            return ""
        first_h2 = _H2_RE.search(text)
        if first_h2 and not re.sub(r"<[^>]+>", "", text[: first_h2.start()]).strip():
            text = text[first_h2.end():]
        body = _demote_extra_h2(text).strip()
        if not re.sub(r"<[^>]+>", "", body).strip():
            return ""
        return f"<h2>{html_lib.escape(section.heading, quote=False)}</h2>\n{body}"

    def needs_closing(self) -> bool:
        if self.conclusion_title:
            return True
        if self.fmt not in CLOSING_FORMATS or not self.sections:
            return False
        last = normalize_heading(self.sections[-1].heading)
        return not any(hint in last for hint in _CLOSING_HINTS)

    def write_closing(self, article_so_far: str) -> str:
        goal = {
            "comparison": "le verdict selon le profil du lecteur (quel choix pour quel cas)",
            "how_to": "la prochaine étape concrète une fois la méthode appliquée",
            "price_guide": "comment obtenir un devis juste et quel budget retenir selon le profil du lecteur",
            "list": "par quoi commencer selon la situation du lecteur",
        }.get(self.fmt, "la conséquence pratique ou la prochaine étape pour le lecteur")
        heading_rule = (
            f"- Commence par <h2>{html_lib.escape(self.conclusion_title, quote=False)}</h2>."
            if self.conclusion_title else "- Aucun titre : uniquement des paragraphes <p>."
        )
        prompt = "\n".join([
            self.brief_text, "", self._outline_list(), "",
            f"Fin du texte précédent : « {last_paragraph_text(article_so_far)} »", "",
            f"Rédige la fin de l'article : 1 ou 2 paragraphes courts (40 à 100 mots) sur {goal}.",
            heading_rule,
            "- Pas de « En résumé » ni « En conclusion », ne répète pas les sections précédentes.",
            *self._common_rules(),
            "\nRetourne uniquement le HTML.",
        ])
        text = self._call(prompt, "WritingPass_Closing", 0.6, min_words=20)
        if not text:
            return ""
        if self.conclusion_title:
            text = _strip_headings(text)
            return f"<h2>{html_lib.escape(self.conclusion_title, quote=False)}</h2>\n{text}" if text else ""
        return _strip_headings(text)

    # ── Assemblage ──────────────────────────────────────────────────────

    def _abort_if_failing(self) -> None:
        if self._consecutive_failures >= 2:
            raise SectionWritingError(
                "Le rédacteur n'a rien produit d'exploitable sur deux unités consécutives."
            )

    def write_article(self) -> str:
        if not self.sections:
            raise SectionWritingError("Plan vide : aucune section à rédiger.")
        parts: list[str] = []
        intro = self.write_intro()
        if intro:
            parts.append(intro)
        else:
            self.report["missing"].append("introduction")
        previous = intro
        for index in range(len(self.sections)):
            section_html = self.write_section(index, previous, "\n".join(parts))
            if section_html:
                parts.append(section_html)
                previous = section_html
            self._abort_if_failing()
        if not any(p.startswith("<h2>") for p in parts):
            raise SectionWritingError("Aucune section du plan n'a pu être rédigée.")
        if self.needs_closing():
            self.closing_html = self.write_closing("\n".join(parts))
            if self.closing_html:
                parts.append(self.closing_html)
        return "\n".join(parts)

    def missing_sections(self, content: str) -> list[int]:
        present = extract_h2_texts(content)
        return [
            i for i, s in enumerate(self.sections)
            if not any(headings_match(s.heading, h) for h in present)
        ]

    def _insertion_point(self, content: str, index: int) -> int:
        """Position d'une section manquante : avant le H2 de la première
        section suivante présente, sinon avant la fin rédigée, sinon à la fin."""
        for later in self.sections[index + 1:]:
            for m in _H2_RE.finditer(content):
                if headings_match(later.heading, m.group(1)):
                    return m.start()
        closing = self.closing_html.strip()
        if closing and content.rstrip().endswith(closing):
            return content.rstrip().rfind(closing)
        return len(content.rstrip())

    def ensure_complete(self, content: str) -> tuple[str, list[str], list[str]]:
        """Vérifie que chaque H2 du plan est présent ; régénère uniquement les
        sections absentes. Retourne (contenu, régénérées, toujours absentes)."""
        regenerated: list[str] = []
        still_missing: list[str] = []
        for index in self.missing_sections(content):
            heading = self.sections[index].heading
            pos = self._insertion_point(content, index)
            section_html = self.write_section(index, content[:pos], content)
            if section_html:
                content = content[:pos].rstrip() + "\n" + section_html + "\n" + content[pos:].lstrip()
                regenerated.append(heading)
            else:
                still_missing.append(heading)
        self.report["regenerated"].extend(regenerated)
        self.report["missing"] = [m for m in self.report["missing"] if m == "introduction"] + still_missing
        return content, regenerated, still_missing


class SectionWritingError(RuntimeError):
    pass
