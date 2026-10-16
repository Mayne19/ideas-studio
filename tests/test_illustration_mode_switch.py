"""Bascule du mode des images (IA / Unsplash / aucune) dans l'orchestrateur,
et repli Unsplash du mode IA — hors ligne, sans base ni réseau."""
from types import SimpleNamespace

import pytest

from app.services import illustration_settings_service as settings_svc
from app.services.illustration_settings_service import IllustrationConfig
from app.services.seo import illustration_service
from app.services.seo import seo_generation_orchestrator as orch_module
from app.services.seo.seo_generation_orchestrator import SEOGenerationOrchestrator


def _orchestrator(unsplash_configured=False):
    orch = SEOGenerationOrchestrator.__new__(SEOGenerationOrchestrator)
    orch.db = None
    orch.project_id = "proj-1"
    orch.project = SimpleNamespace(locale="fr-FR")
    orch.context = {}
    orch.tools_used = []
    orch.tools_not_configured = []
    orch.limitations = []
    orch.errors = []
    orch.image_sourcing_adapter = SimpleNamespace(configured=unsplash_configured)
    orch._log = lambda *a, **kw: None
    orch._save = lambda *a, **kw: None
    orch._error = lambda step, message: orch.errors.append(f"[{step}] {message}")
    return orch


@pytest.fixture
def unsplash_plan(monkeypatch):
    calls = []

    def fake_plan(keyword, outline, db=None, project_id=None):
        calls.append(keyword)
        return {
            "image_plan": {"provider_configured": True, "images": []},
            "image_sources": [{"image_url": "https://images.unsplash.com/x", "source_name": "Unsplash"}],
        }

    monkeypatch.setattr(orch_module, "build_image_plan_dict", fake_plan)
    return calls


def _mode(monkeypatch, mode):
    monkeypatch.setattr(settings_svc, "resolve_config", lambda db, project_id: IllustrationConfig(mode=mode))


def test_unsplash_mode_keeps_legacy_plan(monkeypatch, unsplash_plan):
    _mode(monkeypatch, "unsplash")
    orch = _orchestrator()
    result = orch._plan_images("vélo", {"sections": []})
    assert unsplash_plan == ["vélo"]
    assert result["image_plan"]["mode"] == "unsplash"
    assert orch.context["image_sources"][0]["source_name"] == "Unsplash"
    assert "unsplash" in orch.tools_used


def test_ai_mode_defers_generation_and_skips_unsplash(monkeypatch, unsplash_plan):
    _mode(monkeypatch, "ai")
    orch = _orchestrator()
    result = orch._plan_images("vélo", {"sections": []})
    assert unsplash_plan == []
    assert result["image_plan"]["mode"] == "ai"
    assert orch.context["image_sources"] == []
    assert orch.context["illustration_config"].mode == "ai"
    assert "image_generation" in orch.tools_used


def test_none_mode_plans_nothing(monkeypatch, unsplash_plan):
    _mode(monkeypatch, "none")
    orch = _orchestrator()
    result = orch._plan_images("vélo", {"sections": []})
    assert unsplash_plan == []
    assert result["image_sources"] == []
    assert orch.tools_used == [] and orch.limitations == []


def _draft():
    return SimpleNamespace(title="Bien choisir son vélo", keyword="vélo")


def test_ai_generation_returns_generated_sources(monkeypatch, unsplash_plan):
    generated = [{"image_url": "https://cdn/x.webp", "role": "inline", "usage_rights_status": "generated"}]
    monkeypatch.setattr(illustration_service, "generate_illustrations", lambda *a, **kw: (generated, []))
    orch = _orchestrator(unsplash_configured=True)
    out = orch._generate_illustrations(SimpleNamespace(id="a"), _draft(), {}, "<h2>x</h2>", IllustrationConfig(mode="ai"))
    assert out == generated
    assert unsplash_plan == []


def test_ai_generation_falls_back_to_unsplash_when_configured(monkeypatch, unsplash_plan):
    monkeypatch.setattr(illustration_service, "generate_illustrations", lambda *a, **kw: ([], ["no key"]))
    orch = _orchestrator(unsplash_configured=True)
    out = orch._generate_illustrations(SimpleNamespace(id="a"), _draft(), {}, "<h2>x</h2>", IllustrationConfig(mode="ai"))
    assert out and out[0]["source_name"] == "Unsplash"
    assert orch.context["image_plan"]["mode"] == "unsplash_fallback"
    assert any("no key" in e for e in orch.errors)


def test_ai_generation_without_unsplash_yields_no_image(monkeypatch, unsplash_plan):
    def boom(*a, **kw):
        raise RuntimeError("provider down")

    monkeypatch.setattr(illustration_service, "generate_illustrations", boom)
    orch = _orchestrator(unsplash_configured=False)
    out = orch._generate_illustrations(SimpleNamespace(id="a"), _draft(), {}, "<h2>x</h2>", IllustrationConfig(mode="ai"))
    assert out == []
    assert unsplash_plan == []
    assert any("provider down" in e for e in orch.errors)
