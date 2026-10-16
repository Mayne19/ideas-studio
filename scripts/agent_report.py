"""Rapport d'un article rédigé par l'agent unique, au format demandé pour la
relecture : mot-clé, concurrents et failles, sources, faits cités mot pour
mot, article brut avec la FAQ (tableaux et listes numérotées rendus fidèlement,
HTML du tableau joint), contrôles, tours de correction, coût détaillé.
Aucun appel à un modèle.

Usage : DATABASE_URL=… python scripts/agent_report.py <article_id> [--out rapport.md]
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys


def to_markdown(body: str) -> str:
    out = body or ""

    def table(m: re.Match) -> str:
        rows = re.findall(r"<tr\b.*?</tr>", m.group(0), re.IGNORECASE | re.DOTALL)
        lines = []
        for i, row in enumerate(rows):
            cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                     for c in re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", row, re.IGNORECASE | re.DOTALL)]
            lines.append("| " + " | ".join(cells) + " |")
            if i == 0:
                lines.append("|" + "---|" * len(cells))
        return "\n\n" + "\n".join(lines) + "\n\n"

    def ordered(m: re.Match) -> str:
        items = re.findall(r"<li\b[^>]*>(.*?)</li>", m.group(0), re.IGNORECASE | re.DOTALL)
        return "\n\n" + "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1)) + "\n\n"

    out = re.sub(r"<table\b.*?</table>", table, out, flags=re.IGNORECASE | re.DOTALL)
    out = re.sub(r"<ol\b.*?</ol>", ordered, out, flags=re.IGNORECASE | re.DOTALL)
    out = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n\n## \1\n", out, flags=re.DOTALL)
    out = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n\n### \1\n", out, flags=re.DOTALL)
    out = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", out, flags=re.DOTALL)
    out = re.sub(r"<li[^>]*>", "\n- ", out)
    out = re.sub(r"<p[^>]*>", "\n\n", out)
    out = html.unescape(re.sub(r"<[^>]+>", "", out))
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def build_report(cur, article_id: str) -> str:
    cur.execute("select table_schema||'.'||table_name from information_schema.tables where table_name like '%artifact%'")
    table_name = cur.fetchone()[0]

    def artifact(key: str) -> dict:
        cur.execute(f"select payload from {table_name} where article_id=%s and agent_key=%s "
                    "order by created_at desc limit 1", (article_id, key))
        row = cur.fetchone()
        return (row[0] if row else None) or {}

    cur.execute("select r.title, r.body, r.faq, r.word_count, a.slug from content.article_revisions r "
                "join content.articles a on a.id = r.article_id where r.article_id=%s "
                "order by r.revision_no desc limit 1", (article_id,))
    title, body, faq, words, slug = cur.fetchone()
    cur.execute("select meta_title, meta_description from content.article_seo where article_id=%s", (article_id,))
    meta_title, meta_description = cur.fetchone() or ("", "")
    cur.execute("select global_score from content.v_article_latest_score where article_id=%s", (article_id,))
    score = cur.fetchone()
    output, report = artifact("agent_writer_output"), artifact("agent_writer_report")
    judge = artifact("editorial_judgement").get("final") or {}
    plagiarism = artifact("plagiarism_report")
    keyword = artifact("idea_discovery").get("main_keyword", "")

    lines = ["**Résumé**",
             f"- Mot-clé : {keyword}",
             f"- Route : {report.get('route')}, modèle {report.get('model')}, raisonnement « {report.get('reasoning')} ».",
             f"- Durée : {report.get('duration_s')} s ; appels : {report.get('calls')}.",
             f"- Jetons : {report.get('input_tokens')} en entrée, {report.get('output_tokens')} en sortie ; "
             f"recherches : {report.get('web_searches')} ; pages lues : {report.get('web_fetches')}.",
             f"- Coût : {report.get('real_cost_usd') or report.get('cost_usd')} $ "
             f"({'facturé' if report.get('real_cost_usd') else 'estimé'}).",
             f"- Juge éditorial : contenu {judge.get('content_score')}/95, score global "
             f"{float(score[0]) if score and score[0] is not None else None}, blocages "
             f"{[b.get('type') for b in judge.get('blockers') or []] or 'aucun'}.",
             f"- Plagiat : {plagiarism.get('status')}, {len(plagiarism.get('matches') or [])} correspondance(s).",
             "", "**Contrôles et tours de correction**"]
    for r in report.get("rounds") or []:
        detail = " | ".join(r.get("errors") or []) or "aucune faute dure" if "errors" in r else r.get("error")
        lines.append(f"- Tour {r.get('round')} : {detail}")
    lines.append("- Fautes restantes : " + (" | ".join(report.get("remaining_errors") or []) or "aucune"))
    lines.append("- Cohérence (informatif) : " + (" | ".join(report.get("consistency_info") or []) or "rien"))
    lines += ["", "**Concurrents et failles**"]
    lines += [f"- {c.get('url')} : " + " ; ".join(c.get("weaknesses") or []) for c in output.get("competitors") or []]
    lines += ["", "**Sous-questions listées avant d'écrire (concurrents et « Autres questions posées »)**"]
    lines += [f"- {q}" for q in output.get("sub_questions") or []]
    lines += ["", "**Sources**"]
    lines += [f"- {s.get('url')} — {s.get('title', '')} — {s.get('used_for', '')}" for s in output.get("sources") or []]
    lines += ["", "**Faits (citation exacte)**"]
    lines += [f"- {f.get('value')} — « {f.get('quote', '')} » — {f.get('source_url')}" for f in output.get("facts") or []]
    lines += ["", "**Auto-relecture** : " + json.dumps(output.get("self_review") or {}, ensure_ascii=False),
              "", f"**Article brut ({words} mots)**", "",
              f"Titre : {title}", f"Meta title : {meta_title}", f"Meta description : {meta_description}",
              f"Slug : {slug}", "", to_markdown(body), "", "**FAQ**"]
    lines += [f"- {f.get('question')}\n  {f.get('answer')}" for f in faq or []]
    tables = re.findall(r"<table\b.*?</table>", body or "", re.IGNORECASE | re.DOTALL)
    if tables:
        lines += ["", "**HTML du tableau (rendu réel)**", "```html", tables[0][:3000], "```"]
    return "\n".join(lines)


def main() -> int:
    import psycopg2

    parser = argparse.ArgumentParser()
    parser.add_argument("article_id")
    parser.add_argument("--out")
    args = parser.parse_args()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    text = build_report(conn.cursor(), args.article_id)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
