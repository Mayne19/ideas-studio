import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "compare_writers.py"
_spec = importlib.util.spec_from_file_location("compare_writers", _PATH)
cw = importlib.util.module_from_spec(_spec)
sys.modules["compare_writers"] = cw
_spec.loader.exec_module(cw)


def test_labels_are_letters_covering_every_model_once():
    models = ["a/one", "b/two", "c/three", "a/one"]
    labels = cw.assign_labels(models, seed=3)
    assert list(labels) == ["A", "B", "C"]
    assert sorted(labels.values()) == ["a/one", "b/two", "c/three"]


def test_labels_are_reproducible_with_seed_and_shuffled():
    models = [f"m/{i}" for i in range(8)]
    assert cw.assign_labels(models, seed=1) == cw.assign_labels(models, seed=1)
    orders = {tuple(cw.assign_labels(models, seed=s).values()) for s in range(10)}
    assert len(orders) > 1


def test_mapping_lists_anonymous_files_per_article():
    mapping = cw.build_mapping({"A": "x/1", "B": "y/2"}, ["art1", "art2"], "judge/m")
    assert mapping["labels"] == {"A": "x/1", "B": "y/2"}
    assert mapping["articles"]["art2"] == {"A": "art2/A.html", "B": "art2/B.html"}
    assert mapping["judge_model"] == "judge/m"
    # Les noms de fichiers ne trahissent pas le modèle.
    assert all("x/1" not in path for paths in mapping["articles"].values() for path in paths.values())


def test_aggregate_means_per_label():
    rows = [
        {"label": "B", "content_score": 80, "hard_failures": 1, "cost": 0.01, "cost_estimated": False},
        {"label": "A", "content_score": 70, "hard_failures": 2, "cost": 0.002, "cost_estimated": False},
        {"label": "A", "content_score": None, "hard_failures": 0, "cost": 0.004, "cost_estimated": True},
        {"label": "B", "content_score": 60, "hard_failures": 3, "cost": None},
        {"label": "B", "content_score": None, "hard_failures": 0, "cost": None, "error": "boom"},
    ]
    summary = {s["label"]: s for s in cw.aggregate(rows)}
    assert list(summary) == ["A", "B"]
    assert summary["A"]["mean_content_score"] == 70
    assert summary["A"]["judged"] == 1
    assert summary["A"]["mean_hard_failures"] == 1
    assert summary["A"]["cost_per_article"] == 0.003
    assert summary["A"]["cost_estimated"] is True
    assert summary["B"]["mean_content_score"] == 70
    assert summary["B"]["mean_hard_failures"] == 2  # la rédaction en échec est exclue
    assert summary["B"]["failed"] == 1
    assert summary["B"]["cost_per_article"] == 0.01


def test_markdown_table_rows():
    table = cw.markdown_table([
        {"label": "A", "articles": 2, "failed": 0, "judged": 2, "mean_content_score": 71.5,
         "mean_hard_failures": 0.5, "cost_per_article": 0.0031, "cost_estimated": False},
        {"label": "B", "articles": 2, "failed": 2, "judged": 0, "mean_content_score": None,
         "mean_hard_failures": None, "cost_per_article": None, "cost_estimated": False},
    ])
    lines = table.splitlines()
    assert lines[0].startswith("| modèle |")
    assert lines[2] == "| A | 2 | 71.5 (2 jugé(s)) | 0.5 | 0.0031 |"
    assert lines[3] == "| B | 2 (2 en échec) | - | - | ? |"


def test_call_cost_prefers_openrouter_usage_cost():
    assert cw.call_cost({"cost": 0.0123}, "x/y") == (0.0123, False)
    cost, estimated = cw.call_cost({"prompt_tokens": 1000, "completion_tokens": 1000}, "deepseek/deepseek-chat")
    assert estimated and cost == 0.00075
    assert cw.call_cost({}, "unknown/model") == (None, True)


def test_parse_word_range():
    assert cw.parse_word_range("1200-1800 mots") == (1200, 1800)
    assert cw.parse_word_range(None) == (None, None)


def test_saved_fact_assignment_is_rebuilt():
    from app.services.seo.section_writer import OutlineSection

    facts = [{"fact_id": "F1", "claim": "a"}, {"fact_id": "F2", "claim": "b"}]
    sections = [OutlineSection(heading="Un"), OutlineSection(heading="Deux")]
    assignment = {"intro": ["F2"], "sections": [{"heading": "Un", "fact_ids": ["F1"]},
                                                {"heading": "Deux", "fact_ids": ["F9"]}], "unassigned": []}
    rebuilt = cw.section_facts_from_assignment(assignment, facts, sections)
    assert rebuilt["intro"] == [facts[1]] and rebuilt[0] == [facts[0]] and rebuilt[1] == []
    assert cw.section_facts_from_assignment(assignment, facts, sections[:1]) is None
