"""v3 baseline — schéma ref/core/content/ai/analytics/ops

Cette révision ne contient AUCUN DDL exécutable : le schéma v3 a été appliqué
directement en production via db/migration-v3/01-schema.sql et 02-donnees.sql
(voir db/migration-v3/REPRENDRE-LA-MAIN.md), avant qu'Alembic ne reprenne la
main. `alembic stamp head` marque cette révision comme appliquée sans exécuter
upgrade() — la base réelle est déjà dans l'état attendu par app/models/*.

Les 44 révisions v2 (schéma plat pré-refonte) sont archivées dans
alembic/versions_archive_v2/ pour référence historique, hors de la chaîne de
révisions active. Toute nouvelle migration doit partir de cette baseline.

Revision ID: v3_0001
Revises:
Create Date: 2026-08-03
"""
from typing import Sequence, Union

revision: str = "v3_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op — schéma déjà appliqué manuellement, voir docstring ci-dessus."""
    pass


def downgrade() -> None:
    """No-op — un rollback complet du schéma v3 doit être fait manuellement
    (aucune migration automatique ne recrée le schéma v2 à plat)."""
    pass
