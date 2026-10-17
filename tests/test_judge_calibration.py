"""Script d'étalonnage du juge : découpage de la FAQ Markdown et manifeste."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("judge_calibration", ROOT / "scripts" / "judge_calibration.py")
calibration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(calibration)


def test_faq_stops_at_the_next_h2_and_keeps_the_conclusion_in_the_body():
    content = ("# Titre\n\nIntroduction.\n\n## Questions fréquentes\n\n### Première question ?\n\nRéponse un.\n\n"
               "### Deuxième question ?\n\nRéponse deux.\n\n## Ce qu'il faut retenir\n\nLa conclusion.\n")
    body, faq = calibration._faq_from_markdown(content)
    assert [f["question"] for f in faq] == ["Première question ?", "Deuxième question ?"]
    assert faq[-1]["answer"] == "Réponse deux." and "conclusion" not in faq[-1]["answer"]
    assert "## Ce qu'il faut retenir" in body and "La conclusion." in body and "Première question" not in body


def test_manifest_has_the_corrected_id_and_reference_scores():
    manifest = json.loads((ROOT / "tests/data/judge_calibration/manifest.json").read_text(encoding="utf-8"))
    by_name = {a["name"]: a for a in manifest["articles"]}
    assert len(manifest["articles"]) == 9
    assert by_name["reste à vivre, ancien système"]["article_id"] == "e089f2ef-0c91-4a9a-8e18-a87ee6b2be7a"
    assert by_name["questionnaire en ligne"]["reference_score"] == 87
    for article in manifest["articles"]:
        if "path" in article:
            assert (ROOT / "tests/data/judge_calibration" / article["path"]).exists()


def test_validated_reference_files_split_into_body_and_faq():
    for name, questions in (("basilic-90.md", 5), ("budget-50-30-20-90.md", 3)):
        content = (ROOT / "tests/data/judge_calibration" / name).read_text(encoding="utf-8")
        body, faq = calibration._faq_from_markdown(content)
        assert len(faq) == questions and "Questions fréquentes" not in body
