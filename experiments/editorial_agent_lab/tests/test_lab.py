"""Laboratoire de rédaction : agent Claude Code + skill redaction-article,
séparation article / fiche, trois contrôles bloquants, alerte de plagiat."""

import json
from pathlib import Path

from experiments.editorial_agent_lab.editorial_agent.checks import blocking_checks, fiche_valid
from experiments.editorial_agent_lab.editorial_agent.claude_cli_client import ALLOWED_TOOLS, build_command, parse_result
from experiments.editorial_agent_lab.editorial_agent.runner import generate
from experiments.editorial_agent_lab.editorial_agent.similarity import plagiarism_alert
from experiments.editorial_agent_lab.editorial_agent.writer import article_slug, build_prompt, split_output

REPO = Path(__file__).resolve().parents[3]
FICHE = {"meta_title": "Apprendre une langue gratuitement", "meta_description": "x" * 150,
         "slug": "application-gratuite-langue", "mot_cle_principal": "application gratuite langue",
         "sources": [{"titre": "Duolingo", "url": "https://fr.duolingo.com"}], "images": [],
         "liens_internes_places": [], "liens_internes_suggeres": [], "faq": []}
ARTICLE = ("# Quelle application gratuite choisir\n\nIntroduction.\n\n"
           '<aside class="summary"><p class="summary-title">En résumé</p><p>Réponse.</p></aside>\n\n'
           "## Comment cela fonctionne\n\nUne phrase assez longue pour être comparée aux sources du test ici.\n")


def output(article=ARTICLE, fiche=FICHE):
    return f"{article}\n\n```json\n{json.dumps(fiche, ensure_ascii=False)}\n```"


def test_skill_is_installed_and_is_the_only_editorial_instruction():
    skill = (REPO / ".claude/skills/redaction-article/SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---\nname: redaction-article\n")
    prompt = build_prompt("Quelle application gratuite choisir pour apprendre une langue")
    assert prompt.splitlines()[0] == "/redaction-article"
    assert prompt.count("\n") <= 3  # sujet seulement : aucune consigne éditoriale dans le code


def test_writer_command_allows_only_skill_and_web_tools_with_high_effort():
    command = build_command("claude", "/redaction-article\n\nSujet : x")
    assert command[command.index("--effort") + 1] == "high"
    tools = command[command.index("--allowed-tools") + 1:command.index("--permission-mode")]
    assert tuple(tools) == ALLOWED_TOOLS == ("Skill", "WebSearch", "WebFetch")
    assert "Read" not in command and "Bash" not in command  # aucun accès aux fichiers (étalonnage compris)
    assert command[command.index("--permission-mode") + 1] == "dontAsk"


def test_site_articles_are_passed_but_never_calibration_files():
    prompt = build_prompt("sujet", [{"titre": "Bien choisir", "url": "https://theslash.fr/a", "resume": "r"}])
    assert "https://theslash.fr/a" in prompt and "judge_calibration" not in prompt


def test_parse_result_reads_real_cost_and_tokens():
    stdout = json.dumps({"result": "texte", "total_cost_usd": 1.23, "duration_ms": 61000, "num_turns": 14,
                         "usage": {"input_tokens": 10, "output_tokens": 20, "cache_creation_input_tokens": 30,
                                   "cache_read_input_tokens": 40, "server_tool_use": {"web_search_requests": 5}}})
    parsed = parse_result(stdout)
    assert parsed["cost_usd"] == 1.23 and parsed["tokens"] == {"input": 10, "output": 20, "cache_creation": 30,
                                                              "cache_read": 40}
    assert parsed["web_search_requests"] == 5 and parsed["duration_s"] == 61.0


def test_split_output_separates_article_and_fiche():
    article, fiche, error = split_output(output())
    assert article == ARTICLE.strip() and fiche["slug"] == "application-gratuite-langue" and error == ""
    _, missing, error = split_output(ARTICLE)
    assert missing is None and "aucun bloc" in error
    _, bad, error = split_output(ARTICLE + "\n```json\n{pas du json}\n```")
    assert bad is None and error.startswith("JSON invalide")
    assert article_slug("Quelle application ?", {"slug": "Pas Un Slug"}) == "quelle-application"
    preamble, _, _ = split_output("I have what I need. Here is the article:\n\n" + output())
    assert preamble.startswith("# Quelle application") and "Here is the article" not in preamble


def test_three_blocking_checks():
    names = [c["name"] for c in blocking_checks(ARTICLE, FICHE, "")]
    assert names == ["encadré « En résumé »", "aucun tiret cadratin", "fiche json valide"]
    assert all(c["passed"] for c in blocking_checks(ARTICLE, FICHE, ""))
    failing = blocking_checks("# T\n\nSans encadré — avec tiret.", None, "aucun bloc")
    assert [c["passed"] for c in failing] == [False, False, False]
    assert "faq manquant" in fiche_valid({k: v for k, v in FICHE.items() if k != "faq"}, "")["detail"]
    assert "sources doit être list" in fiche_valid(FICHE | {"sources": "x"}, "")["detail"]


def test_plagiarism_is_only_an_alert():
    source = "<p>Une phrase assez longue pour être comparée aux sources du test ici.</p>"
    alert = plagiarism_alert(ARTICLE, ["https://a.fr", "https://b.fr"], fetch=lambda url: source if "a.fr" in url else "")
    assert alert["blocking"] is False and alert["findings"][0]["source_url"] == "https://a.fr"
    assert alert["unreadable_sources"] == ["https://b.fr"]


def test_generate_writes_article_fiche_and_report(tmp_path):
    seen = []

    def fake_writer(prompt):
        seen.append(prompt)
        return {"text": output(), "cost_usd": 0.0, "tokens": {"input": 1, "output": 2}, "duration_s": 1.0}

    report = generate("Quelle application gratuite choisir pour apprendre une langue", output_root=tmp_path,
                      writer=fake_writer, fetch=lambda url: "")
    out = tmp_path / "application-gratuite-langue"
    assert (out / "article.md").read_text(encoding="utf-8").startswith("# Quelle application")
    assert json.loads((out / "fiche.json").read_text(encoding="utf-8"))["slug"] == "application-gratuite-langue"
    assert json.loads((out / "report.json").read_text(encoding="utf-8"))["passed"] is True
    assert (out / "raw_output.md").read_text(encoding="utf-8").startswith("# Quelle application")
    assert report["writer"]["tokens"] == {"input": 1, "output": 2} and seen[0].startswith("/redaction-article")
