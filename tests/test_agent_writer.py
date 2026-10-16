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
