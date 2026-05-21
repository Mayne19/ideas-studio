from __future__ import annotations

import re


class ReadabilityAdapter:
    provider_name = "readability"
    enabled = True
    configured = True
    requires_api_key = False
    last_error: str | None = None
    real_data_available = True
    fallback_mode = "internal_heuristic"
    trust_level = "medium"

    def score(self, text: str) -> dict:
        if not text:
            return {"score": 0, "average_sentence_length": 0, "sentence_count": 0}
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        words = text.split()
        word_count = len(words)
        sentence_count = len(sentences) or 1
        avg_sentence_length = word_count / sentence_count

        long_sentences = sum(1 for s in sentences if len(s.split()) > 25)
        long_paragraphs = 0
        paragraphs = re.split(r"\n\s*\n", text)
        for p in paragraphs:
            p_words = len(p.split())
            if p_words > 100:
                long_paragraphs += 1

        score = 100
        if avg_sentence_length > 20:
            score -= (avg_sentence_length - 20) * 2
        if long_sentences > sentence_count * 0.3:
            score -= 10
        if long_paragraphs > 0:
            score -= long_paragraphs * 5
        score = max(0, min(100, score))

        return {
            "score": round(score, 1),
            "average_sentence_length": round(avg_sentence_length, 1),
            "sentence_count": sentence_count,
            "word_count": word_count,
            "long_sentences": long_sentences,
            "long_paragraphs": long_paragraphs,
        }

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


readability_adapter = ReadabilityAdapter()
