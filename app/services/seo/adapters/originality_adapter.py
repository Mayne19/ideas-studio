from __future__ import annotations

import re
from collections import Counter


class OriginalityAdapter:
    provider_name = "originality"
    enabled = True
    configured = True
    requires_api_key = False
    last_error: str | None = None
    real_data_available = False
    fallback_mode = "heuristic_only"
    trust_level = "low"

    def compare_ngrams(self, text: str, sources: list[str]) -> dict:
        if not text:
            return {"score": 100, "suspicious": []}
        text_ngrams = self._ngrams(text, 4)
        suspicious = []
        total = len(text_ngrams)
        matches = 0

        for src in sources:
            src_ngrams = self._ngrams(src, 4)
            overlap = text_ngrams & src_ngrams
            if overlap:
                for ng in overlap:
                    suspicious.append({"ngram": ng, "source_snippet": src[:100]})
                matches += len(overlap)

        overlap_ratio = matches / max(total, 1)
        score = max(0, min(100, round(100 - overlap_ratio * 100)))

        return {
            "score": score,
            "total_ngrams": total,
            "matching_ngrams": matches,
            "overlap_ratio": round(overlap_ratio, 4),
            "suspicious": suspicious[:20],
            "method": "heuristic_ngrams",
            "real_data_available": False,
            "note": "Contrôle originalité heuristique contre sources collectées, pas contrôle web complet.",
        }

    def _ngrams(self, text: str, n: int = 4) -> set[str]:
        words = re.findall(r"\b\w+\b", text.lower())
        return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}

    def detect_similar_starts(self, text: str, sources: list[str]) -> list[dict]:
        text_sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        issues = []
        for s in text_sentences:
            start = " ".join(s.split()[:5]).lower()
            for src in sources:
                if start and start in src.lower() and len(start) > 15:
                    issues.append({"sentence_start": start, "source_snippet": src[:100]})
                    break
        return issues

    def get_status(self) -> dict:
        return {
            "provider_name": self.provider_name,
            "enabled": self.enabled,
            "configured": self.configured,
            "requires_api_key": self.requires_api_key,
            "last_error": self.last_error,
            "real_data_available": self.real_data_available,
            "fallback_mode": self.fallback_mode,
            "trust_level": self.trust_level,
        }


originality_adapter = OriginalityAdapter()
