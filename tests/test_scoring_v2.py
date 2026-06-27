"""Tests unitaires pour le scoring v2.1."""
import pytest

from app.services.seo.format_expectations import normalize_to_format, get_format, get_expectations, infer_format
from app.services.seo.readability_service import compute_lix, lix_to_score, compute_readability_score
from app.services.seo.originality_service import (
    score_ai_generic_absence,
    compute_originality_score,
)
from app.services.seo.eeat_service import compute_eeat_score, score_nuance_markers
from app.services.seo.geo_expert_service import compute_geo_score, score_direct_answers
from app.services.scoring_service import compute_global_score


# ── normalize_to_format ──────────────────────────────────────────────────────

def test_normalize_at_ideal():
    assert normalize_to_format(5, 3, 5) == 100.0

def test_normalize_above_ideal():
    assert normalize_to_format(8, 3, 5) == 100.0

def test_normalize_at_minimum():
    assert normalize_to_format(3, 3, 5) == 50.0

def test_normalize_between_min_and_ideal():
    result = normalize_to_format(4, 3, 5)
    assert result == 75.0

def test_normalize_below_minimum():
    result = normalize_to_format(1, 3, 5)
    assert 0 <= result < 50

def test_normalize_zero():
    assert normalize_to_format(0, 3, 5) == 0.0

def test_normalize_ideal_zero():
    assert normalize_to_format(0, 0, 0) == 100.0


# ── infer_format ─────────────────────────────────────────────────────────────

def test_infer_format_short():
    assert infer_format(500) == "short"

def test_infer_format_medium():
    assert infer_format(1000) == "medium"

def test_infer_format_long():
    assert infer_format(2000) == "long"

def test_infer_format_pillar():
    assert infer_format(3000) == "pillar"

def test_infer_format_none():
    assert infer_format(None) == "medium"


# ── get_format ────────────────────────────────────────────────────────────────

def test_get_format_explicit():
    assert get_format({"content_format": "pillar"}) == "pillar"

def test_get_format_inferred():
    assert get_format({"target_word_count": 500}) == "short"

def test_get_format_default():
    assert get_format({}) == "medium"


# ── LIX readability ───────────────────────────────────────────────────────────

SIMPLE_TEXT = "Le SEO aide les sites. Il est utile. Les moteurs indexent les pages web."
COMPLEX_TEXT = (
    "L'optimisation des moteurs de recherche constitue une discipline fondamentale "
    "dans l'écosystème numérique contemporain. Les algorithmes d'indexation, "
    "particulièrement sophistiqués, analysent systématiquement les paramètres "
    "structurels des contenus éditoriaux."
)

def test_lix_simple_text():
    lix = compute_lix(SIMPLE_TEXT)
    assert lix < 40, f"LIX devrait être bas pour du texte simple, obtenu {lix}"

def test_lix_complex_text():
    lix = compute_lix(COMPLEX_TEXT)
    assert lix > 45, f"LIX devrait être élevé pour du texte complexe, obtenu {lix}"

def test_lix_to_score_easy():
    assert lix_to_score(20) == 95

def test_lix_to_score_medium():
    assert lix_to_score(45) == 60

def test_lix_to_score_hard():
    assert lix_to_score(65) == 20

def test_readability_no_content():
    result = compute_readability_score({"content": ""})
    assert result["confidence"] == "low"
    assert "no_content" in result["flags"]

def test_readability_returns_score():
    html = f"<p>{SIMPLE_TEXT * 3}</p><p>{SIMPLE_TEXT * 3}</p>"
    result = compute_readability_score({"content": html})
    assert result["score"] is not None
    assert 0 <= result["score"] <= 100
    assert result["version"] == "2.1"


# ── Originality ───────────────────────────────────────────────────────────────

def test_originality_no_sources_is_unverified():
    article = {"content": "<p>Contenu de qualité sans sources.</p>" * 10, "content_format": "short"}
    result = compute_originality_score(article, [])
    assert result["status"] == "unverified"
    assert result["score"] <= 65  # plafonné

def test_originality_generic_ai_patterns_penalized():
    article = {
        "content": "<p>Dans cet article, nous allons voir comment fonctionne le SEO. "
                   "Il est important de noter que le référencement est essentiel. "
                   "En conclusion, nous pouvons dire que c'est utile.</p>" * 3,
        "content_format": "short",
    }
    score_with_patterns = score_ai_generic_absence(article["content"])
    assert score_with_patterns < 60, "Les patterns IA génériques doivent pénaliser le score"

def test_originality_no_patterns_high_score():
    clean = "Le référencement naturel repose sur trois piliers : technique, contenu, autorité."
    score = score_ai_generic_absence(clean)
    assert score == 100.0

def test_originality_empty_content():
    result = compute_originality_score({"content": ""}, [])
    assert result["confidence"] == "low"
    assert result["status"] == "unverified"


# ── EEAT ──────────────────────────────────────────────────────────────────────

EEAT_CONTENT = """
<h2>Comment optimiser votre stratégie SEO ?</h2>
<p>Le SEO permet d'améliorer la visibilité. Cependant, il faut distinguer le SEO technique
du SEO de contenu. Selon une étude HubSpot 2024, 70% des clics vont aux 3 premiers résultats.</p>
<h3>Le référencement technique</h3>
<p>En outre, la vitesse de chargement est cruciale. Toutefois, le contenu reste prioritaire.</p>
<h2>Les outils indispensables</h2>
<p>Néanmoins, certains outils gratuits suffisent pour démarrer. Par exemple, Google Search Console
permet de suivre vos positions selon les données officielles de Google.</p>
<a href="https://searchenginejournal.com">Source 1</a>
<a href="https://moz.com">Source 2</a>
"""

def test_eeat_no_content():
    result = compute_eeat_score({"content": ""})
    assert result["confidence"] == "low"
    assert result["score"] == 0

def test_eeat_with_content_returns_score():
    result = compute_eeat_score({"content": EEAT_CONTENT, "content_format": "medium"})
    assert 0 <= result["score"] <= 100
    assert result["confidence"] in {"low", "medium", "high"}
    assert result["version"] == "2.1"
    assert "external_links" in result["signals"]

def test_eeat_no_author_bio_flagged():
    result = compute_eeat_score({"content": EEAT_CONTENT, "content_format": "medium"})
    assert "no_author_bio" in result["flags"]

def test_nuance_markers_density():
    text = "cependant toutefois néanmoins en revanche cependant"
    score = score_nuance_markers(text, word_count=50)
    assert score > 60

def test_eeat_format_short_vs_pillar():
    """Un même article devrait scorer plus haut en 'short' qu'en 'pillar' (exigences moindres)."""
    article_short = {"content": EEAT_CONTENT, "content_format": "short"}
    article_pillar = {"content": EEAT_CONTENT, "content_format": "pillar"}
    score_short = compute_eeat_score(article_short)["score"]
    score_pillar = compute_eeat_score(article_pillar)["score"]
    assert score_short >= score_pillar, "Les exigences pilier sont plus élevées"


# ── GEO ──────────────────────────────────────────────────────────────────────

GEO_CONTENT = """
<h2>Comment fonctionne le référencement naturel ?</h2>
<p>Le référencement naturel, ou SEO, permet d'améliorer la position d'un site web dans
les résultats organiques de Google et Bing. Les algorithmes analysent plusieurs signaux.</p>
<h2>Pourquoi investir dans le SEO en 2026 ?</h2>
<p>Selon Search Engine Journal, 93% des expériences en ligne débutent par un moteur de recherche.
À retenir : le SEO génère un trafic qualifié et durable.</p>
"""

def test_geo_no_content():
    result = compute_geo_score({"content": ""})
    assert result["confidence"] == "low"
    assert "no_content" in result["flags"]

def test_geo_with_content():
    result = compute_geo_score({"content": GEO_CONTENT, "content_format": "short", "keyword": "SEO"})
    assert 0 <= result["score"] <= 100
    assert result["version"] == "2.1"
    assert "direct_answers" in result["signals"]

def test_geo_summary_marker_detected():
    content = "<h2>Comment faire ?</h2><p>À retenir : voici les étapes essentielles pour réussir.</p>"
    result = compute_geo_score({"content": content, "content_format": "short"})
    assert result["signals"].get("summary_blocks", {}).get("value", 0) >= 60

def test_geo_no_structured_data_flagged():
    result = compute_geo_score({"content": GEO_CONTENT, "content_format": "short"})
    assert "no_structured_data" in result["flags"]


# ── Global score ──────────────────────────────────────────────────────────────

def test_global_score_unverified_blocks():
    article = {
        "seo_score": 80,
        "eeat_checklist_json": {"v2": {"score": 70}},
        "readability_report_json": {"score": 75},
        "originality_report_json": {"v2": {"score": 40, "status": "unverified"}},
    }
    result = compute_global_score(article)
    assert result["global_score_valid"] is False
    assert "non vérifiée" in (result["incomplete_reason"] or "")

def test_global_score_computes_correctly():
    article = {
        "seo_score": 80,
        "eeat_checklist_json": {"v2": {"score": 60}},
        "readability_report_json": {"score": 70},
        "originality_report_json": {"v2": {"score": 75, "status": "original"}},
    }
    result = compute_global_score(article)
    assert result["global_score_valid"] is True
    # 80*0.35 + 60*0.25 + 70*0.20 + 75*0.20 = 28+15+14+15 = 72
    assert result["global_score"] == pytest.approx(72.0, abs=1)

def test_global_score_partial_available():
    article = {
        "seo_score": 80,
        "eeat_checklist_json": {"v2": {"score": 70}},
        "originality_report_json": None,
    }
    result = compute_global_score(article)
    assert result["global_score_valid"] is False

def test_global_score_v21_note():
    article = {
        "seo_score": 90,
        "eeat_checklist_json": {"v2": {"score": 80}},
        "readability_report_json": {"score": 85},
        "originality_report_json": {"v2": {"score": 90, "status": "adds_value"}},
    }
    result = compute_global_score(article)
    assert "2.1" in result["scoring_note"]
    assert "Volume non noté" in result["scoring_note"]
