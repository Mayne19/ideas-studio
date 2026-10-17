"""Étalonne judge_v2 sur un manifeste de 9 articles notés par Claude.

Le manifeste contient des entrées {name, reference_score, article_id} (articles DB)
ou {name, reference_score, path} (fichiers locaux). Un call_fn explicite est requis :
ce script ne choisit ni ne déclenche seul de fournisseur de modèle.

Usage:
  DATABASE_URL=… python scripts/judge_calibration.py \
    --manifest tests/data/judge_calibration/manifest.json \
    --judge app.services.seo.editorial_judge:judge_v2 \
    --call-fn mon_module:call_fn
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

EXPECTED_COUNT = 9


def _load_callable(spec: str) -> Callable:
    module_name, sep, attr = spec.partition(":")
    if not sep or not module_name or not attr:
        raise ValueError(f"Callable attendu sous la forme module:fonction, reçu {spec!r}")
    value = getattr(importlib.import_module(module_name), attr)
    if not callable(value):
        raise TypeError(f"{spec} n'est pas appelable")
    return value


def _md_to_html(text: str) -> str:
    """Convertit les éléments Markdown des trois exemples en HTML simple."""
    out: list[str] = []
    paragraph: list[str] = []
    in_list: str | None = None

    def flush_paragraph() -> None:
        if paragraph:
            out.append("<p>" + " ".join(paragraph) + "</p>")
            paragraph.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            if in_list:
                out.append(f"</{in_list}>")
                in_list = None
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            if in_list:
                out.append(f"</{in_list}>")
                in_list = None
            level = min(len(heading.group(1)), 3)
            out.append(f"<h{level}>{heading.group(2)}</h{level}>")
            continue
        item = re.match(r"^([-*]|\d+\.)\s+(.+)$", stripped)
        if item:
            flush_paragraph()
            kind = "ol" if item.group(1)[0].isdigit() else "ul"
            if in_list != kind:
                if in_list:
                    out.append(f"</{in_list}>")
                out.append(f"<{kind}>")
                in_list = kind
            out.append(f"<li>{item.group(2)}</li>")
            continue
        if stripped.startswith("|"):
            flush_paragraph()
            if re.fullmatch(r"[| :\-]+", stripped):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            out.append("<p>" + " | ".join(cells) + "</p>")
            continue
        paragraph.append(stripped)
    flush_paragraph()
    if in_list:
        out.append(f"</{in_list}>")
    return "\n".join(out)


def _fetch_db_article(cur: Any, article_id: str) -> dict:
    cur.execute(
        "select r.title, r.body from content.article_revisions r "
        "where r.article_id=%s order by r.revision_no desc limit 1",
        (article_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Article introuvable en base : {article_id}")
    title, content = row
    cur.execute(
        "select table_schema, table_name from information_schema.tables "
        "where table_name like '%artifact%' order by table_schema, table_name limit 1"
    )
    table = cur.fetchone()
    if not table:
        raise ValueError("Table d'artefacts introuvable")
    from psycopg2 import sql

    table_ref = sql.SQL(".").join(map(sql.Identifier, table))
    cur.execute(
        sql.SQL("select payload from {} where article_id=%s and agent_key=%s "
                "order by created_at desc limit 1").format(table_ref),
        (article_id, "agent_writer_output"),
    )
    result = cur.fetchone()
    output = (result[0] if result else {}) or {}
    facts = [
        f"{f.get('value', '')} — {f.get('quote', '')} — {f.get('source_url', '')}"
        for f in output.get("facts", []) if isinstance(f, dict)
    ]
    competitors = [
        c.get("url", "") if isinstance(c, dict) else str(c)
        for c in output.get("competitors", [])
    ]
    return {"title": title or article_id, "content": content or "", "facts": facts,
            "competitors": competitors, "keyword": ""}


def _load_items(manifest_path: Path) -> tuple[list[dict], Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("articles") if isinstance(manifest, dict) else None
    if not isinstance(items, list) or len(items) != EXPECTED_COUNT:
        raise ValueError(f"Le manifeste doit contenir exactement {EXPECTED_COUNT} articles.")
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict) or not item.get("name") or "reference_score" not in item:
            raise ValueError(f"Entrée {i}: name et reference_score sont requis.")
        if ("article_id" in item) == ("path" in item):
            raise ValueError(f"Entrée {i}: indique exactement un article_id ou un path.")
        item["reference_score"] = float(item["reference_score"])
    return items, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("tests/data/judge_calibration/manifest.json"))
    parser.add_argument("--judge", required=True, help="module:judge_v2")
    parser.add_argument("--call-fn", required=True, help="module:fonction de rappel du juge")
    parser.add_argument("--mean-limit", type=float, default=3)
    parser.add_argument("--max-limit", type=float, default=6)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    items, _ = _load_items(args.manifest)
    judge_v2 = _load_callable(args.judge)
    call_fn = _load_callable(args.call_fn)
    conn = None
    cursor = None
    if any("article_id" in item for item in items):
        try:
            import psycopg2
        except ImportError as exc:
            raise RuntimeError("psycopg2 est requis pour les articles de la base.") from exc
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cursor = conn.cursor()

    rows = []
    try:
        for item in items:
            if "path" in item:
                path = (args.manifest.parent / item["path"]).resolve()
                raw = path.read_text(encoding="utf-8")
                article = {"title": item.get("title", item["name"]),
                           "content": _md_to_html(raw) if path.suffix.lower() == ".md" else raw,
                           "facts": item.get("facts", []), "competitors": item.get("competitors", []),
                           "keyword": item.get("keyword", "")}
            else:
                article = _fetch_db_article(cursor, str(item["article_id"]))
                article.update({k: item[k] for k in ("facts", "competitors", "keyword", "title")
                                if k in item})
            result = judge_v2(
                article["content"], article.get("facts", []), article.get("competitors", []), call_fn
            )
            if not isinstance(result, dict) or "total" not in result:
                raise ValueError(f"{item['name']}: judge_v2 doit rendre un objet avec total.")
            rows.append({
                "name": item["name"],
                "reference": item["reference_score"],
                "total": float(result["total"]),
                "error": abs(float(result["total"]) - float(item["reference_score"])),
                "criteria": result.get("criteria", {}),
                "caps": result.get("caps", []),
            })
    finally:
        if conn:
            conn.close()

    mean_error = sum(r["error"] for r in rows) / len(rows)
    max_error = max(r["error"] for r in rows)
    ref_rank = [r["name"] for r in sorted(rows, key=lambda r: (-r["reference"], r["name"]))]
    judge_rank = [r["name"] for r in sorted(rows, key=lambda r: (-r["total"], r["name"]))]
    rank_positions = {name: i for i, name in enumerate(ref_rank)}
    inversions = sum(
        rank_positions[judge_rank[i]] > rank_positions[judge_rank[j]]
        for i in range(len(judge_rank)) for j in range(i + 1, len(judge_rank))
    )
    pair_count = len(rows) * (len(rows) - 1) // 2
    passed = mean_error <= args.mean_limit and max_error <= args.max_limit
    report = {
        "count": len(rows), "mean_absolute_error": round(mean_error, 3),
        "max_absolute_error": round(max_error, 3), "mean_limit": args.mean_limit,
        "max_limit": args.max_limit, "ranking_reference": ref_rank,
        "ranking_judge": judge_rank, "ranking_inversions": inversions,
        "ranking_pairs": pair_count, "passed": passed, "articles": rows,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
