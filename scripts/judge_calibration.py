"""Calibrate judge_v2 against Claude's nine reference scores.

Usage:
  DATABASE_URL=… python scripts/judge_calibration.py \
    --call-fn your_module:call_fn

The call_fn must have the signature call_fn(prompt, step, temperature). Each
calibration article invokes the supplied judge once. No model provider is
selected implicitly.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

MANIFEST_DEFAULT = Path("tests/data/judge_calibration/manifest.json")
AGENT_ARTICLE_IDS = {
    "6b83f483-b4c0-466e-ac0c-483f2cff654b",
    "4066a97b-c1fe-44b4-81f5-06f2f9e73fc7",
    "8a794c0c-ba49-4938-8cc6-c6e82f7e029f",
    "d34f45fb-ee51-4adc-998a-50cca66d6ce7",
}
EXPECTED_COUNT = 9


def load_callable(spec: str):
    module_name, sep, attr = spec.partition(":")
    if not sep or not module_name or not attr:
        raise ValueError("Utilise le format module:fonction.")
    fn = getattr(importlib.import_module(module_name), attr)
    if not callable(fn):
        raise TypeError(f"{spec} n'est pas appelable.")
    return fn


def _as_json(value, default):
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value


def _faq_from_markdown(content: str) -> tuple[str, list[dict]]:
    lines = content.splitlines()
    start = next((i for i, line in enumerate(lines)
                  if re.match(r"^##\s+.*(?:FAQ|questions fréquentes)", line, re.I)), None)
    if start is None:
        return content, []
    body = "\n".join(lines[:start]).rstrip()
    faq_lines = lines[start + 1:]
    entries: list[dict] = []
    question = None
    answer: list[str] = []
    for line in faq_lines:
        match = re.match(r"^#{3,}\s+(.+)$", line.strip())
        if match:
            if question:
                entries.append({"question": question, "answer": "\n".join(answer).strip()})
            question, answer = match.group(1).strip(), []
        elif question:
            answer.append(line)
    if question:
        entries.append({"question": question, "answer": "\n".join(answer).strip()})
    return body, entries


def _domain(url: str) -> str:
    host = urlparse(url if "://" in url else "https://" + url).hostname or ""
    return host.lower().removeprefix("www.")


def _fetch_db_article(cur, item: dict) -> dict:
    article_id = item["article_id"]
    cur.execute(
        "select r.title, r.body, r.faq from content.articles a "
        "join content.article_revisions r on r.id = a.current_revision_id "
        "where a.id = %s",
        (article_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Article introuvable : {article_id}")
    title, content, faq = row
    faq = _as_json(faq, [])
    if not isinstance(faq, list):
        faq = []
    facts, competitors, keyword = [], [], ""
    if article_id in AGENT_ARTICLE_IDS:
        cur.execute(
            "select payload from ai.artifacts where article_id = %s "
            "and agent_key = 'agent_writer_output' order by created_at desc limit 1",
            (article_id,),
        )
        result = cur.fetchone()
        output = _as_json(result[0] if result else None, {})
        facts = output.get("facts") or []
        competitors = sorted({
            domain for c in output.get("competitors") or []
            if isinstance(c, dict)
            for domain in [_domain(c.get("url", ""))] if domain
        })
    cur.execute(
        "select payload from ai.artifacts where article_id = %s "
        "and agent_key = 'idea_discovery' order by created_at desc limit 1",
        (article_id,),
    )
    result = cur.fetchone()
    idea = _as_json(result[0] if result else None, {})
    keyword = idea.get("main_keyword", "")
    return {"title": title or item["name"], "content": content or "",
            "facts": facts, "competitors": competitors, "faq": faq, "keyword": keyword}


def load_article(item: dict, manifest_dir: Path, cur) -> dict:
    if "article_id" in item:
        article = _fetch_db_article(cur, item)
    else:
        path = (manifest_dir / item["path"]).resolve()
        content = path.read_text(encoding="utf-8")
        content, faq = _faq_from_markdown(content)
        article = {"title": item.get("title", item["name"]), "content": content,
                   "facts": item.get("facts", []), "competitors": item.get("competitors", []),
                   "faq": faq, "keyword": item.get("keyword", "")}
    article["facts"] = _as_json(article.get("facts"), [])
    article["competitors"] = article.get("competitors") or []
    article["faq"] = _as_json(article.get("faq"), [])
    return article


def pairwise_ranking_identical(rows: list[dict]) -> bool:
    """Exact ordering check that preserves reference ties."""
    for i, left in enumerate(rows):
        for right in rows[i + 1:]:
            reference_delta = left["reference_score"] - right["reference_score"]
            judge_delta = left["judge_score"] - right["judge_score"]
            if (reference_delta > 0) != (judge_delta > 0):
                return False
            if (reference_delta < 0) != (judge_delta < 0):
                return False
            if (reference_delta == 0) != (judge_delta == 0):
                return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_DEFAULT)
    parser.add_argument("--judge", default="app.services.seo.editorial_judge:judge_v2")
    parser.add_argument("--call-fn", required=True, help="module:fonction(prompt, step, temperature)")
    parser.add_argument("--mean-limit", type=float, default=3)
    parser.add_argument("--max-limit", type=float, default=6)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    items = manifest.get("articles", [])
    if len(items) != EXPECTED_COUNT:
        raise ValueError(f"Le manifeste doit contenir exactement {EXPECTED_COUNT} articles.")
    judge_v2 = load_callable(args.judge)
    call_fn = load_callable(args.call_fn)

    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    rows = []
    try:
        cur = conn.cursor()
        for item in items:
            article = load_article(item, args.manifest.parent, cur)
            result = judge_v2(
                article["content"], call_fn, title=article["title"],
                keyword=article["keyword"], facts=article["facts"],
                competitors=article["competitors"], faq=article["faq"],
            )
            if not isinstance(result, dict) or result.get("total") is None:
                raise ValueError(f"{item['name']}: judge_v2 n'a pas renvoyé total.")
            reference = float(item["reference_score"])
            score = float(result["total"])
            rows.append({
                "name": item["name"], "reference_score": reference,
                "judge_score": score, "absolute_error": abs(score - reference),
                "criteria": result.get("criteria", {}), "caps": result.get("caps", []),
                "grave_faults": result.get("grave_faults", []),
                "measurements": result.get("measurements", {}),
                "status": result.get("status"),
            })
    finally:
        conn.close()

    mean_error = sum(r["absolute_error"] for r in rows) / len(rows)
    max_error = max(r["absolute_error"] for r in rows)
    ranked = sorted(rows, key=lambda r: (-r["reference_score"], r["name"]))
    ranking_identical = pairwise_ranking_identical(rows)
    calibrated = (mean_error <= args.mean_limit and max_error <= args.max_limit and ranking_identical)
    report = {
        "articles": ranked,
        "overall": {
            "count": len(rows), "mean_absolute_error": round(mean_error, 3),
            "max_absolute_error": round(max_error, 3),
            "mean_limit": args.mean_limit, "max_limit": args.max_limit,
            "ranking_reference": [r["name"] for r in sorted(rows, key=lambda r: (-r["reference_score"], r["name"]))],
            "ranking_judge": [r["name"] for r in sorted(rows, key=lambda r: (-r["judge_score"], r["name"]))],
            "ranking_identical": ranking_identical,
            "verdict": "étalonné" if calibrated else "non étalonné",
        },
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.json_out:
        args.json_out.write_text(output + "\n", encoding="utf-8")
    return 0 if calibrated else 1


if __name__ == "__main__":
    sys.exit(main())
