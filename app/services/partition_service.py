"""Création des partitions mensuelles des tables partitionnées (schéma v3).

ops.event_logs, ai.usage_events et analytics.traffic_events sont partitionnées
par mois sur `occurred_at`. Sans partition pour le mois courant, toute
insertion échoue (« no partition of relation ... found for row »), ce qui
casse jusqu'à la génération d'articles. Ce service crée, de façon idempotente,
la partition du mois en cours et des mois suivants.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

PARTITIONED_TABLES = (
    ("ops", "event_logs"),
    ("ai", "usage_events"),
    ("analytics", "traffic_events"),
)


def _add_months(day: date, months: int) -> date:
    index = day.year * 12 + (day.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


def ensure_monthly_partitions(engine: Engine, months_ahead: int = 3, today: date | None = None) -> list[str]:
    """Crée les partitions manquantes du mois courant à `months_ahead` mois.

    Retourne la liste des partitions créées. Ne fait rien hors PostgreSQL.
    """
    if engine.dialect.name != "postgresql":
        return []
    start = (today or datetime.now(timezone.utc).date()).replace(day=1)
    created: list[str] = []
    with engine.begin() as conn:
        for schema, table in PARTITIONED_TABLES:
            exists = conn.execute(
                text("select to_regclass(:name) is not null"),
                {"name": f"{schema}.{table}"},
            ).scalar()
            if not exists:
                continue
            for offset in range(months_ahead + 1):
                lower = _add_months(start, offset)
                upper = _add_months(start, offset + 1)
                partition = f"{table}_{lower.year}_{lower.month:02d}"
                already = conn.execute(
                    text("select to_regclass(:name) is not null"),
                    {"name": f"{schema}.{partition}"},
                ).scalar()
                if already:
                    continue
                conn.execute(text(
                    f'CREATE TABLE IF NOT EXISTS "{schema}"."{partition}" '
                    f'PARTITION OF "{schema}"."{table}" '
                    f"FOR VALUES FROM ('{lower.isoformat()} 00:00:00+00') TO ('{upper.isoformat()} 00:00:00+00')"
                ))
                created.append(f"{schema}.{partition}")
    if created:
        logger.info("Monthly partitions created: %s", ", ".join(created))
    return created
