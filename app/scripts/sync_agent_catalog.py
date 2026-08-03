"""Synchronise ai.agents depuis le registre Python (source de vérité) — voir
db/migration-v3/REPRENDRE-LA-MAIN.md §6 étape 9. Le sens de synchronisation
est fixe : app/services/agents/agent_registry.py -> ai.agents, jamais
l'inverse. Idempotent : upsert par key, jamais de suppression (un agent retiré
du registre reste en base tel quel plutôt que de casser les FK
ai.agent_bindings/ai.artifacts qui le référencent)."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import Agent
from app.services.agents.agent_registry import AGENTS

logger = logging.getLogger(__name__)


def sync_agent_catalog(db: Session) -> dict:
    existing = {a.key: a for a in db.execute(select(Agent)).scalars().all()}
    created = 0
    updated = 0

    for sort_order, agent_def in enumerate(AGENTS):
        row = existing.get(agent_def.agent_id)
        if row is None:
            row = Agent(
                key=agent_def.agent_id,
                label=agent_def.name,
                category=agent_def.category.value,
                phase=agent_def.phase,
                status=agent_def.status.value,
                output_json_field=agent_def.output_json_field,
                requires_llm=agent_def.requires_llm,
                requires_search=agent_def.requires_search,
                sort_order=sort_order,
                is_visible_in_frontend=agent_def.visible_in_frontend,
            )
            db.add(row)
            created += 1
        else:
            row.label = agent_def.name
            row.category = agent_def.category.value
            row.phase = agent_def.phase
            row.status = agent_def.status.value
            row.output_json_field = agent_def.output_json_field
            row.requires_llm = agent_def.requires_llm
            row.requires_search = agent_def.requires_search
            row.sort_order = sort_order
            row.is_visible_in_frontend = agent_def.visible_in_frontend
            updated += 1

    db.commit()
    logger.info("Agent catalog sync: %d créés, %d mis à jour (%d total)", created, updated, len(AGENTS))
    return {"created": created, "updated": updated, "total": len(AGENTS)}
