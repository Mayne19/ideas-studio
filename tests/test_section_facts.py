"""Faits par section : chaque fait va à une seule section, avec son URL."""
from app.services.seo.section_writer import (
    SectionWriter,
    assign_facts_to_sections,
    build_section_brief,
    collect_writer_facts,
    group_outline_sections,
)

OUTLINE = {"sections": [
    {"heading": "Les prix de Webflow", "level": 2, "key_points": ["abonnement", "plans"]},
    {"heading": "Le coût de l'hébergement WordPress", "level": 2, "key_points": ["hébergeur", "serveur"]},
    {"heading": "La prise en main", "level": 2, "purpose": "apprentissage de l'interface"},
]}

LEDGER = [
    {"fact_id": "F1", "claim": "Le plan Basic de Webflow coûte 14 $ par mois", "figure": "14 $",
     "url": "https://webflow.com/pricing", "usage_hint": "prix webflow"},
    {"fact_id": "F2", "claim": "Un hébergement WordPress mutualisé démarre à 3 € par mois",
     "figure": "3 €", "url": "https://example-host.fr/offres", "usage_hint": "hébergement wordpress"},
    {"fact_id": "F3", "claim": "L'interface de Webflow demande environ 20 heures d'apprentissage",
     "figure": "20 heures", "url": "https://university.webflow.com", "usage_hint": "prise en main"},
    {"fact_id": "F4", "claim": "Les plans Webflow annuels sont facturés avec une remise",
     "url": "https://webflow.com/pricing"},
    {"fact_id": "F5", "claim": "La météo de Lyon était ensoleillée", "url": "https://meteo.example"},
]


def _assignment():
    sections = group_outline_sections(OUTLINE)
    facts = collect_writer_facts({"fact_ledger": LEDGER})
    return sections, assign_facts_to_sections(facts, sections, reader_question="Combien coûte Webflow ?")


def test_each_fact_goes_to_a_single_section():
    sections, assignment = _assignment()
    ids_per_section = [[f["fact_id"] for f in assignment[i]] for i in range(len(sections))]
    flat = [fid for ids in ids_per_section for fid in ids]
    assert len(flat) == len(set(flat))
    assert "F1" in ids_per_section[0] and "F4" in ids_per_section[0]
    assert ids_per_section[1] == ["F2"]
    assert ids_per_section[2] == ["F3"]


def test_unrelated_fact_is_not_forced_into_a_section():
    _, assignment = _assignment()
    assert [f["fact_id"] for f in assignment["unassigned"]] == ["F5"]


def test_per_section_cap_is_respected():
    sections = group_outline_sections(OUTLINE)
    facts = [{"fact_id": f"F{i}", "claim": f"Prix Webflow plan {i}", "url": "u"} for i in range(10)]
    assignment = assign_facts_to_sections(facts, sections, per_section=3)
    assert len(assignment[0]) == 3


def test_section_prompt_contains_only_its_facts_with_url():
    sections, assignment = _assignment()
    prompts: dict[str, str] = {}

    def fake(prompt, step, temperature):
        prompts[step] = prompt
        return "<p>" + "Texte concret et précis sur le sujet. " * 30 + "</p>"

    writer = SectionWriter(fake, "=== BRIEF ===", sections, section_facts=assignment)
    writer.write_article()
    first = prompts["WritingPass_Section_1"]
    second = prompts["WritingPass_Section_2"]
    assert "[F1]" in first and "https://webflow.com/pricing" in first
    assert "[F2]" not in first
    assert "[F2]" in second and "[F1]" not in second
    assert "[F1]" in prompts["WritingPass_Intro"]


def test_evidence_items_are_used_when_no_ledger():
    facts = collect_writer_facts({"evidence_items": [{"fact": "Fait A", "source_url": "https://a.fr"}]})
    assert facts == [{
        "fact_id": "F1", "claim": "Fait A", "figure": "", "url": "https://a.fr", "quote": "",
        "usage_hint": "", "date_or_as_of": "",
    }]


def test_shared_brief_has_questions_keywords_and_differentiation_but_no_facts():
    text = build_section_brief({
        "title": "T", "sub_questions": ["Q1 ?"], "related_questions": ["Q2 ?", "q1 ?"],
        "secondary_keywords": ["prix webflow"], "differentiation": "Coûts sur 3 ans",
        "evidence_items": [{"fact": "Fait répété"}],
    })
    assert "Q1 ?" in text and "Q2 ?" in text and text.count("q1 ?") == 0
    assert "prix webflow" in text
    assert "Coûts sur 3 ans" in text
    assert "Fait répété" not in text
