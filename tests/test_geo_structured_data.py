from types import SimpleNamespace

from app.services.seo.geo_expert_service import score_structured_data


def test_structured_data_builder_output_is_scored():
    draft = SimpleNamespace(structured_data_json={
        "status": "generated",
        "schemas": [{"@type": "BlogPosting"}, {"@type": "FAQPage"}],
    })
    assert score_structured_data(draft) == 65.0


def test_structured_data_plain_list_still_scored():
    assert score_structured_data({"structured_data_json": [{"@type": "Article"}]}) == 25.0
    assert score_structured_data(SimpleNamespace(structured_data_json=None)) == 0.0
