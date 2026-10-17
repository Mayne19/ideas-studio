from __future__ import annotations

from typing import Any

from experiments.editorial_agent_lab.editorial_agent.models import (
    ArticleDraft,
    ArticlePlan,
    ArticleRequest,
    FactRecord,
    FaqPlanItem,
    SectionPlan,
    SiteContext,
)
from experiments.editorial_agent_lab.editorial_agent.similarity import scan_exact_phrases
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
            value="3",
            definition="Nombre de concurrents lus.",
            source_url="https://example.com/fact",
            source_kind="official",
            verified=True,
        )]


class FakePlanner:
    def build_plan(self, request: Any, context: Any, competitors: Any, reader: Any, facts: Any) -> ArticlePlan:
        return make_plan()


class FakeWriter:
    def write(self, request: Any, context: Any, competitors: Any, reader: Any, facts: Any, plan: Any) -> ArticleDraft:
        return make_draft()


class FakeSimilarity:
    def scan(self, content_html: str, sources: list[str]) -> list[dict[str, object]]:
        return []


def test_workflow_runs_without_a_paid_model_call() -> None:
    agent = EditorialAgent(FakeResearch(), FakePlanner(), FakeWriter(), FakeSimilarity())
    result = agent.generate(
        ArticleRequest(keyword="choisir un outil"),
        SiteContext(site_name="Test", domain="example.com"),
    )
    assert result.report.blocking_issues == []
    assert result.plan.faq[0].question == "Que faire dans un cas particulier ?"
