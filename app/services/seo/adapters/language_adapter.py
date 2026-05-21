from __future__ import annotations


class LanguageAdapter:
    provider_name = "languagetool"
    enabled = False
    configured = False
    requires_api_key = False
    last_error: str | None = None
    real_data_available = False
    fallback_mode = "not_configured"
    trust_level = "none"

    def __init__(self):
        try:
            import language_tool_python  # noqa: F401
            self.configured = True
            self.enabled = True
            self.real_data_available = True
            self.fallback_mode = "languagetool_local"
            self.trust_level = "high"
        except ImportError:
            pass

    def check(self, text: str, language: str = "fr") -> dict:
        if not self.configured:
            return {
                "external_tool_used": False,
                "tool_used": "heuristic",
                "issues": [],
                "error": "LanguageTool not configured",
            }
        try:
            import language_tool_python
            tool = language_tool_python.LanguageTool(language)
            matches = tool.check(text)
            issues = []
            for m in matches[:50]:
                issues.append({
                    "message": m.message,
                    "category": m.category,
                    "rule_id": m.ruleId,
                    "replacements": m.replacements[:3],
                    "offset": m.offset,
                    "length": m.length,
                })
            return {
                "external_tool_used": True,
                "tool_used": "languagetool",
                "issues": issues,
                "issues_count": len(issues),
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "external_tool_used": False,
                "tool_used": "heuristic",
                "issues": [],
                "error": str(exc),
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


language_adapter = LanguageAdapter()
