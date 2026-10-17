from app.services.seo.agent_generation import assembly_errors, structure_errors

GOOD = {
    "title": "T",
    "content_html": ("<p>Réponse directe au lecteur, avec ce qu'il doit faire tout de suite.</p>"
                     "<h2>Pourquoi</h2><p>Parce que le gras repousse l'eau, il faut un produit qui l'attrape.</p>"
                     "<h2>Le geste qui sauve votre vêtement</h2><p>Agissez avant le premier lavage.</p>"),
    "faq": [{"question": f"q{i}", "answer": "a"} for i in range(4)],
}


def test_assembly_accepts_clean_article():
    assert assembly_errors(GOOD) == []


def test_assembly_flags_faq_count_body_faq_and_duplicates():
    bad = {**GOOD, "faq": [], "content_html": GOOD["content_html"]
           + "<h2>Pourquoi</h2><p>x</p><h2>Questions fréquentes</h2><p>q</p>"}
    errors = " | ".join(assembly_errors(bad))
    assert "3 à 5 questions" in errors and "section FAQ" in errors and "répété" in errors

    six_questions = {**GOOD, "faq": [{"question": f"q{i}", "answer": "a"} for i in range(6)]}
    assert "3 à 5 questions" in " | ".join(assembly_errors(six_questions))
    five_questions = {**GOOD, "faq": [{"question": f"q{i}", "answer": "a"} for i in range(5)]}
    assert assembly_errors(five_questions) == []


def test_only_hard_faults_trigger_corrections():
    from app.services.seo.agent_generation import (
        announced_count_errors, html_render_errors, link_errors,
    )

    assert structure_errors("<p>Intro.</p><h2>A</h2><h3>B</h3><p>x</p><h3>C</h3><p>y</p>", "T") == []
    assert any("tiret" in e.lower() for e in structure_errors("<p>Un texte — avec un tiret long.</p><h2>A</h2><p>x</p>", "T"))
    long_intro = "<p>" + "mot " * 160 + "</p><h2>A</h2><p>" + "corps " * 1200 + "</p>"
    assert structure_errors(long_intro, "T") == []  # 160 mots mais moins de 15 %
    assert len(link_errors('<a href="https://w.be/x">a</a> <a href="https://w.be/x/">b</a>')) == 1
    html = ("<p>i</p><h2>La méthode en quatre gestes</h2><p>x</p><ul><li>a</li><li>b</li><li>c</li><li>d</li></ul>"
            "<table><tr><td>a</td><td>b</td></tr><tr><td>c</td></tr></table>")
    render = " | ".join(html_render_errors(html))
    assert "liste numérotée" in render and "en-tête" in render and "longueurs différentes" in render
    assert announced_count_errors("<p>i</p><h2>Les trois erreurs à éviter</h2><ol><li>a</li><li>b</li></ol>")
    assert not announced_count_errors("<p>i</p><h2>Les trois erreurs à éviter</h2><ol><li>a</li><li>b</li><li>c</li></ol>")


def test_competitor_and_prose_count_hard_faults():
    from app.services.seo.agent_generation import competitor_errors, fact_errors, prose_count_errors

    candidate = {
        "content_html": ('<p>Idéal le reconnaît, et <a href="https://www.linge-net.com/blog/x">ce guide</a> aussi. '
                         "Les sites concurrents se trompent.</p>"),
        "competitors": [{"url": "https://www.ideal.fr/a"}, {"url": "https://www.linge-net.com/blog/x"}],
        "sources": [{"url": "https://www.60millions-mag.com/a"}, {"url": "https://www.ideal.fr/a"}],
    }
    errors = " | ".join(competitor_errors(candidate))
    assert "Lien vers un concurrent" in errors and "linge-net" in errors
    assert "sites concurrents" in errors and "Seulement 1 domaine" in errors
    assert "concurrent apparaît dans" in errors
    assert prose_count_errors("<p>Retenez deux gestes à faire dans l'ordre :</p><ol><li>a</li><li>b</li><li>c</li></ol>")
    assert prose_count_errors("<p>Retenez 2 gestes :</p><ol><li>a</li><li>b</li><li>c</li></ol>")
    assert prose_count_errors("<p>Retenez un seul geste :</p><ol><li>a</li><li>b</li></ol>")
    assert not prose_count_errors("<p>Retenez trois gestes :</p><ol><li>a</li><li>b</li><li>c</li></ol>")
    assert not prose_count_errors("<p>Attendez deux heures avant de recommencer.</p>")
    assert not prose_count_errors("<blockquote>Les deux gestes sont parfois confondus.</blockquote>"
                                  "<ol><li>a</li><li>b</li></ol>")
    assert not prose_count_errors("<p>La dose est de 2 mg.</p><ol><li>a</li><li>b</li></ol>")
    assert not prose_count_errors("<table><tr><td>Deux gestes</td></tr></table>"
                                  "<ol><li>a</li><li>b</li></ol>")
    assert not prose_count_errors("<p>Retenez deux gestes dans cette phrase, sans liste à suivre.</p>")


def test_facts_require_exact_quote_and_declared_source():
    from app.services.seo.agent_generation import fact_errors, self_review_errors

    valid = {
        "sources": [{"url": "https://example.com/guide/?utm_source=test"}],
        "facts": [{"value": "20 minutes", "source_url": "http://www.example.com/guide/#section",
                   "quote": "20 minutes"}],
        "self_review": {"notes": "Chaque fait est relié à sa source."},
    }
    assert fact_errors(valid) == []
    assert self_review_errors(valid) == []

    invalid = {
        "sources": [{"url": "https://example.com/guide"}],
        "facts": [{"value": "20 minutes", "source_url": "https://other.example/guide", "quote": ""}],
    }
    errors = " | ".join(fact_errors(invalid))
    assert "citation exacte" in errors and "n'apparaît pas" in errors
    assert self_review_errors({"self_review": {"notes": "Ce point vient de connaissances générales."}})


def test_fact_url_matching_decodes_path_and_self_review_handles_negation_and_agreement():
    from app.services.seo.agent_generation import fact_errors, self_review_errors

    candidate = {
        "sources": [{"url": "https://example.com/guide/été"}],
        "facts": [{"value": "20 minutes", "source_url": "http://www.example.com/guide/%C3%A9t%C3%A9#details",
                   "quote": "20 minutes"}],
    }
    assert fact_errors(candidate) == []

    assert self_review_errors({"self_review": {"notes": "Aucun fait non sourcé. Rien n'est écrit de mémoire."}}) == []
    assert self_review_errors({"self_review": {"notes": "Deux chiffres non vérifiés."}})
    assert self_review_errors({"self_review": {"notes": "Une mise en garde non sourcée."}})
    assert self_review_errors({"self_review": {"notes": "Les faits viennent de connaissances générales, pas d'une source lue."}})
    assert self_review_errors({"self_review": {"notes": "Il n'y a pas de fait non vérifié."}}) == []
    assert self_review_errors({"self_review": {"notes": "Je n'ai rien écrit de mémoire."}}) == []
    assert self_review_errors({"self_review": {"notes": "Aucun fait non sourcé, mais deux chiffres restent non vérifiés."}})
    assert self_review_errors({"self_review": {"notes": "Domaines admissibles lus : 2 sur 3 requis."}}) == []


def test_competitor_matching_uses_registered_domain_without_suffix_false_positive():
    from app.services.seo.agent_generation import competitor_errors

    candidate = {
        "content_html": '<p><a href="https://blog.ideal.fr/guide">guide</a></p>',
        "competitors": [{"url": "https://www.ideal.fr/a"}],
        "sources": [{"url": "https://notideal.fr/a"}, {"url": "https://one.example/a"},
                    {"url": "https://two.example/a"}, {"url": "https://three.example/a"}],
    }
    errors = " | ".join(competitor_errors(candidate))
    assert "Lien vers un concurrent" in errors
    assert "Seulement" not in errors

    clean = {**candidate, "sources": [{"url": "https://notideal.fr/a"}, {"url": "https://one.example/a"},
                                        {"url": "https://two.example/a"}, {"url": "https://three.example/a"}]}
    ideal_text = {**clean, "content_html": "<p>Idéal le reconnaît.</p>"}
    assert any("ideal" in error for error in competitor_errors(ideal_text))
    assert not any("concurrent" in error.lower() for error in competitor_errors(
        {**clean, "content_html": "<p>Le moment idéal arrive.</p>"}))
    assert not any("concurrent" in error.lower() for error in competitor_errors(
        {**clean, "content_html": "<p>La température idéale convient.</p>"}))

    ariel = {**clean, "competitors": [{"url": "https://ariel.co.uk/a"}],
             "content_html": "<p>Ariel conseille cette méthode.</p>"}
    assert any("ariel" in error for error in competitor_errors(ariel))

    elle = {**clean, "competitors": [{"url": "https://elle.fr/a"}]}
    assert not any("concurrent" in error.lower() for error in competitor_errors(
        {**elle, "content_html": "<p>Elle se lave à 30 °C.</p>"}))
    assert not any("concurrent" in error.lower() for error in competitor_errors(
        {**elle, "content_html": "<p>Il faut qu’elle sèche.</p>"}))
    assert any("elle" in error for error in competitor_errors(
        {**elle, "content_html": "<p>Selon Elle, ce produit convient.</p>"}))
    assert any("elle" in error for error in competitor_errors(
        {**elle, "content_html": "<p>Le magazine Elle recommande ce produit.</p>"}))
    assert not any("concurrent" in error.lower() for error in competitor_errors(
        {**elle, "content_html": "<ul><li>Elle sèche vite à l'air.</li></ul>"}))
    assert not any("concurrent" in error.lower() for error in competitor_errors(
        {**elle, "content_html": "<h2>Le lin</h2><p>Elle se froisse vite.</p>"}))
    assert not any("concurrent" in error.lower() for error in competitor_errors(
        {**elle, "content_html": "<p>Deux précautions : Elle doit sécher à plat.</p>"}))

    public_sources = {**candidate, "competitors": [], "sources": [
        {"url": "https://sante.gouv.fr/a"}, {"url": "https://service-public.gouv.fr/a"},
        {"url": "https://one.example/a"},
    ]}
    assert not any("Seulement" in error for error in competitor_errors(public_sources))


def test_judge_unsourced_figure_becomes_a_hard_fault_with_facts_sent():
    from types import SimpleNamespace

    from app.services.seo import agent_generation

    seen = {}

    def fake_judge(content, call_fn, **kwargs):
        seen.update(kwargs)
        return {"blockers": [
            {"type": "unsourced_figure", "section": "Mélatonine", "detail": "« les plus de 60 ans » sans citation"},
            {"type": "heading_mismatch", "section": "Lumière", "detail": "le titre promet le retour"},
            {"type": "contradiction", "section": "x", "detail": "informatif"}]}

    import app.services.seo.editorial_judge as judge_module
    original = judge_module.judge_article
    judge_module.judge_article = fake_judge
    try:
        orch = SimpleNamespace(context={}, _write_pass=lambda *a: "")
        candidate = {"content_html": "<p>x</p>", "title": "T",
                     "facts": [{"value": "1 h par jour", "quote": "une heure par jour", "source_url": "https://inserm.fr/a"}],
                     "competitors": [{"url": "https://www.lonelyplanet.fr/x"}]}
        errors = agent_generation.judge_errors(orch, None, candidate)
    finally:
        judge_module.judge_article = original
    assert len(errors) == 2
    assert "« les plus de 60 ans » sans citation" in errors[0] and "citation exacte" in errors[0]
    assert "Titre en désaccord" in errors[1]
    assert seen["facts"] == ["1 h par jour — « une heure par jour » (source : https://inserm.fr/a)"]
    assert seen["strict_facts"] is True and seen["competitors"] == ["lonelyplanet.fr"]


def test_strict_judge_prompt_exempts_shown_calculations_and_examples():
    from app.services.seo.editorial_judge import STRICT_FACTS_CALCULATION_RULE, build_judge_prompt

    strict = build_judge_prompt("<p>x</p>", title="T", keyword="k", brief={}, facts=["f"], reference_figures=[],
                                strict_facts=True)
    loose = build_judge_prompt("<p>x</p>", title="T", keyword="k", brief={}, facts=["f"], reference_figures=[])
    assert STRICT_FACTS_CALCULATION_RULE in strict and STRICT_FACTS_CALCULATION_RULE not in loose
    assert "calcul montré" in STRICT_FACTS_CALCULATION_RULE and "exemple" in STRICT_FACTS_CALCULATION_RULE


def test_hard_stop_during_a_correction_round_keeps_the_round_zero_article():
    from app.services.seo.agent_generation import correction_rounds
    from app.services.seo.agent_writer_openrouter import AgentBudgetExceeded

    class Writer:
        def correct(self, errors):
            raise AgentBudgetExceeded("arrêt dur : coût cumulé 1.02 $ > 1.00 $")

    first = {"title": "Tour 0", "content_html": "<p>article</p>"}
    report: dict = {"rounds": []}
    best, errors, plag = correction_rounds(Writer(), lambda c: (["faute"], {"status": "clean"}), first, report)
    assert best is first and errors == ["faute"] and plag == {"status": "clean"}
    assert report["rounds"][0] == {"round": 0, "errors": ["faute"]}
    assert "arrêt dur" in report["rounds"][1]["error"] and report["remaining_errors"] == ["faute"]


def test_consistency_review_turns_contradictions_into_a_correction_round():
    import json

    from app.services.seo.agent_generation import consistency_review, review_round

    reply = json.dumps({"contradictions": [{"passage": "Chaque matinée dehors vous rapproche de l'heure locale",
                                            "probleme": "faux vers l'ouest selon la règle de l'article",
                                            "correction": "distinguer l'est et l'ouest"}]})
    prompts = []

    def complete(system, user):
        prompts.append(user)
        return reply

    candidate = {"content_html": "<p>article</p>",
                 "facts": [{"value": "1 h par jour", "quote": "une heure par jour", "source_url": "https://cdc.gov/x"}]}
    errors = consistency_review(complete, candidate)
    assert len(errors) == 1 and "Chaque matinée dehors" in errors[0] and "distinguer l'est" in errors[0]
    assert "une heure par jour" in prompts[0] and "<p>article</p>" in prompts[0]

    class Writer:
        def __init__(self):
            self.sent = None

        def correct(self, errs):
            self.sent = errs
            return {"content_html": "<p>corrigé</p>"}

    writer, report = Writer(), {"rounds": []}
    best, errs, _ = review_round(writer, lambda c: ([], {"status": "clean"}), complete, candidate, [], {}, report)
    assert best["content_html"] == "<p>corrigé</p>" and writer.sent == errors
    assert report["consistency_review"]["contradictions"] == errors and report["rounds"][-1]["round"] == "relecture"


def test_consistency_review_keeps_article_when_clean_or_on_error():
    from app.services.seo.agent_generation import review_round

    article, report = {"content_html": "<p>a</p>"}, {"rounds": []}
    best, _, _ = review_round(None, None, lambda s, u: '{"contradictions": []}', article, [], {}, report)
    assert best is article and report["rounds"] == []

    def boom(system, user):
        raise RuntimeError("arrêt dur : coût cumulé 1.01 $ > 1.00 $")

    best, _, _ = review_round(None, None, boom, article, [], {}, report)
    assert best is article and "arrêt dur" in report["consistency_review"]["error"]


def test_quotes_must_come_from_fact_quotes_with_tolerant_matching():
    from app.services.seo.agent_generation import quote_errors

    facts = [{"quote": "L’Anses déconseille la consommation de compléments alimentaires à base de mélatonine "
                       "aux femmes enceintes ou allaitantes", "source_url": "https://anses.fr/a"}]
    ok = ("<p>Selon l'Anses, elle « déconseille la consommation de compléments alimentaires » "
          "et vise « l'anses deconseille la consommation … aux femmes enceintes ou allaitantes ». "
          "Un « mot court » passe.</p>")
    assert quote_errors({"facts": facts, "content_html": ok}) == []
    bad = "<p>Vidal écrit « un temps d'adaptation au-delà de six fuseaux vers l'est ».</p>"
    errors = quote_errors({"facts": facts, "content_html": bad})
    assert len(errors) == 1 and "au-delà de six fuseaux" in errors[0]


def test_source_balance_flags_a_domain_over_half_of_the_facts():
    from app.services.seo.agent_generation import source_balance_errors

    def facts(urls):
        return {"facts": [{"source_url": u} for u in urls]}

    vidal = ["https://www.vidal.fr/a"] * 10 + ["https://anses.fr/b"] * 4 + ["https://sante.fr/c"] * 3
    errors = source_balance_errors(facts(vidal))
    assert len(errors) == 1 and "vidal.fr porte 10 faits sur 17" in errors[0]
    assert source_balance_errors(facts(["https://vidal.fr/a"] * 2 + ["https://anses.fr/b"] * 2)) == []
    assert source_balance_errors(facts(["https://www.cdc.gov/a", "https://wwwnc.cdc.gov/b", "https://anses.fr/c",
                                        "https://inserm.fr/d", "https://cdc.gov/e"])) != []
    assert source_balance_errors(facts(["https://vidal.fr/a"] * 3)) == []
