"""Comparaison contrôlée entre le laboratoire et l'ancien pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class BenchmarkRun:
    topic: str
    system: Literal["lab", "pipeline"]
    human_score: float | None
    blocking_errors: int
    warnings: int
    cost_usd: float
    duration_s: float


@dataclass(frozen=True)
class BenchmarkDecision:
    status: Literal["PENDING", "GO", "NO-GO"]
    topics_tested: int
    articles_tested: int
    reason: str
    average_lab_score: float | None = None
    average_pipeline_score: float | None = None


@dataclass
class BenchmarkLedger:
    runs: list[BenchmarkRun] = field(default_factory=list)

    def add(self, run: BenchmarkRun) -> None:
        self.runs.append(run)

    def decide(self, *, minimum_topics: int = 5, minimum_articles: int = 10) -> BenchmarkDecision:
        lab = [run for run in self.runs if run.system == "lab"]
        pipeline = [run for run in self.runs if run.system == "pipeline"]
        topics = {run.topic for run in lab}
        if len(topics) < minimum_topics or len(lab) < minimum_articles:
            return BenchmarkDecision(
                status="PENDING",
                topics_tested=len(topics),
                articles_tested=len(lab),
                reason=f"Il faut {minimum_topics} sujets et {minimum_articles} articles du laboratoire.",
            )
        if any(run.blocking_errors for run in lab):
            return BenchmarkDecision(
                status="NO-GO",
                topics_tested=len(topics),
                articles_tested=len(lab),
                reason="Au moins un article du laboratoire conserve une erreur bloquante.",
            )
        lab_scores = [run.human_score for run in lab if run.human_score is not None]
        pipeline_scores = [run.human_score for run in pipeline if run.human_score is not None]
        average_lab = sum(lab_scores) / len(lab_scores) if lab_scores else None
        average_pipeline = sum(pipeline_scores) / len(pipeline_scores) if pipeline_scores else None
        if average_lab is None or average_pipeline is None:
            return BenchmarkDecision(
                status="PENDING",
                topics_tested=len(topics),
                articles_tested=len(lab),
                reason="Les deux systèmes doivent être notés par un humain.",
                average_lab_score=average_lab,
                average_pipeline_score=average_pipeline,
            )
        if average_lab <= average_pipeline:
            return BenchmarkDecision(
                status="NO-GO",
                topics_tested=len(topics),
                articles_tested=len(lab),
                reason="Le laboratoire ne dépasse pas l'ancien pipeline.",
                average_lab_score=average_lab,
                average_pipeline_score=average_pipeline,
            )
        return BenchmarkDecision(
            status="GO",
            topics_tested=len(topics),
            articles_tested=len(lab),
            reason="Le laboratoire dépasse l'ancien pipeline sans erreur bloquante.",
            average_lab_score=average_lab,
            average_pipeline_score=average_pipeline,
        )
