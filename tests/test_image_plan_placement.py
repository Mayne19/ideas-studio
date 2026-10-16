"""Placement et attribution des images : tests hors ligne, sans LLM ni réseau."""
import re

from app.services.seo import image_plan_service as svc
from app.services.seo.image_plan_service import (
    insert_images_in_content,
    localize_image_alts,
    pick_cover_source,
    track_unsplash_downloads,
)

ARTICLE = (
    "<h1>Bien choisir son vélo</h1>\n"
    "<p>Introduction.</p>\n"
    "<h2>Le vélo de ville</h2>\n"
    "<p>Le vélo de ville privilégie le confort.</p>\n"
    "<p>Second paragraphe.</p>\n"
    "<h2>Le vélo de route</h2>\n"
    "<p>Le vélo de route vise la vitesse.</p>\n"
    "<h2>Conclusion</h2>\n"
    "<p>Fin.</p>\n"
)


def _unsplash(heading, url="https://images.unsplash.com/photo-1", **extra):
    source = {
        "image_url": url,
        "source_url": "https://unsplash.com/photos/abc",
        "source_name": "Unsplash",
        "author": "Jane Doe",
        "author_url": "https://unsplash.com/@janedoe",
        "download_location": "https://api.unsplash.com/photos/abc/download?ixid=xyz",
        "alt_text": "a red bicycle leaning on a wall",
        "usage_rights_status": "free_with_attribution",
        "section_heading": heading,
    }
    source.update(extra)
    return source


def test_image_inserted_after_first_paragraph_of_its_section():
    out = insert_images_in_content(ARTICLE, [_unsplash("Le vélo de route")])
    section = out.split("<h2>Le vélo de route</h2>")[1]
    assert section.startswith("\n<p>Le vélo de route vise la vitesse.</p><figure>")
    # Pas d'image collée directement sous le titre.
    assert "</h2><figure>" not in out


def test_section_without_paragraph_falls_back_after_heading():
    content = "<h2>Galerie</h2><ul><li>a</li></ul><h2>Suite</h2><p>x</p>"
    out = insert_images_in_content(content, [_unsplash("Galerie")])
    assert out.startswith("<h2>Galerie</h2><figure>")


def test_unsplash_figcaption_with_utm_links():
    out = insert_images_in_content(ARTICLE, [_unsplash("Le vélo de ville")])
    figure = re.search(r"<figure>.*?</figure>", out, re.DOTALL).group(0)
    assert '<figcaption>Photo : <a href="https://unsplash.com/@janedoe?utm_source=ideas_studio&amp;utm_medium=referral">Jane Doe</a>' in figure
    assert 'sur <a href="https://unsplash.com/?utm_source=ideas_studio&amp;utm_medium=referral">Unsplash</a></figcaption>' in figure


def test_alt_never_uses_raw_english_unsplash_description():
    out = insert_images_in_content(ARTICLE, [_unsplash("Le vélo de ville")])
    assert "a red bicycle" not in out
    assert 'alt="Le vélo de ville"' in out


def test_localized_alt_is_used(monkeypatch):
    captured = {}

    def fake_writer(items, language, keyword, db=None, project_id=None):
        captured["items"] = items
        captured["language"] = language
        return ["Vélo rouge appuyé contre un mur en ville"]

    import app.services.agents.agent_services as agents
    monkeypatch.setattr(agents, "write_image_alt_texts", fake_writer)
    sources = [_unsplash("Le vélo de ville")]
    localize_image_alts(ARTICLE, sources, "fr", "vélo")
    assert captured["language"] == "fr"
    assert captured["items"][0]["section_excerpt"] == "Le vélo de ville privilégie le confort."
    out = insert_images_in_content(ARTICLE, sources)
    assert 'alt="Vélo rouge appuyé contre un mur en ville"' in out


def test_localize_falls_back_to_heading_when_llm_fails(monkeypatch):
    import app.services.agents.agent_services as agents

    def boom(*args, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(agents, "write_image_alt_texts", boom)
    sources = [_unsplash("Le vélo de ville")]
    localize_image_alts(ARTICLE, sources, "fr")
    assert "alt_localized" not in sources[0]
    assert svc.image_alt_text(sources[0]) == "Le vélo de ville"


def test_unmatched_image_goes_to_first_free_section_only():
    sources = [_unsplash("Le vélo de ville"), _unsplash("Section supprimée", url="https://images.unsplash.com/photo-2")]
    out = insert_images_in_content(ARTICLE, sources)
    assert out.count("<figure>") == 2
    route = out.split("<h2>Le vélo de route</h2>")[1].split("<h2>")[0]
    assert "photo-2" in route
    assert all(s.get("inserted") for s in sources)


def test_brand_image_has_no_unsplash_caption():
    brand = {
        "image_url": "https://canva.com/shot.png", "source_name": "canva.com",
        "usage_rights_status": "official_source", "section_heading": "Le vélo de route",
        "alt_text": "Canva homepage",
    }
    out = insert_images_in_content(ARTICLE, [brand])
    assert "<figure><img" in out and "<figcaption>" not in out


def test_track_downloads_only_for_inserted_unsplash_images():
    class FakeAdapter:
        def __init__(self):
            self.calls = []

        def track_download(self, location):
            self.calls.append(location)
            return True

    used = _unsplash("Le vélo de ville", inserted=True)
    unused = _unsplash("Autre", url="https://images.unsplash.com/photo-3")
    adapter = FakeAdapter()
    assert track_unsplash_downloads([used, unused], adapter) == 1
    assert adapter.calls == [used["download_location"]]
    # Une seule fois par photo.
    assert track_unsplash_downloads([used], adapter) == 0


def test_adapter_refuses_non_unsplash_download_location():
    from app.services.seo.adapters.image_sourcing_adapter import ImageSourcingAdapter

    adapter = ImageSourcingAdapter.__new__(ImageSourcingAdapter)
    adapter.configured = True
    adapter.api_key = "k"
    assert adapter.track_download("http://169.254.169.254/latest") is False


def test_cover_prefers_inserted_unsplash_image():
    brand = {"image_url": "https://canva.com/a.png", "source_name": "canva.com", "inserted": True}
    photo = _unsplash("x", inserted=True)
    skipped = _unsplash("y", url="https://images.unsplash.com/photo-9")
    assert pick_cover_source([brand, skipped, photo]) is photo
    assert pick_cover_source([brand]) is brand
    assert pick_cover_source([skipped]) is None
