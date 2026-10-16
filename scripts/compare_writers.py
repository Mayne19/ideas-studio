"""Comparaison à l'aveugle de modèles rédacteurs.

Pour chaque article donné (ou les 5 plus récents d'un projet), relit les
artefacts sauvegardés (production_brief, outline, fact_ledger,
reference_figures, section_fact_assignment), réécrit l'article avec chaque
modèle via le rédacteur section par section (app/services/seo/section_writer.py),
puis note chaque version avec le juge éditorial et le validateur de structure.

Les articles sont enregistrés sous des noms anonymes (A.html, B.html…) ; la
correspondance lettre -> modèle est dans mapping.json, à n'ouvrir qu'après
lecture. Aucun modèle par défaut de l'application n'est modifié.

Usage :
  DATABASE_URL=… OPENROUTER_API_KEY=… [JUDGE_MODEL=google/gemini-3.8-flash] \
  python scripts/compare_writers.py --models deepseek/deepseek-v4-flash mistralai/mistral-small-4 \
      (--articles <id> <id> … | --project <project_id>) --out compare_out [--seed 7]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import string
import sys
from dataclasses import dataclass, field
from pathlib import Path

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_JUDGE_MODEL = "google/gemini-3.8-flash"
ARTIFACT_KEYS = ("production_brief", "outline", "fact_ledger", "reference_figures", "section_fact_assignment")


# ── Anonymisation et agrégation (fonctions pures, testées) ──────────────────

def assign_labels(models: list[str], seed: int | None = None) -> dict[str, str]:
    """Lettre anonyme -> modèle, ordre mélangé (le même pour tous les briefs,
    pour pouvoir agréger par lettre)."""
    unique = list(dict.fromkeys(models))
    if len(unique) > len(string.ascii_uppercase):
        raise ValueError("26 modèles au plus")
    shuffled = unique[:]
    random.Random(seed).shuffle(shuffled)
    return {string.ascii_uppercase[i]: model for i, model in enumerate(shuffled)}


def build_mapping(labels: dict[str, str], article_ids: list[str], judge_model: str) -> dict:
    return {
        "labels": labels,
        "articles": {aid: {label: f"{aid}/{label}.html" for label in labels} for aid in article_ids},
        "judge_model": judge_model,
    }


def aggregate(rows: list[dict]) -> list[dict]:
    """rows : {label, content_score (None si le juge a échoué), hard_failures,
    cost, cost_estimated}. Moyenne par lettre ; une note absente n'entre pas
    dans la moyenne de la note."""
    by_label: dict[str, list[dict]] = {}
    for row in rows:
        by_label.setdefault(row["label"], []).append(row)
    summary = []
    for label in sorted(by_label):
        items = by_label[label]
        scores = [r["content_score"] for r in items if r.get("content_score") is not None]
        costs = [r["cost"] for r in items if r.get("cost") is not None]
        # Une rédaction en échec n'a pas de structure : hors moyenne des règles.
        written = [r for r in items if not r.get("error")]
        summary.append({
            "label": label,
            "articles": len(items),
            "failed": len(items) - len(written),
            "judged": len(scores),
            "mean_content_score": round(sum(scores) / len(scores), 1) if scores else None,
            "mean_hard_failures": (
                round(sum(r.get("hard_failures") or 0 for r in written) / len(written), 2) if written else None
            ),
            "cost_per_article": round(sum(costs) / len(costs), 5) if costs else None,
            "cost_estimated": any(r.get("cost_estimated") for r in items),
        })
    return summary


def markdown_table(summary: list[dict]) -> str:
    lines = [
        "| modèle | articles | note juge /95 (moy.) | règles dures en échec (moy.) | coût / article |",
        "|---|---|---|---|---|",
    ]
    for s in summary:
        score = "-" if s["mean_content_score"] is None else f"{s['mean_content_score']:g} ({s['judged']} jugé(s))"
        if s["cost_per_article"] is None:
            cost = "?"
        else:
            cost = f"{s['cost_per_article']:.4f}" + (" ~" if s["cost_estimated"] else "")
        hard = "-" if s["mean_hard_failures"] is None else f"{s['mean_hard_failures']:g}"
        articles = f"{s['articles']}" + (f" ({s['failed']} en échec)" if s.get("failed") else "")
        lines.append(f"| {s['label']} | {articles} | {score} | {hard} | {cost} |")
    return "\n".join(lines)


def call_cost(usage: dict | None, model: str) -> tuple[float | None, bool]:
    """(coût, estimé ?) : usage.cost d'OpenRouter s'il est renvoyé (USD),
    sinon estimation par cost_estimator (table de prix en EUR, None si le
    modèle n'y figure pas)."""
    usage = usage or {}
    if usage.get("cost") is not None:
        try:
            return float(usage["cost"]), False
        except (TypeError, ValueError):
            pass
    from app.services.cost_estimator import estimate_call_cost

    provider, _, name = model.partition("/")
    estimate = estimate_call_cost(
        provider, name or None,
        input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"),
    )
    return estimate.get("estimated_cost_eur"), True


def parse_word_range(value) -> tuple[int | None, int | None]:
    numbers = [int(n) for n in re.findall(r"\d+", str(value or ""))]
    if len(numbers) >= 2:
        return min(numbers[:2]), max(numbers[:2])
    if len(numbers) == 1:
        return numbers[0], None
    return None, None


# ── Appels OpenRouter ───────────────────────────────────────────────────────

@dataclass
class CostMeter:
    total: float = 0.0
    estimated: bool = False
    unknown: int = 0
    calls: list[dict] = field(default_factory=list)

    def add(self, cost: float | None, estimated: bool, step: str) -> None:
        self.calls.append({"step": step, "cost": cost, "estimated": estimated})
        if cost is None:
            self.unknown += 1
            return
        self.total += cost
        self.estimated = self.estimated or estimated


def openrouter_call(model: str, meter: CostMeter, system: str = "", max_tokens: int = 6000):
    """Fonction d'appel (prompt, step, temperature) -> texte, raisonnement
    désactivé ; relance une fois sans le paramètre si le modèle l'impose
    (puis ne l'envoie plus pour ce modèle)."""
    state = {"disable_reasoning": True}

    def call(prompt: str, step: str, temperature: float) -> str:
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        payload = {"model": model, "temperature": temperature, "max_tokens": max_tokens, "messages": messages,
                   "usage": {"include": True}}
        if state["disable_reasoning"]:
            payload["reasoning"] = {"enabled": False}
        headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
        resp = httpx.post(OPENROUTER_URL, json=payload, headers=headers, timeout=300)
        if resp.status_code == 400 and "reasoning" in payload and "easoning is mandatory" in resp.text:
            state["disable_reasoning"] = False
            payload.pop("reasoning")
            resp = httpx.post(OPENROUTER_URL, json=payload, headers=headers, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        cost, estimated = call_cost(data.get("usage"), model)
        meter.add(cost, estimated, step)
        return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    return call


# ── Base de données ─────────────────────────────────────────────────────────

def _connect():
    import psycopg2

    return psycopg2.connect(os.environ["DATABASE_URL"])


def artifact_table(cur) -> str:
    cur.execute("select table_schema||'.'||table_name from information_schema.tables where table_name like '%artifact%'")
    return cur.fetchone()[0]


def recent_article_ids(cur, table: str, project_id: str, limit: int = 5) -> list[str]:
    cur.execute(
        f"select a.article_id from {table} a join content.articles ar on ar.id = a.article_id "
        "where ar.project_id = %s and a.agent_key = 'production_brief' "
        "group by a.article_id order by max(a.created_at) desc limit %s",
        (project_id, limit),
    )
    return [str(row[0]) for row in cur.fetchall()]


def load_artifacts(cur, table: str, article_id: str) -> dict:
    found = {}
    for key in ARTIFACT_KEYS:
        cur.execute(f"select payload from {table} where article_id=%s and agent_key=%s "
                    "order by created_at desc limit 1", (article_id, key))
        row = cur.fetchone()
        if row and row[0]:
            found[key] = row[0]
    return found


# ── Réécriture ──────────────────────────────────────────────────────────────

def writer_system_prompt() -> str:
    """Prompt système du rédacteur de production (profil éditorial vide)."""
    try:
        from types import SimpleNamespace
        from app.services.seo.seo_generation_orchestrator import SEOGenerationOrchestrator

        return SEOGenerationOrchestrator._build_writer_system_prompt(SimpleNamespace(context={}))
    except Exception as exc:  # pragma: no cover - dépend de l'environnement
        print(f"prompt système indisponible ({exc}) : rédaction sans prompt système", file=sys.stderr)
        return ""


def section_facts_from_assignment(assignment: dict | None, facts: list[dict], sections: list) -> dict | None:
    """Reconstruit l'attribution des faits sauvegardée (ids -> faits) ; None si
    elle ne correspond plus au plan."""
    if not assignment or not isinstance(assignment.get("sections"), list):
        return None
    if len(assignment["sections"]) != len(sections):
        return None
    by_id = {f["fact_id"]: f for f in facts}
    result: dict = {"intro": [by_id[i] for i in assignment.get("intro") or [] if i in by_id],
                    "unassigned": [by_id[i] for i in assignment.get("unassigned") or [] if i in by_id]}
    for index, item in enumerate(assignment["sections"]):
        result[index] = [by_id[i] for i in (item or {}).get("fact_ids") or [] if i in by_id]
    return result


def prepare(artifacts: dict) -> dict:
    from app.services.seo.section_writer import (
        OutlineSection, assign_facts_to_sections, build_section_brief, collect_writer_facts,
        compute_words_per_section, group_outline_sections,
    )

    brief = dict(artifacts["production_brief"])
    ledger = [f for f in (artifacts.get("fact_ledger") or {}).get("facts") or [] if isinstance(f, dict)]
    if ledger and not brief.get("fact_ledger"):
        brief["fact_ledger"] = ledger
    outline = artifacts.get("outline") or {}
    sections = group_outline_sections(outline) or [
        OutlineSection(heading=brief.get("reader_real_question") or brief.get("title") or brief.get("keyword") or "")
    ]
    figures = [f for f in (artifacts.get("reference_figures") or {}).get("figures") or [] if isinstance(f, dict)]
    brief_parts = [build_section_brief(brief), "Pas de FAQ : elle est générée séparément."]
    if figures:
        brief_parts.append(
            "Chiffres de référence (identiques dans tout l'article ; pour ces grandeurs, n'utilise pas "
            "d'autre fourchette, même si un fait de ta section en donne une autre) :\n"
            + "\n".join(f"- {f.get('quantity')} : {f.get('reference')}" for f in figures)
        )
    facts = collect_writer_facts(brief)
    section_facts = section_facts_from_assignment(artifacts.get("section_fact_assignment"), facts, sections) \
        or assign_facts_to_sections(facts, sections, reader_question=brief.get("reader_real_question") or "")
    wc_min, wc_max = parse_word_range(brief.get("word_count_range"))
    return {
        "brief": brief,
        "brief_text": "\n".join(brief_parts),
        "sections": sections,
        "section_facts": section_facts,
        "fmt": brief.get("recommended_format") or "",
        "words_per_section": compute_words_per_section(len(sections), wc_min, wc_max),
        "conclusion_title": outline.get("conclusion_title") or "",
        "ledger": ledger,
        "figures": [f"{f.get('quantity')} : {f.get('reference')}" for f in figures],
    }


def write_with(model: str, prepared: dict, system: str) -> tuple[str, CostMeter]:
    from app.services.seo.section_writer import SectionWriter

    meter = CostMeter()
    writer = SectionWriter(
        openrouter_call(model, meter, system=system),
        prepared["brief_text"],
        prepared["sections"],
        fmt=prepared["fmt"],
        words_per_section=prepared["words_per_section"],
        conclusion_title=prepared["conclusion_title"],
        section_facts=prepared["section_facts"],
    )
    content = writer.write_article()
    content, _, _ = writer.ensure_complete(content)
    return content, meter


def score(content: str, prepared: dict, judge_model: str) -> dict:
    from app.services.seo.editorial_judge import judge_article
    from app.services.seo.section_writer import FORMAT_COMPONENT_INSTRUCTIONS
    from app.services.seo.structure_validator import validate_structure

    brief = prepared["brief"]
    title = brief.get("title") or ""
    report = validate_structure(content, title, prepared["fmt"])
    facts = [
        f"{f.get('fact_id')} [{f.get('source_tier') or 'neutral'}] {str(f.get('claim', ''))[:200]} "
        f"(source : {f.get('url', '')})"
        for f in prepared["ledger"]
    ]
    judge_meter = CostMeter()
    judgement = judge_article(
        content, openrouter_call(judge_model, judge_meter, max_tokens=12000),
        title=title, keyword=brief.get("keyword") or "", brief=brief, facts=facts,
        reference_figures=prepared["figures"], structure_report=report,
        required_component=FORMAT_COMPONENT_INSTRUCTIONS.get(prepared["fmt"], ""),
    )
    return {"structure": report, "judgement": judgement, "judge_cost": judge_meter.total}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", required=True, help="ids de modèles OpenRouter")
    parser.add_argument("--articles", nargs="*", default=[], help="ids d'articles (sinon --project)")
    parser.add_argument("--project", help="projet : ses 5 articles les plus récents avec un brief")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out", default="compare_writers_out")
    parser.add_argument("--seed", type=int, default=None, help="graine du mélange des lettres")
    args = parser.parse_args()

    judge_model = os.environ.get("JUDGE_MODEL") or DEFAULT_JUDGE_MODEL
    conn = _connect()
    cur = conn.cursor()
    table = artifact_table(cur)
    article_ids = list(args.articles)
    if not article_ids:
        if not args.project:
            parser.error("--articles ou --project requis")
        article_ids = recent_article_ids(cur, table, args.project, args.limit)
    if not article_ids:
        print("aucun article avec un production_brief", file=sys.stderr)
        return 1

    labels = assign_labels(args.models, args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "mapping.json").write_text(json.dumps(build_mapping(labels, article_ids, judge_model), indent=2))
    system = writer_system_prompt()

    rows: list[dict] = []
    for article_id in article_ids:
        artifacts = load_artifacts(cur, table, article_id)
        if "production_brief" not in artifacts:
            print(f"{article_id} : pas de production_brief, ignoré", file=sys.stderr)
            continue
        prepared = prepare(artifacts)
        folder = out / article_id
        folder.mkdir(exist_ok=True)
        for label, model in labels.items():
            print(f"{article_id[:8]} {label} : rédaction…", flush=True)
            try:
                content, meter = write_with(model, prepared, system)
            except Exception as exc:
                print(f"  {label} : échec de rédaction ({exc})", file=sys.stderr)
                rows.append({"article_id": article_id, "label": label, "content_score": None,
                             "hard_failures": 0, "cost": None, "error": str(exc)[:300]})
                continue
            (folder / f"{label}.html").write_text(content)
            scored = score(content, prepared, judge_model)
            judgement = scored["judgement"]
            row = {
                "article_id": article_id, "label": label,
                "content_score": None if judgement.get("error") else judgement.get("content_score"),
                "hard_failures": scored["structure"]["hard_failures"],
                "failed_hard_rules": scored["structure"]["failed_hard_rules"],
                "blockers": [b["type"] for b in judgement.get("blockers") or []],
                "cost": None if meter.unknown else meter.total,
                "cost_estimated": meter.estimated,
                "judge_cost": scored["judge_cost"],
                "judge_error": judgement.get("error"),
            }
            (folder / f"{label}.judgement.json").write_text(json.dumps(scored, indent=2, ensure_ascii=False))
            rows.append(row)
            print(f"  {label} : {row['content_score']}/95, {row['hard_failures']} règle(s) dure(s)", flush=True)
    conn.close()

    summary = aggregate(rows)
    (out / "results.json").write_text(json.dumps({"rows": rows, "summary": summary}, indent=2, ensure_ascii=False))
    print()
    print(markdown_table(summary))
    print("\nCoût en USD (usage.cost OpenRouter) ; « ~ » = estimation cost_estimator (EUR). "
          "Correspondance des lettres : mapping.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
