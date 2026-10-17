from __future__ import annotations

from typing import Any

from experiments.editorial_agent_lab.editorial_agent.models import (
    ArticleDraft,
    EditorialAngle,
    ArticlePlan,
    ArticleRequest,
    FactRecord,
    FaqPlanItem,
    SectionPlan,
    SiteContext,
)
from experiments.editorial_agent_lab.editorial_agent.existing_pipeline_adapter import (
    ExistingPipelineWebAdapter,
)
from experiments.editorial_agent_lab.editorial_agent.angle import propose_angle, validate_angle
from experiments.editorial_agent_lab.editorial_agent.fact_ledger import assign_fact_ids, validate_fact_ledger
from experiments.editorial_agent_lab.editorial_agent.prompting import build_writer_context
from experiments.editorial_agent_lab.editorial_agent.writer import (
    SinglePassWriter,
    WriterOutputError,
    load_lab_prompt,
)
from experiments.editorial_agent_lab.editorial_agent.validation_pipeline import validate_article
from experiments.editorial_agent_lab.editorial_agent.reporting import build_run_report
from experiments.editorial_agent_lab.editorial_agent.review import ReviewLedger
from experiments.editorial_agent_lab.editorial_agent.benchmark import BenchmarkLedger, BenchmarkRun
from experiments.editorial_agent_lab.editorial_agent.similarity import scan_exact_phrases
from experiments.editorial_agent_lab.editorial_agent.planning import (
    build_reader_intent,
    validate_competitor_dossier,
    validate_plan_coverage,
    validate_source_diversity,
)
from experiments.editorial_agent_lab.editorial_agent.validators import (
    choose_best_version,
    validate_draft,
    validate_plan,
)
from experiments.editorial_agent_lab.editorial_agent.workflow import EditorialAgent


def make_plan() -> ArticlePlan:
    return ArticlePlan(
        intro_purpose="Installer le problème.",
        summary_callout="La réponse courte tient en quelques mots.",
        sections=[SectionPlan(
            heading="Choisir la bonne méthode",
            promise="Comparer les options utiles.",
            reader_question="Quelle option choisir ?",
            facts_to_use=["fact-1"],
        )],
        conclusion_heading="Le bon choix dépend de votre situation",
        faq=[FaqPlanItem(
            question="Que faire dans un cas particulier ?",
            reason_not_in_article="Le cas demande une réponse séparée.",
        )],
    )


def make_draft() -> ArticleDraft:
    return ArticleDraft(
        title="Un article utile",
        meta_title="Un article utile",
        meta_description="Une description utile.",
        slug="article-utile",
        content_html=(
            "<p>Voici le contexte du sujet.</p>"
            '<aside class="summary-callout"><strong>En résumé</strong> La réponse courte.</aside>'
            "<h2>Choisir la bonne méthode</h2>"
            "<p>Cette section explique les options et leurs différences.</p>"
            "<p>Le premier cas demande une comparaison simple pour éviter une mauvaise décision.</p>"
            "<p>Le deuxième cas dépend du budget, du temps disponible et du niveau de maîtrise.</p>"
            "<p>Un exemple concret permet de vérifier la méthode avant de l'utiliser.</p>"
            "<p>Les sources apportent les chiffres nécessaires et évitent les affirmations vagues.</p>"
            "<p>La décision finale doit rester liée à la situation réelle du lecteur.</p>"
            "<h2>Le bon choix dépend de votre situation</h2>"
            "<p>La conclusion laisse une idée claire.</p>"
            "<h2>FAQ</h2><p>Une réponse qui n'était pas dans l'article.</p>"
        ),
    )


def test_plan_requires_callout_and_section_contract() -> None:
    plan = make_plan()
    assert validate_plan(plan) == []

    invalid = plan.model_copy(update={"summary_callout": ""})
    issues = validate_plan(invalid)
    assert any(issue.code == "missing_summary_callout" and issue.blocking for issue in issues)


def test_draft_has_callout_and_conclusion_before_faq() -> None:
    assert validate_draft(make_draft(), make_plan()) == []


def test_similarity_reports_without_modifying_the_text() -> None:
    sentence = "Cette phrase identique doit être signalée par le scanner."
    findings = scan_exact_phrases(
        f"<p>{sentence}</p>",
        {"https://example.com/source": f"Un début. {sentence} Une fin."},
    )
    assert len(findings) == 1
    assert findings[0].similarity == 1.0
    assert findings[0].suggested_reformulation


def test_plagiarism_correction_is_targeted_and_not_a_general_rewrite() -> None:
    from experiments.editorial_agent_lab.editorial_agent.live_runner import _plagiarism_correction_errors

    errors = _plagiarism_correction_errors({"matches": [{
        "sentence": "Cette phrase est reprise telle quelle dans une autre page.",
        "url": "https://source.example/page",
    }]})
    assert len(errors) == 1
    assert "uniquement cette phrase" in errors[0]
    assert "sans modifier le reste" in errors[0]


def test_no_plagiarism_match_does_not_request_a_correction() -> None:
    from experiments.editorial_agent_lab.editorial_agent.live_runner import _plagiarism_correction_errors

    assert _plagiarism_correction_errors({"matches": []}) == []


def test_best_version_keeps_the_oldest_equal_safe_version() -> None:
    draft = make_draft()
    selected = choose_best_version([(1, draft, []), (2, draft, [])])
    assert selected[0] == 1


class FakeResearch:
    def search_competitors(self, keyword: str, domain: str, limit: int = 3) -> list[str]:
        return [
            "https://example.com/one",
            "https://example.com/two",
            "https://example.com/three",
        ][:limit]

    def fetch_page(self, url: str) -> str:
        return f"Contenu de {url}."

    def find_facts(self, keyword: str, reader: Any) -> list[FactRecord]:
        return [FactRecord(
            value=str(index),
            definition="Un fait vérifié.",
            quote=f"Le fait vérifié vaut {index}.",
            source_url=f"https://official-{index}.example/fact",
            source_kind="official",
            verified=True,
        ) for index in range(1, 4)]


class FakePlanner:
    def build_plan(self, request: Any, context: Any, competitors: Any, reader: Any, angle: Any, facts: Any) -> ArticlePlan:
        return make_plan()


class FakeCompetitorAnalyzer:
    def analyze(self, competitors: list[Any]) -> list[Any]:
        return [competitor.model_copy(update={
            "strengths": ["Une force"],
            "weaknesses": ["Une faiblesse"],
        }) for competitor in competitors]


class FakeWriter:
    def write(self, request: Any, context: Any, competitors: Any, reader: Any, angle: Any, facts: Any, plan: Any) -> ArticleDraft:
        return make_draft()


class FakeSimilarity:
    def scan(self, content_html: str, sources: list[str]) -> list[dict[str, object]]:
        return []


def test_workflow_runs_without_a_paid_model_call() -> None:
    agent = EditorialAgent(FakeResearch(), FakeCompetitorAnalyzer(), FakePlanner(), FakeWriter(), FakeSimilarity())
    result = agent.generate(
        ArticleRequest(keyword="choisir un outil"),
        SiteContext(site_name="Test", domain="example.com"),
    )
    assert result.report.blocking_issues == []
    assert result.plan.faq[0].question == "Que faire dans un cas particulier ?"


def test_existing_pipeline_adapter_filters_own_domain_and_duplicates() -> None:
    calls: list[tuple[str, int]] = []

    def search(query: str, limit: int) -> list[dict[str, str]]:
        calls.append((query, limit))
        return [
            {"url": "https://www.example.com/existing"},
            {"url": "https://competitor.fr/guide"},
            {"url": "https://competitor.fr/guide#section"},
            {"link": "https://second.fr/article"},
            {"url": "not-a-url"},
        ]

    adapter = ExistingPipelineWebAdapter(search_fn=search, fetch_fn=lambda url: "page")
    assert adapter.search_competitors("mot clé", "https://example.com", limit=3) == [
        "https://competitor.fr/guide",
        "https://second.fr/article",
    ]
    assert calls == [("mot clé", 10)]


def test_existing_pipeline_adapter_reports_empty_reads() -> None:
    adapter = ExistingPipelineWebAdapter(
        search_fn=lambda query, limit: [],
        fetch_fn=lambda url: "",
    )
    assert adapter.fetch_page("https://example.com/page") == ""
    assert adapter.stats()["pages_read"] == 0
    assert adapter.stats()["fetch_errors"]


def test_planning_requires_competitor_strengths_and_weaknesses() -> None:
    competitors = [
        {"url": "https://example.com", "title": "A", "content": "texte"},
    ]
    from experiments.editorial_agent_lab.editorial_agent.models import CompetitorPage

    pages = [CompetitorPage(**competitor) for competitor in competitors]
    issues = validate_competitor_dossier(pages)
    assert any(issue.code == "not_enough_competitors" for issue in issues)
    assert any(issue.code == "missing_competitor_strengths" for issue in issues)


def test_source_diversity_rejects_one_dominant_domain() -> None:
    facts = [
        FactRecord(value=str(index), definition="x", source_url="https://source.example/fact", source_kind="official", verified=True)
        for index in range(4)
    ]
    assert any(issue.code == "insufficient_source_diversity" for issue in validate_source_diversity(facts))
    assert any(issue.code == "dominant_source" for issue in validate_source_diversity(facts))


def test_plan_rejects_faq_overlap_with_body() -> None:
    plan = make_plan().model_copy(update={
        "faq": [FaqPlanItem(
            question="Quelle option choisir ?",
            reason_not_in_article="La question est prévue dans la FAQ.",
            facts_to_use=["faq-fact"],
        )],
    })
    issues = validate_plan_coverage(plan)
    assert any(issue.code == "faq_question_overlap" for issue in issues)


def test_reader_intent_uses_a_missing_competitor_topic() -> None:
    from experiments.editorial_agent_lab.editorial_agent.models import CompetitorPage

    reader = build_reader_intent("choisir un outil", [CompetitorPage(
        url="https://example.com",
        title="Concurrent",
        content="texte",
        missing_topics=["le coût réel"],
    )])
    assert reader.likely_trap == "le coût réel"


def test_fact_ledger_requires_exact_quote_and_loaded_source() -> None:
    facts = assign_fact_ids([FactRecord(
        value="12",
        definition="Un seuil.",
        source_url="https://official.example/fact",
        source_kind="official",
        verified=True,
    )])
    issues = validate_fact_ledger(facts, {"https://official.example/fact"})
    assert any(issue.code == "missing_fact_quote" for issue in issues)


def test_angle_must_be_distinct_and_supported() -> None:
    from experiments.editorial_agent_lab.editorial_agent.models import CompetitorPage

    reader = build_reader_intent("choisir un outil", [CompetitorPage(
        url="https://example.com",
        title="Concurrent",
        content="texte",
        missing_topics=["un calcul réel"],
    )])
    angle = propose_angle(reader, [], ["fact-1"])
    assert validate_angle(angle, {"fact-1"}) == []


def test_writer_context_contains_plan_and_callout_rule() -> None:
    context = build_writer_context(
        ArticleRequest(keyword="choisir un outil"),
        SiteContext(site_name="Test", domain="example.com"),
        [],
        build_reader_intent("choisir un outil", []),
        EditorialAngle(
            title="Un angle",
            reader_problem="Un problème",
            information_gain="Un gain",
            distinct_from_competitors=["Une différence"],
        ),
        [],
        make_plan(),
    )
    assert '"summary_callout"' in context
    assert "call out En résumé" in context


def test_single_pass_writer_calls_model_once_and_validates_json() -> None:
    calls: list[tuple[str, str]] = []

    def fake_call(system: str, user: str) -> str:
        calls.append((system, user))
        return make_draft().model_dump_json()

    writer = SinglePassWriter(fake_call, load_lab_prompt())
    draft = writer.write(
        ArticleRequest(keyword="choisir un outil"),
        SiteContext(site_name="Test", domain="example.com"),
        [],
        build_reader_intent("choisir un outil", []),
        EditorialAngle(
            title="Un angle",
            reader_problem="Un problème",
            information_gain="Un gain",
            distinct_from_competitors=["Une différence"],
        ),
        [],
        make_plan(),
    )
    assert draft.title == "Un article utile"
    assert len(calls) == 1
    assert "summary_callout" in calls[0][1]


def test_single_pass_writer_does_not_hide_a_correction_round() -> None:
    calls = 0

    def fake_call(system: str, user: str) -> str:
        nonlocal calls
        calls += 1
        return "ceci n'est pas du JSON"

    writer = SinglePassWriter(fake_call, load_lab_prompt())
    try:
        writer.write(
            ArticleRequest(keyword="choisir un outil"),
            SiteContext(site_name="Test", domain="example.com"),
            [],
            build_reader_intent("choisir un outil", []),
            EditorialAngle(
                title="Un angle",
                reader_problem="Un problème",
                information_gain="Un gain",
                distinct_from_competitors=["Une différence"],
            ),
            [],
            make_plan(),
        )
    except WriterOutputError:
        pass
    else:
        raise AssertionError("un JSON invalide doit être bloquant")
    assert calls == 1


def test_validation_pipeline_keeps_similarity_as_non_blocking_warning() -> None:
    from experiments.editorial_agent_lab.editorial_agent.models import CompetitorPage, SimilarityFinding

    competitors = [CompetitorPage(
        url=f"https://competitor-{index}.example",
        title=f"Concurrent {index}",
        content="Contenu lisible.",
        strengths=["Une force"],
        weaknesses=["Une lacune"],
    ) for index in range(3)]
    facts = [FactRecord(
        fact_id="fact-1",
        value="12",
        definition="Un seuil.",
        quote="Le seuil est de 12.",
        source_url="https://official.example/fact",
        source_kind="official",
        verified=True,
    )]
    report = validate_article(
        plan=make_plan(),
        draft=make_draft(),
        facts=facts,
        competitors=competitors,
        source_urls={"https://official.example/fact"},
        similarity_findings=[SimilarityFinding(
            sentence="Une phrase reprise suffisamment longue pour être signalée.",
            source_url="https://source.example/page",
            matched_text="Une phrase reprise suffisamment longue pour être signalée.",
            similarity=1.0,
        )],
    )
    assert report.passed is False
    assert report.blocking_count > 0
    assert any(issue.code == "similarity_warning" and not issue.blocking for issue in report.issues)


def test_run_report_contains_the_plan_and_blocking_issues() -> None:
    result = EditorialAgent(
        FakeResearch(),
        FakeCompetitorAnalyzer(),
        FakePlanner(),
        FakeWriter(),
        FakeSimilarity(),
    ).generate(
        ArticleRequest(keyword="choisir un outil"),
        SiteContext(site_name="Test", domain="example.com"),
    )
    report = build_run_report(result, model="fake-test", duration_s=1.2)
    assert report["model"] == "fake-test"
    assert report["plan"]["summary_callout"]
    assert "draft" in report


def test_human_review_cannot_approve_blocked_article() -> None:
    result = EditorialAgent(
        FakeResearch(),
        FakeCompetitorAnalyzer(),
        FakePlanner(),
        FakeWriter(),
        FakeSimilarity(),
    ).generate(
        ArticleRequest(keyword="choisir un outil"),
        SiteContext(site_name="Test", domain="example.com"),
    )
    from experiments.editorial_agent_lab.editorial_agent.models import ValidationIssue

    result.report.blocking_issues.append(ValidationIssue(
        code="test_blocker",
        message="Erreur bloquante de test.",
        blocking=True,
    ))
    ledger = ReviewLedger()
    try:
        ledger.record(result, decision="approved", reviewer="test", notes="ok")
    except ValueError:
        pass
    else:
        raise AssertionError("un article bloqué ne doit pas être approuvé")


def test_review_can_create_a_pending_rule_without_modifying_the_draft() -> None:
    result = EditorialAgent(
        FakeResearch(),
        FakeCompetitorAnalyzer(),
        FakePlanner(),
        FakeWriter(),
        FakeSimilarity(),
    ).generate(
        ArticleRequest(keyword="choisir un outil"),
        SiteContext(site_name="Test", domain="example.com"),
    )
    before = result.draft.content_html
    ledger = ReviewLedger()
    rule = ledger.propose_rule(
        rule_id="style.no_empty_opening",
        text="Ne pas ouvrir une section par une formule vide.",
        origin="review:test",
    )
    assert rule.status == "pending"
    assert result.draft.content_html == before


def test_benchmark_stays_pending_before_the_acceptance_sample() -> None:
    ledger = BenchmarkLedger()
    ledger.add(BenchmarkRun(
        topic="basilic",
        system="lab",
        human_score=90,
        blocking_errors=0,
        warnings=1,
        cost_usd=0,
        duration_s=1,
    ))
    decision = ledger.decide()
    assert decision.status == "PENDING"


def test_benchmark_can_return_no_go_for_blocking_errors() -> None:
    ledger = BenchmarkLedger()
    for index in range(10):
        topic = f"topic-{index % 5}"
        ledger.add(BenchmarkRun(topic, "lab", 90, 1 if index == 0 else 0, 0, 1, 1))
        ledger.add(BenchmarkRun(topic, "pipeline", 80, 0, 0, 1, 1))
    assert ledger.decide().status == "NO-GO"
