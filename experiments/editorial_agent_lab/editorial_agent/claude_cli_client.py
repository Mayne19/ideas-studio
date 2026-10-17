"""Client minimal vers la session Claude Code déjà authentifiée sur la machine.

Il n'expose ni ne copie de credential. Claude Code s'occupe de l'authentification
OAuth et le laboratoire ne conserve que le texte des réponses nécessaires à
l'essai courant.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace


def find_claude_cli() -> str | None:
    """Trouve Claude Code dans le PATH ou dans l'extension VS Code installée."""

    configured = shutil.which("claude")
    if configured:
        return configured
    extensions = Path.home() / ".vscode" / "extensions"
    candidates = sorted(
        extensions.glob("anthropic.claude-code-*/resources/native-binary/claude"),
        reverse=True,
    )
    return str(candidates[0]) if candidates else None


def _text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if value.get("text"):
            return str(value["text"])
        return _text(value.get("content", ""))
    if isinstance(value, (list, tuple)):
        return "".join(_text(item) for item in value)
    return str(getattr(value, "text", "") or getattr(value, "content", "") or "")


@dataclass
class ClaudeCliResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cost_usd: float | None = None

    @property
    def content(self):
        return [SimpleNamespace(type="text", text=self.text)]

    @property
    def stop_reason(self):
        return "end_turn"

    @property
    def usage(self):
        return SimpleNamespace(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens,
        )


class ClaudeCliClient:
    """Expose la session Claude Code comme client compatible avec le labo."""

    def __init__(self, *, model: str = "opus", timeout_seconds: float = 900.0):
        self.binary = find_claude_cli()
        if not self.binary:
            raise RuntimeError("Claude Code n'est pas installé sur cette machine.")
        self.model = model or "opus"
        self.timeout_seconds = timeout_seconds
        self.messages = SimpleNamespace(create=self._create)
        self.fetch_log: list[str] = []
        self.search_log: list[str] = []
        self.cost_usd: float | None = None
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_read_input_tokens = 0
        self.calls = 0

    def _run(self, system: str, prompt: str, *, web_tools: bool = False) -> tuple[str, dict]:
        command = [
            self.binary,
            "-p",
            prompt,
            "--model",
            self.model,
            "--permission-mode",
            "dontAsk",
            "--no-session-persistence",
            "--output-format",
            "json",
            "--system-prompt",
            system,
        ]
        if web_tools:
            command.extend(["--allowed-tools", "WebSearch", "WebFetch"])
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("La session Claude Code a dépassé le délai autorisé.") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip().splitlines()
            raise RuntimeError(detail[-1] if detail else "La session Claude Code a échoué.")
        raw = (result.stdout or "").strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Claude Code a renvoyé une réponse inexploitable.") from exc
        if payload.get("is_error"):
            raise RuntimeError(str(payload.get("result") or "La session Claude Code a échoué."))
        usage = payload.get("usage") or {}
        self.calls += 1
        self.input_tokens += int(usage.get("input_tokens") or 0)
        self.output_tokens += int(usage.get("output_tokens") or 0)
        self.cache_read_input_tokens += int(usage.get("cache_read_input_tokens") or 0)
        reported_cost = payload.get("total_cost_usd")
        if reported_cost is not None:
            self.cost_usd = round((self.cost_usd or 0.0) + float(reported_cost), 6)
        return str(payload.get("result") or "").strip(), usage

    def _create(self, *, system: str, messages: list[dict], **kwargs):
        prompt_parts = []
        for message in messages:
            role = message.get("role", "user")
            prompt_parts.append(f"{role.upper()}:\n{_text(message.get('content', ''))}")
        text, usage = self._run(system, "\n\n".join(prompt_parts), web_tools=True)
        return ClaudeCliResponse(
            text,
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            cache_read_input_tokens=int(usage.get("cache_read_input_tokens") or 0),
            cost_usd=self.cost_usd,
        )

    def complete(self, system: str, prompt: str, *, max_tokens: int = 32000) -> str:
        text, _ = self._run(system, prompt, web_tools=False)
        return text

    def usage_summary(self) -> dict[str, object]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "calls": self.calls,
            "cost_usd": self.cost_usd,
            "cost_source": "claude_code_total_cost_usd",
        }
