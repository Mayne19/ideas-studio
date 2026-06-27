"""
LLMBudgetManager — contrôle si un appel LLM est justifié pour l'enrichissement du scoring.

Règles :
- L'appel LLM n'est déclenché que si les règles seules donnent une confiance < "high"
  ET que le score est dans la zone "grise" (40–75) où le LLM apporte de la valeur
- En dehors de cette zone, les règles suffisent (0–39 = clairement insuffisant,
  76–100 = clairement bon)
- Un budget global par analyse limite les appels à N experts maximum
"""
from __future__ import annotations

from dataclasses import dataclass, field


GREY_ZONE_LOW = 40
GREY_ZONE_HIGH = 75
DEFAULT_MAX_LLM_CALLS = 2


@dataclass
class LLMBudgetManager:
    max_calls: int = DEFAULT_MAX_LLM_CALLS
    calls_used: int = 0
    _calls_log: list[str] = field(default_factory=list)

    def should_call_llm(self, expert: str, rules_score: float, confidence: str) -> bool:
        """Return True if an LLM call is warranted for this expert."""
        if self.calls_used >= self.max_calls:
            return False
        if confidence == "high" and (rules_score < GREY_ZONE_LOW or rules_score > GREY_ZONE_HIGH):
            return False
        if GREY_ZONE_LOW <= rules_score <= GREY_ZONE_HIGH:
            return True
        if confidence in ("low", "medium"):
            return True
        return False

    def consume(self, expert: str) -> None:
        self.calls_used += 1
        self._calls_log.append(expert)

    def remaining(self) -> int:
        return max(0, self.max_calls - self.calls_used)

    def summary(self) -> dict:
        return {
            "max_calls": self.max_calls,
            "calls_used": self.calls_used,
            "calls_log": self._calls_log,
            "remaining": self.remaining(),
        }
