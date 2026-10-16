"""Duel contre le n°1 de Google (voir app/services/seo/champion_duel.py).

Pour chaque article donné : cherche le champion de son mot-clé (Serper),
télécharge sa page, le dissèque, puis fait juger les deux textes à l'aveugle
par deux juges d'autres familles que le rédacteur.

Usage :
  DATABASE_URL=… OPENROUTER_API_KEY=… SERPER_API_KEY=… \
  python scripts/champion_duel.py <article_id> [<article_id> …] [--out report.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.seo.champion_duel import dissect_champion, pick_champion, run_duel, to_markdown  # noqa: E402

JUDGES = [("gemini", "google/gemini-3.8-flash"), ("mistral", "mistralai/mistral-large-4-0")]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


def openrouter_call(model: str):
    def call(prompt: str, step: str, temperature: float) -> str:
        payload = {"model": model, "temperature": temperature, "max_tokens": 12000,
                   "messages": [{"role": "user", "content": prompt}]}
        resp = httpx.post("https://openrouter.ai/api/v1/chat/completions", json=payload, timeout=240,
                          headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"] or ""
    return call


def our_article(article_id: str) -> dict:
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("select r.title, r.body, (select k.term from content.article_keywords ak "
                "join content.keywords k on k.id = ak.keyword_id where ak.article_id = r.article_id "
                "order by (ak.role::text = 'primary') desc limit 1) "
                "from content.article_revisions r where r.article_id=%s "
                "order by r.revision_no desc limit 1", (article_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise SystemExit(f"article introuvable : {article_id}")
    title, body, keyword = row
    return {"title": title, "html": f"<h1>{title}</h1>{body}", "keyword": keyword}


def serp(keyword: str) -> list[dict]:
    resp = httpx.post("https://google.serper.dev/search", timeout=30,
                      headers={"X-API-KEY": os.environ["SERPER_API_KEY"]},
                      json={"q": keyword, "gl": "fr", "hl": "fr", "num": 10})
    resp.raise_for_status()
    return resp.json().get("organic", [])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("article_ids", nargs="+")
    parser.add_argument("--out", default="champion_duel_report.json")
    args = parser.parse_args()

    judges = [(name, openrouter_call(model)) for name, model in JUDGES]
    report = []
    for article_id in args.article_ids:
        ours = our_article(article_id)
        keyword = ours["keyword"] or ours["title"]
        champion = pick_champion(serp(keyword), exclude_hosts=("theslash.fr",))
        if not champion:
            print(f"{keyword} : aucun champion trouvé")
            continue
        page = httpx.get(champion["url"], headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
        champion_md = to_markdown(page.text, champion["url"])
        ours_md = to_markdown(ours["html"])
        if len(champion_md.split()) < 200:
            print(f"{keyword} : page du champion illisible ({champion['url']})")
            continue
        dissection = dissect_champion(champion_md, keyword, judges[0][1])
        duel = run_duel(ours_md, champion_md, keyword, keyword, judges)
        entry = {"keyword": keyword, "article_id": article_id, "champion": champion,
                 "words": {"ours": len(ours_md.split()), "champion": len(champion_md.split())},
                 "dissection": dissection, "duel": duel}
        report.append(entry)
        print(f"\n## {keyword}\nchampion : {champion['url']} (pos. {champion.get('position')})")
        print(f"mots : nous {entry['words']['ours']} / champion {entry['words']['champion']}")
        if duel.get("criteria"):
            print(f"total : nous {duel['ours_total']} / champion {duel['champion_total']} — "
                  f"publié {duel['publish_rate']:.0%}, lecteur {duel['reader_rate']:.0%}, IA {duel['ai_rate']:.0%} — "
                  f"{'VICTOIRE' if duel['won'] else 'DÉFAITE'}")
            for key, c in duel["criteria"].items():
                mark = "<" if c["ours"] < c["champion"] else ("=" if c["ours"] == c["champion"] else ">")
                print(f"  {key:17} nous {c['ours']:5} {mark} champion {c['champion']}")
        else:
            print("  duel invalide :", [r.get("error") for r in duel.get("rounds", [])])
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(f"\nrapport : {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
