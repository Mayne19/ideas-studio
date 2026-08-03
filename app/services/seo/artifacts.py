"""Accès à ai.artifacts — remplace les ~40 colonnes articles.<x>_json de
l'ancien modèle plat. Une ligne par (article, agent_key), la plus récente
fait foi. Voir db/migration-v3/REPRENDRE-LA-MAIN.md §6 étape 6.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import Artifact


def save_artifact(db: Session, article_id: str, agent_key: str, payload: dict[str, Any]) -> Artifact:
    """Enregistre une nouvelle version de l'artefact — ne met jamais à jour en
    place, l'historique complet reste consultable (created_at DESC)."""
    artifact = Artifact(article_id=article_id, agent_key=agent_key, payload=payload)
    db.add(artifact)
    db.flush()
    return artifact


def get_latest_artifact(db: Session, article_id: str, agent_key: str) -> dict[str, Any] | None:
    artifact = db.execute(
        select(Artifact)
        .where(Artifact.article_id == article_id, Artifact.agent_key == agent_key)
        .order_by(Artifact.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return artifact.payload if artifact else None


def get_latest_artifacts(db: Session, article_id: str, agent_keys: list[str]) -> dict[str, dict[str, Any]]:
    """Version groupée : une requête pour plusieurs agent_key à la fois
    (utilisé par compute_global_score, qui a besoin de 4-5 artefacts)."""
    rows = db.execute(
        select(Artifact)
        .where(Artifact.article_id == article_id, Artifact.agent_key.in_(agent_keys))
        .order_by(Artifact.agent_key, Artifact.created_at.desc())
    ).scalars().all()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        # La première ligne rencontrée par agent_key est la plus récente (tri ci-dessus)
        result.setdefault(row.agent_key, row.payload)
    return result


def get_all_latest_artifacts(db: Session, article_id: str) -> dict[str, dict[str, Any]]:
    """Tous les agent_key connus pour cet article, sans liste fixe — utilisé
    par l'éditeur qui affiche tout ce qui existe (voir schemas/editor.py)."""
    rows = db.execute(
        select(Artifact)
        .where(Artifact.article_id == article_id)
        .order_by(Artifact.agent_key, Artifact.created_at.desc())
    ).scalars().all()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        result.setdefault(row.agent_key, row.payload)
    return result
