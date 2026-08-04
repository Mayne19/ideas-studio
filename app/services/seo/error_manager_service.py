from __future__ import annotations

"""Gestion des erreurs (error_manager) — synthétise les erreurs collectées
pendant une génération d'article en un verdict exploitable : gravité, étapes
bloquantes, et si un nouvel essai automatique a du sens. N'exécute aucun
retry lui-même (ça reste le rôle de production_queue.requeue_stale_writing,
au niveau de la file d'attente) — se contente de qualifier ce qui a été
collecté par SeoGenerationOrchestrator._error() à chaque étape.
"""

# Étapes dont l'échec empêche l'article d'être publiable en l'état — un échec
# ailleurs (ex: ImagePlan, InternalLinkPlan) est une dégradation acceptable.
_BLOCKING_STEPS = {
    "DraftWriting",
    "FactCheckPass",
    "ArticleOutline",
    "KeywordBrief",
}

# Étapes dont l'échec est généralement transitoire (réseau, rate limit) et
# vaut la peine d'être retenté automatiquement plutôt que traité comme un
# échec définitif.
_TRANSIENT_STEP_HINTS = ("timeout", "connection", "rate limit", "503", "429", "unavailable")


def analyze_generation_errors(errors: list[str], steps_completed: list[str]) -> dict:
    """errors : liste de chaînes "[Step] message" telles que collectées par
    SeoGenerationOrchestrator._error(). steps_completed : étapes réussies."""
    if not errors:
        return {
            "status": "clean",
            "severity": "none",
            "blocking_failures": [],
            "transient_failures": [],
            "retry_recommended": False,
            "summary": "Aucune erreur pendant la génération.",
        }

    blocking_failures: list[dict] = []
    transient_failures: list[dict] = []
    other_failures: list[dict] = []

    for entry in errors:
        step, message = _split_entry(entry)
        is_transient = any(hint in message.lower() for hint in _TRANSIENT_STEP_HINTS)
        item = {"step": step, "message": message, "transient": is_transient}
        if step in _BLOCKING_STEPS:
            blocking_failures.append(item)
        elif is_transient:
            transient_failures.append(item)
        else:
            other_failures.append(item)

    if blocking_failures:
        severity = "critical"
        status = "blocked"
    elif transient_failures:
        severity = "medium"
        status = "degraded_transient"
    else:
        severity = "low"
        status = "degraded"

    retry_recommended = bool(transient_failures) and not any(
        f["step"] in _BLOCKING_STEPS and not f["transient"] for f in blocking_failures
    )

    return {
        "status": status,
        "severity": severity,
        "blocking_failures": blocking_failures,
        "transient_failures": transient_failures,
        "other_failures": other_failures,
        "retry_recommended": retry_recommended,
        "summary": _build_summary(blocking_failures, transient_failures, other_failures, steps_completed),
    }


def _split_entry(entry: str) -> tuple[str, str]:
    # Format produit par SeoGenerationOrchestrator._error() : "[Step] message"
    if entry.startswith("[") and "]" in entry:
        step, _, message = entry[1:].partition("]")
        return step.strip(), message.strip()
    return "unknown", entry


def _build_summary(blocking: list[dict], transient: list[dict], other: list[dict], steps_completed: list[str]) -> str:
    parts = []
    if blocking:
        parts.append(f"{len(blocking)} échec(s) bloquant(s) : {', '.join(f['step'] for f in blocking)}")
    if transient:
        parts.append(f"{len(transient)} échec(s) probablement transitoire(s) (réessai recommandé)")
    if other:
        parts.append(f"{len(other)} échec(s) non bloquant(s) — l'article reste utilisable en l'état")
    if not parts:
        parts.append("Aucun échec notable.")
    parts.append(f"{len(steps_completed)} étape(s) complétée(s) avec succès.")
    return " ; ".join(parts)
