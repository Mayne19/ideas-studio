import json
from types import SimpleNamespace as NS

import pytest

from app.services.seo.agent_writer import (
    AgentWriter, AgentWriterError, build_user_message, load_system_prompt, locale_names, validate_output,
)

ARTICLE = {
    "title": "Comment enlever une tache de gras", "meta_title": "Tache de gras : la méthode",
    "meta_description": "…", "slug": "enlever-tache-de-gras",
    "content_html": "<p>" + "mot " * 300 + "</p><h2>Conclusion</h2><p>fin</p>",
    "faq": [{"question": "q", "answer": "a"}],
}


def text(t):
    return NS(type="text", text=t)


def response(content, stop="end_turn", searches=0, fetches=0):
    usage = NS(input_tokens=1000, output_tokens=500, cache_read_input_tokens=0,
               server_tool_use=NS(web_search_requests=searches, web_fetch_requests=fetches))
    return NS(content=content, stop_reason=stop, usage=usage)


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.messages = NS(create=self._create)

    def _create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


def test_prompt_variables_are_replaced():
    tpl = "Site {site_name} ({site_domain}) en {langue} pour {pays} le {date}. JSON : {\"title\": \"\"}"
    out = load_system_prompt(site_name="theslash", site_domain="theslash.fr", langue="français", pays="France",
                             template=tpl)
    assert "theslash (theslash.fr) en français pour France" in out and '{"title": ""}' in out and "{date}" not in out
    assert locale_names("fr-FR") == ("français", "France")
    real = load_system_prompt(site_name="theslash", site_domain="theslash.fr", langue="français", pays="France")
    assert "ÉTAPE 8" in real and "{site_name}" not in real


def test_tool_loop_resumes_pause_turn_and_counts_usage():
    client = FakeClient([
        response([NS(type="server_tool_use", name="web_search")], stop="pause_turn", searches=3),
        response([text(json.dumps(ARTICLE))], fetches=4),
    ])
    writer = AgentWriter(client, system="s")
    data = writer.write(build_user_message(keyword="tache de gras"))
    assert data["slug"] == "enlever-tache-de-gras" and len(client.calls) == 2
    report = writer.report()
    assert report["web_searches"] == 3 and report["web_fetches"] == 4 and report["input_tokens"] == 2000
    assert report["cost_usd"] > 0


def test_invalid_json_then_valid():
    client = FakeClient([response([text("Voici l'article !")]), response([text(json.dumps(ARTICLE))])])
    data = AgentWriter(client, system="s").write("kw")
    assert data["title"] and "pas un JSON valide" in client.calls[1]["messages"][-1]["content"]


def test_invalid_json_twice_raises():
    client = FakeClient([response([text("non")]), response([text("toujours pas")])])
    with pytest.raises(AgentWriterError):
        AgentWriter(client, system="s").write("kw")


def test_correction_stays_in_same_conversation():
    fixed = {**ARTICLE, "title": "Titre corrigé"}
    client = FakeClient([response([text(json.dumps(ARTICLE))]), response([text(json.dumps(fixed))])])
    writer = AgentWriter(client, system="s")
    writer.write("kw")
    out = writer.correct(["H2 suivi directement d'un H3"])
    assert out["title"] == "Titre corrigé"
    last_user = client.calls[1]["messages"][-1]["content"]
    assert last_user.startswith("Corrige uniquement ces points") and len(client.calls[1]["messages"]) == 3


def test_validate_output_and_user_message():
    assert validate_output({"title": "x"})
    assert validate_output(ARTICLE) == []
    msg = build_user_message(keyword="k", published_articles=[{"title": "A", "url": "https://s.fr/blog/a"}])
    assert "https://s.fr/blog/a" in msg
    assert "pas de lien interne" in build_user_message(keyword="k")


def test_openrouter_bridge_runs_tools_and_keeps_transcript():
    from app.services.seo.agent_writer_openrouter import OpenRouterAgentClient

    replies = [
        {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
            {"id": "1", "type": "function", "function": {"name": "web_search", "arguments": '{"query": "tache"}'}},
            {"id": "2", "type": "function", "function": {"name": "web_fetch", "arguments": '{"url": "https://a.fr"}'}},
        ]}, "finish_reason": "tool_calls"}], "usage": {"prompt_tokens": 100, "completion_tokens": 10}},
        {"choices": [{"message": {"role": "assistant", "content": json.dumps(ARTICLE)}, "finish_reason": "stop"}],
         "usage": {"prompt_tokens": 300, "completion_tokens": 900}},
    ]
    sent = []

    def post(payload):
        sent.append(payload)
        return replies.pop(0)

    client = OpenRouterAgentClient("k", search_fn=lambda q, n: [{"title": "A", "link": "https://a.fr", "snippet": "s"}],
                                   fetch_fn=lambda url: "Texte de la page. " * 100, post=post)
    writer = AgentWriter(client, model="anthropic/claude-opus-5.5", system="sys")
    data = writer.write("Mot-clé : tache")
    assert data["slug"] == "enlever-tache-de-gras"
    roles = [m["role"] for m in client.transcript]
    assert roles[:2] == ["system", "user"] and roles.count("tool") == 2
    report = writer.report()
    assert report["web_searches"] == 1 and report["web_fetches"] == 1 and report["cost_usd"] > 0


def test_openrouter_bridge_hard_stop_and_explicit_fetch_error():
    from app.services.seo.agent_writer_openrouter import AgentBudgetExceeded, OpenRouterAgentClient

    def post(payload):
        return {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
            {"id": "1", "type": "function", "function": {"name": "web_fetch", "arguments": '{"url": "https://x.fr"}'}}]},
            "finish_reason": "tool_calls"}], "usage": {"prompt_tokens": 10, "completion_tokens": 1, "cost": 2.0}}

    client = OpenRouterAgentClient("k", search_fn=lambda q, n: [], fetch_fn=lambda url: "", post=post, max_cost_usd=3.0)
    client.seen_urls.add("x.fr/")
    with pytest.raises(AgentBudgetExceeded):
        AgentWriter(client, model="anthropic/claude-opus-5.5", system="s").write("kw")
    assert "ÉCHEC DE LECTURE" in [m for m in client.transcript if m["role"] == "tool"][0]["content"]


def test_failed_fetches_do_not_consume_page_budget_and_are_reported():
    from app.services.seo.agent_writer_openrouter import OpenRouterAgentClient

    pages = {"https://ok.fr": "Texte lu. " * 200, "https://court.fr": "Trop court"}
    urls = ["https://bloque.fr", "https://ok.fr", "https://court.fr", "https://vide2.fr"]
    client = OpenRouterAgentClient("k", search_fn=lambda q, n: [{"url": u} for u in urls],
                                   fetch_fn=lambda url: pages.get(url, ""), max_fetches=1, max_failed_fetches=2)
    client._run_tool("web_search", {"query": "q"})
    assert "ÉCHEC DE LECTURE" in client._run_tool("web_fetch", {"url": "https://bloque.fr"})
    assert client._run_tool("web_fetch", {"url": "https://ok.fr"}).startswith("Texte lu")
    assert client.fetches == 1 and client.failed_fetches == 1
    assert "Limite de pages lues" in client._run_tool("web_fetch", {"url": "https://ok.fr"})
    client.fetches = 0
    assert "ÉCHEC DE LECTURE (10 caractères)" in client._run_tool("web_fetch", {"url": "https://court.fr"})
    assert "Limite d'échecs" in client._run_tool("web_fetch", {"url": "https://vide2.fr"})
    assert [e["failed"] for e in client.fetch_log] == [True, False, True]


def test_report_keeps_raw_text_and_fetch_log_when_json_fails():
    from app.services.seo.agent_writer_openrouter import OpenRouterAgentClient

    replies = [{"choices": [{"message": {"role": "assistant", "content": '{"sources": []}'}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}} for _ in range(2)]
    client = OpenRouterAgentClient("k", search_fn=lambda q, n: [], fetch_fn=lambda url: "",
                                   post=lambda payload: replies.pop(0))
    writer = AgentWriter(client, model="anthropic/claude-opus-5.5", system="s")
    with pytest.raises(AgentWriterError):
        writer.write("kw")
    report = writer.report()
    assert report["raw_text_head"] == '{"sources": []}' and report["fetch_log"] == [] and report["search_log"] == []


def test_page_fetcher_uses_reader_fallback_but_respects_robots():
    from app.services.seo.agent_writer_openrouter import page_fetcher

    class Cache:
        timeout = 8

        def __init__(self, allowed):
            self._allowed = allowed

        def get_html(self, url):
            return None

        def allowed(self, url):
            return self._allowed

    fallback = lambda url: ("Texte rendu par le lecteur de secours. " * 50, 200)
    fetch = page_fetcher(Cache(True), fallback=fallback)
    assert fetch("https://x.fr").startswith("Texte rendu")
    assert fetch.last["method"] == "secours" and fetch.last["status"] == 200 and fetch.last["html_chars"] == 0
    limited = page_fetcher(Cache(True), fallback=lambda url: ("", 429))
    assert limited("https://x.fr") == "" and "limite de débit" in limited.last["note"]
    assert page_fetcher(Cache(False), fallback=fallback)("https://x.fr") == ""
    assert page_fetcher(Cache(True), fallback=None)("https://x.fr") == ""


def test_short_extracted_page_fails_without_using_the_budget():
    from app.services.seo.agent_writer_openrouter import OpenRouterAgentClient

    pages = {"https://court.fr": "a" * 300, "https://long.fr": "a" * 2000}
    client = OpenRouterAgentClient("k", search_fn=lambda q, n: [{"link": u} for u in pages], fetch_fn=lambda url: pages[url],
                                   max_fetches=1)
    client._run_tool("web_search", {"query": "q"})
    assert "ÉCHEC DE LECTURE (300 caractères)" in client._run_tool("web_fetch", {"url": "https://court.fr"})
    assert client.fetches == 0 and client.failed_fetches == 1
    assert client._run_tool("web_fetch", {"url": "https://long.fr"}) == "a" * 2000
    assert client.fetches == 1 and client.fetch_log[-1]["chars"] == 2000


def test_page_fetcher_raises_timeout_for_the_agent_only():
    from app.services.seo.agent_writer_openrouter import AGENT_FETCH_TIMEOUT_SECONDS, page_fetcher
    from app.services.seo.page_cache import DEFAULT_TIMEOUT_SECONDS, PageCache

    shared = PageCache(fetcher=lambda url, timeout: None)
    assert shared.timeout == DEFAULT_TIMEOUT_SECONDS
    page_fetcher(shared, fallback=None)
    assert shared.timeout == AGENT_FETCH_TIMEOUT_SECONDS == 15.0
    assert PageCache().timeout == DEFAULT_TIMEOUT_SECONDS


def test_agent_settings_are_editable_and_bounded():
    from pydantic import ValidationError

    from app.schemas.pipeline import PipelineSettingsUpdate

    update = PipelineSettingsUpdate(agent_max_cost_usd=1.7, agent_reader_fallback=False)
    assert update.agent_max_cost_usd == 1.7 and update.agent_reader_fallback is False
    for bad in (0, -1, 25):
        with pytest.raises(ValidationError):
            PipelineSettingsUpdate(agent_max_cost_usd=bad)


def test_fetch_refuses_urls_absent_from_search_results():
    from app.services.seo.agent_writer_openrouter import OpenRouterAgentClient

    fetched = []
    client = OpenRouterAgentClient(
        "k", search_fn=lambda q, n: [{"url": "https://www.inserm.fr/dossier/chronobiologie/?utm=1"}],
        fetch_fn=lambda url: fetched.append(url) or "a" * 2000)
    client._run_tool("web_search", {"query": "inserm"})
    assert client._run_tool("web_fetch", {"url": "https://www.cdc.gov/invente.html"}) == (
        "URL inventée : choisis une URL issue d'une recherche.")
    assert fetched == [] and client.fetches == 0 and client.failed_fetches == 1
    assert client.fetch_log[-1]["method"] == "refusée"
    # Même page, écrite autrement (schéma, www, barre finale) : acceptée.
    assert client._run_tool("web_fetch", {"url": "http://inserm.fr/dossier/chronobiologie?utm=1"}) == "a" * 2000
    assert client.fetches == 1


def test_invented_urls_count_in_the_failure_cap():
    from app.services.seo.agent_writer_openrouter import OpenRouterAgentClient

    client = OpenRouterAgentClient("k", search_fn=lambda q, n: [], fetch_fn=lambda url: "a" * 2000)
    for i in range(6):
        assert client._run_tool("web_fetch", {"url": f"https://invente{i}.fr"}).startswith("URL inventée")
    assert client._run_tool("web_fetch", {"url": "https://invente7.fr"}) == (
        "Limite d'échecs de lecture atteinte : rédige avec ce que tu as déjà.")
    assert client.fetches == 0 and client.failed_fetches == 6


def test_bridge_reasoning_effort_and_tool_free_review_call_share_the_budget():
    from app.services.seo.agent_writer_openrouter import AgentBudgetExceeded, OpenRouterAgentClient

    sent = []

    def post(payload):
        sent.append(payload)
        return {"choices": [{"message": {"role": "assistant", "content": '{"contradictions": []}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.6}}

    client = OpenRouterAgentClient("k", search_fn=lambda q, n: [], fetch_fn=lambda url: "", post=post,
                                   reasoning_effort="medium", max_cost_usd=1.0)
    assert client.complete("sys", "article") == '{"contradictions": []}'
    assert sent[0]["reasoning"] == {"effort": "medium"} and "tools" not in sent[0]
    assert [m["role"] for m in sent[0]["messages"]] == ["system", "user"] and client.transcript == []
    with pytest.raises(AgentBudgetExceeded):
        client.complete("sys", "article")
    assert OpenRouterAgentClient("k", search_fn=None, fetch_fn=None, reasoning_effort="ultra").reasoning_effort == "low"
