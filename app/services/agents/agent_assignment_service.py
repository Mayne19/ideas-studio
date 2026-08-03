"""Cycle de vie des assignations agent → provider IA."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.agent_assignment import AgentAssignment
from app.models.ai_provider_config import AIProviderConfig

logger = logging.getLogger(__name__)


def delete_assignments_for_provider(db: Session, provider_id: str) -> int:
    """Supprime les assignations pointant vers un provider donné.

    À appeler avant de supprimer un AIProviderConfig : sans FK en base, les
    assignations survivraient à leur provider et s'afficheraient sans nom.
    """
    deleted = (
        db.query(AgentAssignment)
        .filter(AgentAssignment.provider_id == provider_id)
        .delete(synchronize_session=False)
    )
    if deleted:
        logger.info("Suppression de %s assignation(s) liée(s) au provider %s", deleted, provider_id)
    return deleted


def cleanup_orphan_assignments(db: Session) -> int:
    """Supprime les assignations dont le provider n'existe plus."""
    orphan_ids = [
        row[0]
        for row in db.query(AgentAssignment.id)
        .outerjoin(AIProviderConfig, AIProviderConfig.id == AgentAssignment.provider_id)
        .filter(AIProviderConfig.id.is_(None))
        .all()
    ]
    if not orphan_ids:
        return 0
    db.query(AgentAssignment).filter(AgentAssignment.id.in_(orphan_ids)).delete(
        synchronize_session=False
    )
    logger.info("Nettoyage de %s assignation(s) orpheline(s)", len(orphan_ids))
    return len(orphan_ids)
