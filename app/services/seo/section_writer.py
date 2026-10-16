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
CLOSING_FORMATS = ("comparison", "how_to", "list")
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
        heading = str(raw["heading"]).strip()
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
    """Brief compact répété dans chaque appel : l'essentiel seulement."""
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
    if brief.get("must_include"):
        lines.append("À inclure dans l'article : " + " ; ".join(str(x) for x in brief["must_include"][:6]))
    if brief.get("must_avoid"):
        lines.append("À éviter : " + " ; ".join(str(x) for x in brief["must_avoid"][:6]))
    facts = [i for i in (brief.get("evidence_items") or []) if isinstance(i, dict) and i.get("fact")]
    if facts:
        lines.append("Faits vérifiés (à utiliser seulement s'ils aident à répondre) :")
        for item in facts[:6]:
            fact = str(item.get("fact"))
            if item.get("figure"):
                fact += f" [{item['figure']}]"
            lines.append(f"- {fact}")
    return "\n".join(lines)


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
    ):
        self.write_fn = write_fn
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
        self.report: dict = {"units": [], "regenerated": [], "missing": []}
        self._consecutive_failures = 0

    # ── Appels ──────────────────────────────────────────────────────────

    def _call(self, prompt: str, step: str, temperature: float, min_words: int) -> str:
        """Appelle le modèle avec relance si la sortie est vide, trop courte
        ou tronquée. Retourne la meilleure sortie exploitable ou ""."""
        best = ""
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
            text = clean_unit_html(raw)
            truncated = looks_truncated(text)
            if truncated:
                text = trim_incomplete_tail(text)
            words = calculate_word_count(text)
            if words > calculate_word_count(best):
                best = text
            if not truncated and words >= min_words:
                break
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
            "- N'écris aucun chiffre, prix, pourcentage, date ou nom d'étude absent des faits vérifiés "
            "ou des extraits de sources fournis.",
            "- HTML simple uniquement : <h2>, <h3>, <p>, <ul>, <ol>, <li>, <table>, <blockquote>, <strong>, "
            "<em>, <a>. Pas de Markdown, pas de <h1>.",
        ]

    # ── Unités ──────────────────────────────────────────────────────────

    def write_intro(self) -> str:
        prompt_parts = [
            self.brief_text, "", self._outline_list(), "",
            "Rédige uniquement l'introduction de l'article (le texte placé avant le premier <h2>) :",
            "- Les 2 à 3 premières phrases donnent la réponse directe à la question réelle du lecteur. "
            "Pas de contexte, de définition ni d'annonce du plan avant cette réponse.",
            "- Ensuite, une ou deux phrases au plus sur la nuance qui compte (sans énumérer les sections).",
            "- 1 ou 2 paragraphes <p>, environ 60 à 120 mots, aucun titre.",
            *self._common_rules(),
        ]
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
        last = last_paragraph_text(previous_html)
        if last:
            parts.append(f"Fin du texte précédent (enchaîne sans le répéter) : « {last} »")
        if self.words_per_section:
            parts.append(f"Longueur visée : environ {self.words_per_section} mots, moins si le point est simple.")
        parts += [
            "",
            "Consignes :",
            f"- Commence exactement par <h2>{html_lib.escape(section.heading, quote=False)}</h2> puis entre "
            "directement dans le sujet, sans répéter l'introduction ni annoncer ce que la section va dire.",
            "- Aucun autre <h2>. Ne traite pas le contenu des autres sections du plan.",
            "- Pas de phrase de résumé ni de « En conclusion » en fin de section.",
            *self._common_rules(),
        ]
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
