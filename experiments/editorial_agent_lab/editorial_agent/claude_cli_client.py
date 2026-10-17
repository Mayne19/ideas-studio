"""Lance le rédacteur : un seul agent Claude Code non interactif, avec la
session déjà authentifiée sur la machine (abonnement, aucune clé copiée).

L'agent n'a accès qu'au skill redaction-article et aux outils WebSearch et
WebFetch : il ne peut lire aucun fichier du dépôt (en particulier pas
tests/data/judge_calibration, réservé à l'étalonnage du juge).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ALLOWED_TOOLS = ("Skill", "WebSearch", "WebFetch")
DEFAULT_MODEL = "opus"
DEFAULT_EFFORT = "high"
REPO_ROOT = Path(__file__).resolve().parents[3]


def find_claude_cli() -> str | None:
    """Trouve Claude Code dans le PATH ou dans l'extension VS Code installée."""

    configured = shutil.which("claude")
    if configured:
        return configured
    extensions = Path.home() / ".vscode" / "extensions"
    candidates = sorted(extensions.glob("anthropic.claude-code-*/resources/native-binary/claude"), reverse=True)
    return str(candidates[0]) if candidates else None


def build_command(binary: str, prompt: str, *, model: str = DEFAULT_MODEL, effort: str = DEFAULT_EFFORT) -> list[str]:
    return [
        binary, "-p", prompt,
        "--model", model,
        "--effort", effort,
        "--allowed-tools", *ALLOWED_TOOLS,
        "--permission-mode", "dontAsk",
        "--no-session-persistence",
        "--output-format", "json",
    ]


def parse_result(stdout: str) -> dict:
    """Texte rendu, jetons et coût réel depuis la sortie JSON de Claude Code."""

    try:
        payload = json.loads((stdout or "").strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError("Claude Code a renvoyé une réponse inexploitable.") from exc
    if payload.get("is_error"):
        raise RuntimeError(str(payload.get("result") or "La session Claude Code a échoué."))
    usage = payload.get("usage") or {}
    return {
        "text": str(payload.get("result") or "").strip(),
        "cost_usd": payload.get("total_cost_usd"),
        "duration_s": round((payload.get("duration_ms") or 0) / 1000, 1),
        "turns": payload.get("num_turns"),
        "tokens": {
            "input": int(usage.get("input_tokens") or 0),
            "output": int(usage.get("output_tokens") or 0),
            "cache_creation": int(usage.get("cache_creation_input_tokens") or 0),
            "cache_read": int(usage.get("cache_read_input_tokens") or 0),
        },
        "web_search_requests": int((usage.get("server_tool_use") or {}).get("web_search_requests") or 0),
        "model_usage": payload.get("modelUsage") or {},
    }


def run_writer(prompt: str, *, model: str = DEFAULT_MODEL, effort: str = DEFAULT_EFFORT,
               timeout_seconds: float = 1800.0) -> dict:
    binary = find_claude_cli()
    if not binary:
        raise RuntimeError("Claude Code n'est pas installé sur cette machine.")
    try:
        result = subprocess.run(build_command(binary, prompt, model=model, effort=effort), capture_output=True,
                                text=True, timeout=timeout_seconds, check=False, cwd=REPO_ROOT)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("La session Claude Code a dépassé le délai autorisé.") from exc
    if result.returncode != 0 and not (result.stdout or "").strip():
        detail = (result.stderr or "").strip().splitlines()
        raise RuntimeError(detail[-1] if detail else "La session Claude Code a échoué.")
    return parse_result(result.stdout)
