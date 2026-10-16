"""Illustrations IA : construction des prompts et génération de bout en bout
avec un faux planificateur LLM et un faux provider d'image (hors ligne)."""
import re
from types import SimpleNamespace

import pytest

from app.services.illustration_settings_service import (
    IllustrationConfig,
    IllustrationSettingsError,
    compose_image_prompt,
    normalize_config,
)
from app.services.providers.image_generation_provider import GeneratedImage
from app.services.seo import illustration_service as svc
from app.services.seo.image_plan_service import insert_images_in_content, pick_cover_source

ARTICLE = (
    "<h1>Bien choisir son vélo</h1>\n"
    "<p>Le choix d'un vélo dépend d'abord de l'usage quotidien.</p>\n"
    "<h2>Le vélo de ville</h2>\n"
    "<p>Le vélo de ville privilégie le confort et la posture droite.</p>\n"
    "<h2>Le vélo de route</h2>\n"
    "<p>Le vélo de route vise la vitesse sur longue distance.</p>\n"
    "<h2>FAQ</h2>\n"
    "<p>Questions fréquentes.</p>\n"
)


def test_compose_image_prompt_adds_style_palette_and_no_text_rule():
    cfg = IllustrationConfig(mode="ai", style_preset="line_sketch", primary_color="#112233", secondary_color="#AABBCC")
    prompt = compose_image_prompt("A commuter riding an upright city bike.", cfg)
    assert prompt.startswith("A commuter riding an upright city bike.")
    assert "ink line sketch" in prompt
    assert "#112233" in prompt and "#AABBCC" in prompt
    assert "no text" in prompt and "no logos" in prompt and "no letters" in prompt


def test_custom_style_requires_description_and_is_used():
    with pytest.raises(IllustrationSettingsError):
        normalize_config({"style_preset": "custom"})
    cfg = IllustrationConfig(mode="ai", **normalize_config({"style_preset": "custom", "custom_style": "risograph print"}))
    assert "risograph print" in compose_image_prompt("scene", cfg)


def test_normalize_config_validates_colors_model_and_caps_images():
    with pytest.raises(IllustrationSettingsError):
        normalize_config({"primary_color": "blue"})
    with pytest.raises(IllustrationSettingsError):
        normalize_config({"model": "openai/unknown"})
    assert normalize_config({"max_images": 99})["max_images"] == 6
    assert normalize_config({"primary_color": "#abcdef"})["primary_color"] == "#ABCDEF"


def test_planner_prompt_uses_written_section_text_and_slots():
    sections = svc.extract_sections(ARTICLE)
    assert [s["heading"] for s in sections] == ["Le vélo de ville", "Le vélo de route", "FAQ"]
    prompt = svc.build_planner_prompt(
        "Bien choisir son vélo", "choisir vélo", "fr", svc.intro_text(ARTICLE), sections, 2, True,
        IllustrationConfig(mode="ai"),
    )
    assert "posture droite" in prompt  # texte réel de la section, pas seulement le titre
    assert "AU PLUS 2 section" in prompt
    assert "Illustration éditoriale plate" in prompt
    assert "langue 'fr'" in prompt


def test_parse_plan_filters_bad_indexes_duplicates_and_caps():
    sections = svc.extract_sections(ARTICLE)
    raw = {
        "cover": {"scene": "Two bikes side by side", "alt": "Deux vélos côte à côte"},
        "sections": [
            {"index": 1, "scene": "city bike", "alt": "Vélo de ville"},
            {"index": 1, "scene": "dup", "alt": "x"},
            {"index": 9, "scene": "out of range", "alt": "x"},
            {"index": 2, "scene": "road bike", "alt": "Vélo de route"},
            {"index": 3, "scene": "faq", "alt": "x"},
        ],
    }
    plan = svc.parse_plan(raw, sections, section_slots=2, include_cover=True)
    assert plan["cover"]["alt"] == "Deux vélos côte à côte"
    assert [s["heading"] for s in plan["sections"]] == ["Le vélo de ville", "Le vélo de route"]
    assert svc.parse_plan(raw, sections, 2, include_cover=False)["cover"] is None


class FakePlanner:
    is_mock = False
    provider_name = "fake"
    model_name = "fake-planner"
    last_usage = None

    def __init__(self, response):
        self.response = response
        self.prompts = []

    def generate_json(self, prompt, schema_hint=None):
        self.prompts.append(prompt)
        return self.response


class FakeImageProvider:
    model = "google/gemini-3.1-flash-lite-image"

    def __init__(self, fail_on=None):
        self.prompts = []
        self.fail_on = fail_on

    def generate(self, prompt, aspect_ratio="16:9"):
        self.prompts.append(prompt)
        if self.fail_on and self.fail_on in prompt:
            raise RuntimeError("boom")
        return GeneratedImage(data=b"img", mime_type="image/png", model=self.model, cost_usd=0.002)


def _fake_store():
    calls = []

    def store(data, project_id, mime_type, basename):
        calls.append((data, project_id, mime_type))
        return {"url": f"https://cdn.example/{project_id}/{len(calls)}.webp", "filename": f"{len(calls)}.webp",
                "mime_type": "image/webp", "byte_size": 3}

    return store, calls


def test_generate_illustrations_end_to_end_with_fakes():
    planner = FakePlanner({
        "cover": {"scene": "Two bikes", "alt": "Deux vélos"},
        "sections": [{"index": 2, "scene": "A road cyclist on a mountain pass", "alt": "Cycliste sur route de col"}],
    })
    images = FakeImageProvider()
    store, stored = _fake_store()
    article = SimpleNamespace(id="art-1", project_id="proj-1")

    sources, errors = svc.generate_illustrations(
        None, article, ARTICLE, "Bien choisir son vélo", "vélo", "fr",
        IllustrationConfig(mode="ai", max_images=3),
        image_provider=images, planner=planner, store=store, has_cover=False,
    )

    assert errors == []
    assert [s["role"] for s in sources] == ["cover", "inline"]
    assert len(stored) == 2 and all(c[1] == "proj-1" for c in stored)
    assert all("no text" in p for p in images.prompts)
    inline = sources[1]
    assert inline["section_heading"] == "Le vélo de route"
    assert inline["alt_localized"] == "Cycliste sur route de col"

    html = insert_images_in_content(ARTICLE, sources)
    figures = re.findall(r"<figure>.*?</figure>", html, re.DOTALL)
    # Seule l'image de section est insérée ; la couverture reste en tête.
    assert len(figures) == 1
    assert "<figcaption>" not in figures[0]
    assert 'alt="Cycliste sur route de col"' in figures[0]
    assert html.split("<h2>Le vélo de route</h2>")[1].startswith("\n<p>Le vélo de route vise la vitesse sur longue distance.</p><figure>")
    assert pick_cover_source(sources)["role"] == "cover"


def test_existing_cover_means_all_slots_for_sections_and_failures_are_absorbed():
    planner = FakePlanner({
        "cover": {"scene": "ignored", "alt": "x"},
        "sections": [
            {"index": 1, "scene": "city scene", "alt": "Ville"},
            {"index": 2, "scene": "road scene", "alt": "Route"},
        ],
    })
    images = FakeImageProvider(fail_on="road scene")
    store, _ = _fake_store()
    sources, errors = svc.generate_illustrations(
        None, SimpleNamespace(id="a", project_id="p"), ARTICLE, "T", "k", "fr",
        IllustrationConfig(mode="ai", max_images=2),
        image_provider=images, planner=planner, store=store, has_cover=True,
    )
    assert "AU PLUS 2 section" in planner.prompts[0]
    assert [s["section_heading"] for s in sources] == ["Le vélo de ville"]
    assert len(errors) == 1


def test_zero_max_images_generates_nothing():
    planner = FakePlanner({})
    sources, errors = svc.generate_illustrations(
        None, SimpleNamespace(id="a", project_id="p"), ARTICLE, "T", "k", "fr",
        IllustrationConfig(mode="ai", max_images=0),
        image_provider=FakeImageProvider(), planner=planner, store=_fake_store()[0], has_cover=False,
    )
    assert sources == [] and errors == [] and planner.prompts == []
