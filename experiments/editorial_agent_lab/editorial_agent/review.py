"""Validation humaine et évolution des règles, séparées du brouillon."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from .models import GenerationResult, ValidationIssue

ReviewDecision = Literal["approved", "rejected", "changes_requested"]


@dataclass(frozen=True)
class HumanReview:
    version: int
    decision: ReviewDecision
    reviewer: str
    notes: str
    created_at: str


@dataclass(frozen=True)
class RuleProposal:
    rule_id: str
    text: str
    origin: str
    status: Literal["pending", "accepted", "rejected"] = "pending"


@dataclass
class ReviewLedger:
    reviews: list[HumanReview] = field(default_factory=list)
    rule_proposals: list[RuleProposal] = field(default_factory=list)

    def record(
        self,
        result: GenerationResult,
        *,
        decision: ReviewDecision,
        reviewer: str,
        notes: str,
        version: int = 1,
    ) -> HumanReview:
        if decision == "approved" and result.report.blocking_issues:
            raise ValueError("un article avec des erreurs bloquantes ne peut pas être approuvé")
        review = HumanReview(
            version=version,
            decision=decision,
            reviewer=reviewer,
            notes=notes.strip(),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.reviews.append(review)
        return review

    def propose_rule(self, *, rule_id: str, text: str, origin: str) -> RuleProposal:
        if any(rule.rule_id == rule_id for rule in self.rule_proposals):
            raise ValueError(f"la règle existe déjà : {rule_id}")
        proposal = RuleProposal(rule_id=rule_id, text=text.strip(), origin=origin.strip())
        self.rule_proposals.append(proposal)
        return proposal


def review_issues(result: GenerationResult) -> list[ValidationIssue]:
    """Expose les erreurs à l'humain sans modifier l'article."""

    return list(result.report.blocking_issues) + list(result.report.warnings)
