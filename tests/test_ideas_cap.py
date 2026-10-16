"""Plafond d'idées par lancement : tests hors ligne (faux objet Session,
aucune base)."""
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.pipeline import PipelineSettingsUpdate
from app.services.pipeline_service import (
    allocate_ideas_per_category,
    cap_ideas_count,
    resolve_ideas_per_run,
)


class FakeDb:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def get(self, _model, _pk):
        return self.pipeline


def test_allocation_never_exceeds_cap_and_spreads_by_priority():
    allocation = allocate_ideas_per_category([("a", 4), ("b", 1), ("c", 3)], 2)
    assert allocation == {"a": 1, "b": 1}
    assert sum(allocate_ideas_per_category([("a", 4), ("b", 1), ("c", 3)], 3).values()) == 3


def test_allocation_respects_category_volume():
    assert allocate_ideas_per_category([("a", 1)], 3) == {"a": 1}
    assert allocate_ideas_per_category([("a", 0), ("b", 2)], 3) == {"b": 2}
    assert allocate_ideas_per_category([], 3) == {}


def test_default_cap_is_two_without_pipeline():
    assert resolve_ideas_per_run(FakeDb(None), "p") == 2


def test_cap_is_clamped_between_one_and_three():
    assert resolve_ideas_per_run(FakeDb(SimpleNamespace(ideas_per_run=9)), "p") == 3
    assert resolve_ideas_per_run(FakeDb(SimpleNamespace(ideas_per_run=0)), "p") == 1


def test_requested_counts_are_capped():
    db = FakeDb(SimpleNamespace(ideas_per_run=2))
    assert cap_ideas_count(db, "p", None) == 2
    assert cap_ideas_count(db, "p", 5) == 2
    assert cap_ideas_count(db, "p", 1) == 1


def test_settings_update_rejects_out_of_range_values():
    with pytest.raises(ValidationError):
        PipelineSettingsUpdate(ideas_per_run=4)
    with pytest.raises(ValidationError):
        PipelineSettingsUpdate(ideas_per_run=0)
    assert PipelineSettingsUpdate(ideas_per_run=1).ideas_per_run == 1
