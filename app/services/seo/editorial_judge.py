"""Juge éditorial A8 (chaîne v2) : la grille de 100 points de l'audit.

Remplace le « score global » heuristique comme critère de publication. Un
modèle d'une autre famille que le rédacteur (réglable dans le CMS : agent
« quality_gate ») lit l'article avec le brief, les chiffres de référence et
le registre des faits, puis note chaque critère, liste les blocages et donne
une consigne de correction par section fautive (consommée par A9,
targeted_revision).

Grille (docs/AUDIT-CHAINE-EDITORIALE-2026-10.md §4.3) :
- notés par le juge (90 pts) : intention 15, exactitude 20, sources 15,
  gain d'information 15, profondeur 10, clarté 10, fraîcheur 5 ;
- calculés par le code (10 pts) : structure 5 (structure_validator),
  SEO 5 (seo_final_checklist, ajouté au score final).
Publiable : total ≥ seuil du pipeline (90 par défaut) et aucun blocage.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import Callable

from app.services.seo.html_text_ops import extract_json_object, split_units, text_blocks, unit_heading

logger = logging.getLogger(__name__)

CallFn = Callable[[str, str, float], str]

JUDGE_CRITERIA: dict[str, tuple[int, str]] = {
    "intent": (15, "Adéquation à l'intention : la réponse à la question réelle du lecteur arrive dans les 100 "
                   "premiers mots, l'article entier sert cette question"),
    "accuracy": (20, "Exactitude : aucun chiffre, règle ou affirmation faux, inventé, hors sujet (autre public) "
                     "ou contradictoire ; aucune idée reçue présentée comme un fait"),
    "sources": (15, "Fiabilité et traçabilité : les chiffres viennent des faits vérifiés, les sources citées "
                    "sont fiables (officielles, primaires) et liées au bon endroit"),
    "information_gain": (15, "Gain d'information : ce que l'article apporte de plus qu'un article moyen du top "
                             "Google (exemple chiffré complet, cas par profil, méthode, erreurs à éviter)"),
    "depth": (10, "Profondeur : les sous-questions attendues du lecteur sont couvertes, sans remplissage"),
    "clarity": (10, "Clarté et rétention : accroche dès les premières lignes, chaque section commence par ce "
                    "que le lecteur veut savoir, aucun passage creux qui fait décrocher, phrases nettes, ton "
                    "d'expert, pas de répétition"),
    "freshness": (5, "Fraîcheur : prix et données datés ou actuels, aucune année périmée"),
}
CODE_STRUCTURE_POINTS = 5
CODE_SEO_POINTS = 5
BLOCKER_TYPES = ("invented_fact", "unsourced_figure", "contradiction", "intent_missed", "missing_component",
                 "off_topic_fact", "meta_commentary", "reader_drop", "unexplained_jargon", "commercial_copy",
                 "heading_mismatch", "obvious_filler", "plagiarism")

# Introduction acceptée par le fondateur (lecteur : 90/100) : réponse directe
# adaptée au but du lecteur, problème concret, annonce de ce qu'il obtient.
FOUNDER_ACCEPTED_EXAMPLE = (
    "« Pour créer un questionnaire en ligne sans payer ni limiter le nombre de réponses, deux outils suffisent "
    "dans la plupart des cas : Google Forms si vous voulez aller vite, Tally si vous voulez un rendu plus soigné "
    "et des données stockées en Europe. Les six autres outils de ce comparatif ne deviennent intéressants que "
    "dans des situations précises. Le piège se cache dans les versions gratuites. Celle de Typeform s'arrête "
    "désormais à 10 réponses par mois. Passé ce seuil, le formulaire se ferme tout seul, souvent au milieu d'une "
    "campagne d'envoi. Ce comparatif vous donne, pour chacun des 8 outils, la vraie limite de sa version gratuite "
    "et le premier prix à payer, puis un modèle de questionnaire prêt à copier. »"
)
# Passages refusés (« phrases jetées », évidences, tics) : 0/10 pour le fondateur.
FOUNDER_REJECTED_PASSAGES = (
    "« Trois temps suffisent. Vous écrivez vos questions sur un site, l'outil vous donne un lien et chaque réponse "
    "s'enregistre dans un tableau. Aucune installation, aucune ligne de code. » (phrases empilées sans lien, "
    "évidences sans valeur) ; « Curieusement… », « Franchement… », « Imaginez… » (tics de texte généré)."
)

# Calibration humaine : introduction refusée par le fondateur (2026-10-16),
# « aucun lien entre les phrases, on sent le contenu généré, j'ai fermé ».
FOUNDER_REJECTED_EXAMPLE = (
    "« Un CMS headless sépare la gestion de vos contenus (back-office) de leur affichage (front-end). "
    "Concrètement, vous rédigez vos articles et gérez vos médias dans une interface classique, mais le contenu "
    "est livré via une API à n'importe quel support : site web, application mobile, borne interactive. Avec un "
    "CMS traditionnel comme WordPress, le back-office et le front-end sont liés : changer de thème modifie "
    "l'apparence, mais aussi parfois la structure. Avec un headless, vous gardez le même back-office tout en "
    "changeant complètement le design ou la technologie du site sans toucher aux contenus. »\n"
    "Pourquoi c'est refusé : des définitions empilées sans fil ni enjeu pour le lecteur, chaque phrase pourrait "
    "être déplacée sans perte, tic « Concrètement », ton de fiche encyclopédique ; un vrai lecteur ferme la page."
)


def article_digest(content: str) -> str:
    lines: list[str] = []
    for index, unit in enumerate(split_units(content)):
        blocks = text_blocks(unit)
        if not blocks:
            continue
        lines.append("## INTRODUCTION" if index == 0 else f"## SECTION « {unit_heading(unit)} »")
        lines.extend(f"- {b}" for b in blocks)
        # Tableau rendu ligne par ligne : une simple mention faisait croire au
        # juge que le tableau manquait (faux heading_mismatch, 2026-10-17).
        for table in re.findall(r"<table\b.*?</table>", unit, re.IGNORECASE | re.DOTALL):
            lines.append("- Tableau :")
            for row in re.findall(r"<tr\b.*?</tr>", table, re.IGNORECASE | re.DOTALL):
                cells = [re.sub(r"<[^>]+>", "", c).strip()
                         for c in re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", row, re.IGNORECASE | re.DOTALL)]
                lines.append("  | " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines).strip()


def build_judge_prompt(content: str, *, title: str, keyword: str, brief: dict, facts: list[str],
                       reference_figures: list[str], required_component: str = "",
                       planned_gain: dict | None = None, competitors: list[str] | None = None,
                       strict_facts: bool = False) -> str:
    criteria = "\n".join(f"- {key} ({pts} pts) : {desc}" for key, (pts, desc) in JUDGE_CRITERIA.items())
    parts = [
        "Tu es rédacteur en chef d'un média web exigeant (niveau des meilleurs blogs experts français). "
        "Tu notes un article avant publication. Sois sévère et précis : 90/100 veut dire « je publie tel quel "
        "sous mon nom ». Cite des passages exacts comme preuves.",
        "",
        f"Date du jour : {date.today().isoformat()}",
        f"Titre : {title}",
        f"Mot-clé : {keyword}",
        f"Question réelle du lecteur : {brief.get('reader_real_question') or title}",
    ]
    if brief.get("expected_answer"):
        parts.append(f"Réponse attendue : {brief['expected_answer']}")
    if brief.get("audience"):
        parts.append(f"Lecteur : {brief['audience']}")
    if required_component:
        parts.append(f"Composant obligatoire du format : {required_component}")
    if reference_figures:
        parts += ["", "Chiffres de référence (font foi) :", *[f"- {f}" for f in reference_figures]]
    if planned_gain:
        planned = [k for k in ("decision_tool", "worked_example", "surprising_fact", "common_mistakes") if planned_gain.get(k)]
        if planned:
            parts += ["", "Gain d'information prévu avant rédaction (critère information_gain : vérifie que chaque "
                          "élément est présent et juste) : " + ", ".join(planned)]
    if facts:
        parts += ["", "Faits vérifiés disponibles (avec leur source) :", *[f"- {f}" for f in facts[:40]]]
    if strict_facts:
        parts += ["", "Toute affirmation technique, chimique, de santé, de sécurité ou sur un symbole absente de cette "
                      "liste de faits est non sourcée : pénalise accuracy et sources, et signale-la (unsourced_figure "
                      "si c'est un chiffre)."]
    if competitors:
        parts += ["", "Concurrents (ne doivent jamais être nommés, cités ni liés dans l'article ; une mention est une "
                      "faute grave) : " + ", ".join(competitors)]
    parts += [
        "",
        "Grille (note chaque critère de 0 à son maximum) :",
        criteria,
        "",
        "Lis d'abord comme un lecteur humain exigeant, pas comme une IA : il décroche dès que les phrases sont "
        "empilées sans lien logique, qu'un tic revient (« concrètement », « en réalité »), que l'introduction est "
        "redite, que le texte parle de lui-même ou sonne généré. Exemple d'introduction refusée par notre "
        "rédacteur en chef :",
        FOUNDER_REJECTED_EXAMPLE,
        "Un passage de ce niveau dans l'introduction ou dans une section = clarity ≤ 4 et blocage reader_drop.",
        "Autres passages refusés : " + FOUNDER_REJECTED_PASSAGES,
        "Introduction acceptée, le niveau attendu (réponse directe adaptée au but du lecteur, problème concret, "
        "annonce en une phrase de ce qu'il obtient) :",
        FOUNDER_ACCEPTED_EXAMPLE,
        "Lis aussi comme un débutant qui ne connaît pas le sujet : si la première phrase ne répond pas "
        "simplement à la question ou si un terme technique arrive sans explication, clarity ≤ 4 et blocage "
        "unexplained_jargon (cite le terme). Une offre commerciale d'un prestataire (ses tarifs, son diagnostic "
        "gratuit, son forfait) présentée comme un fait = blocage commercial_copy.",
        "",
        "Blocages (un seul suffit à refuser la publication) : invented_fact (fait ou source inventés), "
        "unsourced_figure (chiffre précis absent des faits vérifiés et invérifiable ; un chiffre calculé à partir "
        "des faits, calcul montré, ou un montant présenté comme exemple n'en est pas un, mais vérifie que le calcul "
        "est juste : un calcul faux est un blocage contradiction), contradiction (deux valeurs "
        "différentes pour la même chose), intent_missed (la question n'a pas de réponse claire), off_topic_fact "
        "(chiffre qui concerne un autre public ou un autre cas), meta_commentary (le texte commente l'article, une "
        "consigne ou « le lecteur »), reader_drop (passage qui fait décrocher : phrases sans fil, tics, "
        "répétition, ton généré), unexplained_jargon, commercial_copy, heading_mismatch (une section traite autre "
        "chose que ce que son titre promet, ou le titre promet plus que la section), obvious_filler (évidence sans "
        "valeur : « sans rien installer », « pas besoin de savoir coder »). Ne signale un blocage que s'il est certain.",
        "",
        "Pour chaque section à améliorer, donne une consigne de correction concrète et applicable par un "
        "rédacteur (« remplacer la fourchette X par la référence Y », « supprimer l'affirmation Z non sourcée », "
        "« ajouter un exemple chiffré complet à partir des faits F… ») ; 4 sections au plus, les plus rentables.",
        "",
        "Réponds UNIQUEMENT en JSON :",
        '{"criteria": {"intent": {"score": 0, "evidence": "..."}, "accuracy": {...}, "sources": {...}, '
        '"information_gain": {...}, "depth": {...}, "clarity": {...}, "freshness": {...}}, '
        '"blockers": [{"type": "contradiction", "section": "titre de section ou INTRODUCTION", '
        '"detail": "passage exact et explication"}], '
        '"section_fixes": [{"section": "titre exact de la section ou INTRODUCTION", "instructions": "..."}], '
        '"summary": "deux phrases"}',
        "",
        "Article :",
        article_digest(content),
    ]
    return "\n".join(parts)


def _clamp(value, maximum: int) -> float:
    try:
        return max(0.0, min(float(value), float(maximum)))
    except (TypeError, ValueError):
        return 0.0


def structure_points(structure_report: dict | None) -> float:
    """5 points moins 2 par règle dure en échec (structure_validator)."""
    if not structure_report:
        return float(CODE_STRUCTURE_POINTS)
    hard = len(structure_report.get("failed_hard_rules") or [])
    return float(max(0, CODE_STRUCTURE_POINTS - 2 * hard))


def parse_judgement(raw: str, *, structure_report: dict | None = None) -> dict | None:
    data = extract_json_object(raw)
    if not isinstance(data, dict) or not isinstance(data.get("criteria"), dict):
        return None
    criteria: dict[str, dict] = {}
    for key, (maximum, _) in JUDGE_CRITERIA.items():
        item = data["criteria"].get(key) or {}
        if not isinstance(item, dict):
            item = {"score": item}
        criteria[key] = {"score": _clamp(item.get("score"), maximum), "max": maximum,
                         "evidence": str(item.get("evidence") or "")[:400]}
    blockers = [
        {"type": str(b.get("type")), "section": str(b.get("section") or "")[:200], "detail": str(b.get("detail") or "")[:400]}
        for b in data.get("blockers") or []
        if isinstance(b, dict) and str(b.get("type")) in BLOCKER_TYPES
    ]
    required = next((r for r in (structure_report or {}).get("rules") or []
                     if r.get("rule") == "required_elements" and not r.get("passed")), None)
    if required:
        blockers.append({"type": "missing_component", "section": "", "detail": required.get("label", "")})
    fixes = [
        {"section": str(f.get("section") or "").strip(), "instructions": str(f.get("instructions") or "").strip()[:600]}
        for f in data.get("section_fixes") or []
        if isinstance(f, dict) and str(f.get("instructions") or "").strip()
    ][:4]
    judged = sum(c["score"] for c in criteria.values())
    structure = structure_points(structure_report)
    return {
        "criteria": criteria,
        "structure_points": structure,
        "content_score": round(judged + structure, 1),  # sur 95 ; le SEO (5) s'ajoute au scoring final
        "blockers": blockers,
        "section_fixes": fixes,
        "summary": str(data.get("summary") or "")[:600],
    }


def judge_article(content: str, call_fn: CallFn, *, title: str, keyword: str, brief: dict,
                  facts: list[str], reference_figures: list[str], structure_report: dict | None = None,
                  required_component: str = "", planned_gain: dict | None = None,
                  competitors: list[str] | None = None, strict_facts: bool = False,
                  fatal_exceptions: tuple[type[BaseException], ...] = ()) -> dict:
    """Jugement complet, ou {"error": ...} si l'appel ou le JSON échoue."""
    prompt = build_judge_prompt(content, title=title, keyword=keyword, brief=brief, facts=facts,
                                reference_figures=reference_figures, required_component=required_component,
                                planned_gain=planned_gain, competitors=competitors, strict_facts=strict_facts)
    try:
        raw = call_fn(prompt, "EditorialJudge", 0.1)
    except fatal_exceptions:
        raise
    except Exception as exc:
        logger.warning("editorial_judge: appel en échec : %s", exc)
        return {"error": str(exc)[:300]}
    judgement = parse_judgement(raw, structure_report=structure_report)
    if judgement is None:
        return {"error": "réponse JSON invalide"}
    return judgement


def final_score(judgement: dict, seo_checklist_score: float | None) -> float:
    """Note sur 100 : contenu (95) + SEO technique (5)."""
    seo = (seo_checklist_score or 0.0) / 100.0 * CODE_SEO_POINTS
    return round(min(100.0, float(judgement.get("content_score") or 0.0) + seo), 1)
