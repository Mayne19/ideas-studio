"""Banc d'essai éditorial : génère un jeu fixe d'articles (un par type de
contenu) sur un projet, attend la fin des générations et imprime, pour
chacun, la note du juge éditorial (grille de 100 points), ses critères, ses
blocages et le score heuristique (lint). À relancer après chaque changement
important de la chaîne pour comparer.

Usage :
  IDEAS_API=https://…  IDEAS_TOKEN=…  DATABASE_URL=…  \
  python scripts/editorial_benchmark.py <project_id> [--batch 3] [--delete-previous]

DATABASE_URL sert à lire les artefacts (editorial_judgement) ; IDEAS_TOKEN est
le JWT d'un admin du projet.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

BENCHMARK = [
    ("comparison", "webflow ou wordpress pour un freelance"),
    ("price_guide", "combien coûte un site vitrine"),
    ("how_to", "comment choisir un nom de domaine"),
    ("definition", "qu'est-ce qu'un cms headless"),
    ("list", "meilleurs outils no-code pour créer une application"),
    ("simple_question", "faut-il un site internet pour un auto-entrepreneur"),
]


def _api(method: str, path: str, body: dict | None = None) -> dict | list | None:
    req = urllib.request.Request(
        os.environ["IDEAS_API"].rstrip("/") + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Authorization": f"Bearer {os.environ['IDEAS_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else None


def _wait(project_id: str, job_ids: list[str], timeout: int = 2400) -> dict[str, dict]:
    done: dict[str, dict] = {}
    started = time.time()
    while len(done) < len(job_ids) and time.time() - started < timeout:
        for job_id in job_ids:
            if job_id in done:
                continue
            try:
                job = _api("GET", f"/projects/{project_id}/generation-jobs/{job_id}")
            except Exception:
                continue
            if job and job.get("status") not in ("queued", "pending", "running"):
                done[job_id] = job
                print(f"  {job_id[:8]} {job.get('status')} {job.get('error') or ''}", flush=True)
        time.sleep(30)
    return done


def _report(article_id: str) -> dict:
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("select table_schema||'.'||table_name from information_schema.tables where table_name like '%artifact%'")
    table = cur.fetchone()[0]
    cur.execute(f"select payload from {table} where article_id=%s and agent_key='editorial_judgement' "
                "order by created_at desc limit 1", (article_id,))
    row = cur.fetchone()
    cur.execute("select global_score from content.v_article_latest_score where article_id=%s", (article_id,))
    score = cur.fetchone()
    cur.execute("select title, word_count from content.article_revisions where article_id=%s "
                "order by revision_no desc limit 1", (article_id,))
    title, words = cur.fetchone() or ("", 0)
    conn.close()
    return {"judgement": (row[0] if row else {}) or {}, "global": float(score[0]) if score and score[0] else None,
            "title": title, "words": words}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("--batch", type=int, default=3)
    parser.add_argument("--only", nargs="*", help="types à générer (ex. comparison how_to)")
    args = parser.parse_args()

    items = [b for b in BENCHMARK if not args.only or b[0] in args.only]
    results: list[tuple[str, str, str | None]] = []
    for i in range(0, len(items), args.batch):
        batch = items[i:i + args.batch]
        jobs = {}
        for kind, keyword in batch:
            job = _api("POST", f"/projects/{args.project_id}/articles/generate",
                       {"keyword": keyword, "include_faq": True, "include_callouts": True})
            jobs[job.get("job_id") or job.get("id")] = (kind, keyword)
            print(f"lancé {kind}: {keyword}", flush=True)
        finished = _wait(args.project_id, list(jobs))
        for job_id, (kind, keyword) in jobs.items():
            results.append((kind, keyword, (finished.get(job_id) or {}).get("article_id")))

    print("\n| type | score | juge /95 | blocages | critères | mots | titre |")
    print("|---|---|---|---|---|---|---|")
    for kind, keyword, article_id in results:
        if not article_id:
            print(f"| {kind} | échec | | | | | {keyword} |")
            continue
        r = _report(article_id)
        final = r["judgement"].get("final") or {}
        crit = " ".join(f"{k[:4]}={v['score']:g}/{v['max']}" for k, v in (final.get("criteria") or {}).items())
        blockers = ", ".join(b["type"] for b in final.get("blockers") or []) or "-"
        print(f"| {kind} | {r['global']} | {final.get('content_score')} | {blockers} | {crit} | {r['words']} | "
              f"{r['title']} ({article_id[:8]}) |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
