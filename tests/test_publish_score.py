"""Score minimum de publication : seul le score global bloque (tests hors ligne)."""
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.pipeline import PipelineSettingsUpdate
from app.services.pipeline_service import resolve_min_publish_score
from app.services.validation_service import publish_score_block_reason


def test_settings_update_rejects_out_of_range_min_score():
    with pytest.raises(ValidationError):
        PipelineSettingsUpdate(min_publish_score=80)
    with pytest.raises(ValidationError):
        PipelineSettingsUpdate(min_publish_score=101)
    assert PipelineSettingsUpdate(min_publish_score=85).min_publish_score == 85


def test_min_publish_score_default_and_clamp():
    assert resolve_min_publish_score(None) == 90
    assert resolve_min_publish_score(SimpleNamespace(min_publish_score=70)) == 85


def test_publish_blocked_only_below_min_global_score():
    assert publish_score_block_reason({"global_score_valid": True, "global_score": 92}, 90) is None
    reason = publish_score_block_reason({"global_score_valid": True, "global_score": 89}, 90)
    assert reason and "89" in reason and "90" in reason
    assert publish_score_block_reason({"global_score_valid": False, "incomplete_reason": "Aucun score"}, 90) == "Aucun score"
