"""Client minimal vers la session Claude Code déjà authentifiée sur la machine.

Il n'expose ni ne copie de credential. Claude Code s'occupe de l'authentification
OAuth et le laboratoire ne conserve que le texte des réponses nécessaires à
l'essai courant.
"""

from __future__ import annotations

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

    @property
    def content(self):
        return [SimpleNamespace(type="text", text=self.text)]

    @property
    def stop_reason(self):
        return "end_turn"

    @property
    def usage(self):
        return SimpleNamespace(input_tokens=0, output_tokens=0, cache_read_input_tokens=0)


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
        self.cost_usd = None

    def _run(self, system: str, prompt: str, *, web_tools: bool = False) -> str:
        command = [
            self.binary,
            "-p",
            prompt,
            "--model",
            self.model,
            "--permission-mode",
            "dontAsk",
            "--no-session-persistence",
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
        return (result.stdout or "").strip()

    def _create(self, *, system: str, messages: list[dict], **kwargs):
        prompt_parts = []
        for message in messages:
            role = message.get("role", "user")
            prompt_parts.append(f"{role.upper()}:\n{_text(message.get('content', ''))}")
        text = self._run(system, "\n\n".join(prompt_parts), web_tools=True)
        return ClaudeCliResponse(text)

    def complete(self, system: str, prompt: str, *, max_tokens: int = 32000) -> str:
        return self._run(system, prompt, web_tools=False)
