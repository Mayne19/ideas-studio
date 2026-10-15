"""Relecture par section : tests hors ligne avec un faux provider."""
from app.services.seo.html_text_ops import split_units
from app.services.seo.section_proofreader import proofread_article, rejection_reason

INTRO = (
    "<p>WordFréquemment reste le choix le plus courant pour un blog qui grossit, "
    "alors que Webflow convient mieux aux sites vitrines soignés et peu modifiés.</p>\n"
)
SECTION_PRICES = (
    "<h2>Les prix réels</h2>\n"
    "<p>Un site vitrine réalisé par un freelance coûte entre 1 500 et 3 000 € selon le nombre "
    "de pages, les intégrations demandées et le temps de prise en main prévu.</p>\n"
    "<h3>Hébergement</h3>\n"
    "<p>L'hébergement WordPress se paie a part, comptez quelques euros par mois pour un site "
    "modeste et davantage pour une boutique en ligne avec du trafic.</p>\n"
)
SECTION_SEO = (
    "<h2>Le SEO</h2>\n"
    "<p>Les deux outils permettent de régler les balises title et meta description, "
    "<a href=\"https://fr.wikipedia.org/wiki/WordPress\">WordPress</a> demande souvent une extension "
    "dédiée pour y parvenir proprement.</p>\n"
)
ARTICLE = INTRO + SECTION_PRICES + SECTION_SEO


class FakeProofreader:
    """Corrige le jeton corrompu de l'introduction ; renvoie une sortie
    défectueuse (titre modifié, texte amputé) pour certaines sections."""

    def __init__(self, mode: dict[str, str] | None = None):
        self.mode = mode or {}
        self.steps: list[str] = []

    def __call__(self, prompt: str, step: str, temperature: float) -> str:
        self.steps.append(step)
        unit = prompt.split("Extrait :\n", 1)[1]
        if "<h2>Les prix réels</h2>" in unit:
            behaviour = self.mode.get("prices", "fix")
            if behaviour == "rename_heading":
                return unit.replace("<h2>Les prix réels</h2>", "<h2>Combien ça coûte</h2>")
            if behaviour == "drop_h3":
                return unit.replace("<h3>Hébergement</h3>\n", "")
            if behaviour == "truncate":
                return unit.split("<h3>")[0]
            if behaviour == "change_number":
                return unit.replace("3 000", "2 000")
            return unit.replace("se paie a part", "se paie à part")
        if "<h2>Le SEO</h2>" in unit:
            if self.mode.get("seo") == "error":
                raise RuntimeError("timeout")
            return unit
        return unit.replace("WordFréquemment", "WordPress")


def test_split_units_is_lossless():
    units = split_units(ARTICLE)
    assert len(units) == 3
    assert "".join(units) == ARTICLE


def test_proofreading_fixes_garbled_tokens_and_keeps_structure():
    fake = FakeProofreader()
    content, report = proofread_article(ARTICLE, fake)
    assert "WordFréquemment" not in content
    assert content.startswith("<p>WordPress reste le choix")
    assert "se paie à part" in content
    assert "<h2>Les prix réels</h2>" in content and "<h3>Hébergement</h3>" in content
    assert 'href="https://fr.wikipedia.org/wiki/WordPress"' in content
    assert report["corrected"] == 2
    assert report["rejected"] == 0
    assert len(fake.steps) == 3  # une passe par unité


def test_rejects_output_that_renames_a_heading():
    content, report = proofread_article(ARTICLE, FakeProofreader({"prices": "rename_heading"}))
    assert "<h2>Les prix réels</h2>" in content
    assert "Combien ça coûte" not in content
    assert report["rejected"] == 1
    assert "WordPress reste" in content  # les autres unités restent corrigées


def test_rejects_output_that_drops_an_h3():
    content, report = proofread_article(ARTICLE, FakeProofreader({"prices": "drop_h3"}))
    assert "<h3>Hébergement</h3>" in content
    assert report["rejected"] == 1


def test_rejects_output_that_loses_more_than_ten_percent_of_words():
    original_unit = split_units(ARTICLE)[1]
    truncated = original_unit.split("<h3>")[0]
    assert rejection_reason(original_unit, truncated) is not None
    content, report = proofread_article(ARTICLE, FakeProofreader({"prices": "truncate"}))
    assert SECTION_PRICES.strip() in content
    assert any(u["status"] == "rejected" for u in report["units"])


def test_rejects_output_that_changes_a_figure():
    content, report = proofread_article(ARTICLE, FakeProofreader({"prices": "change_number"}))
    assert "1 500 et 3 000 €" in content
    assert report["rejected"] == 1


def test_provider_error_keeps_unit_unchanged():
    content, report = proofread_article(ARTICLE, FakeProofreader({"seo": "error"}))
    assert SECTION_SEO.strip() in content
    assert report["errors"] == 1
