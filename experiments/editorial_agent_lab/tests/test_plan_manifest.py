from __future__ import annotations

import json
from pathlib import Path


def test_plan_manifest_is_complete_and_only_claims_validated_evidence() -> None:
    path = Path(__file__).parents[1] / "implementation_plan.json"
    plan = json.loads(path.read_text(encoding="utf-8"))
    steps = plan["steps"]
    assert [step["id"] for step in steps] == [f"A{i}" for i in range(19)]
    assert plan["integration_allowed_before_acceptance"] is False
    for step in steps:
        if step["status"] == "validated":
            assert step["evidence"]
        else:
            assert step["status"] == "planned"
