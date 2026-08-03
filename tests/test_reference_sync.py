"""Les IntEnum Python de app/models/reference.py doivent rester synchronisés
avec le contenu réel des tables ref.* — c'est la seule discipline documentée
par plan-migration-v3.md §2 pour éviter que les deux dérivent silencieusement.

Ce module se connecte directement à une base PostgreSQL v3 via la variable
d'environnement V3_TEST_DATABASE_URL (schéma db/migration-v3/01-schema.sql déjà
appliqué). La suite principale (tests/conftest.py) tourne encore sur SQLite
tant que sa propre migration vers PostgreSQL n'a pas été faite (chantier
distinct, non inclus dans REPRENDRE-LA-MAIN.md §6) : ce module est donc
indépendant du conftest global, pour ne pas le forcer sur Postgres.
"""
import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import reference as ref

V3_TEST_DATABASE_URL = os.environ.get("V3_TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not V3_TEST_DATABASE_URL,
    reason="V3_TEST_DATABASE_URL non défini — ce module vérifie le schéma v3 sur "
           "une vraie base PostgreSQL, pas sur le SQLite de la suite principale.",
)


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine(V3_TEST_DATABASE_URL)
    with Session(engine) as session:
        yield session
    engine.dispose()


ENUM_TO_MODEL = [
    (ref.ArticleStatus, ref.RefArticleStatusReason),
    (ref.ProjectStatus, ref.RefProjectStatusReason),
    (ref.MembershipStatus, ref.RefMembershipStatusReason),
    (ref.RunStatus, ref.RefRunStatusReason),
    (ref.StepStatus, ref.RefStepStatusReason),
    (ref.WorkflowPhase, ref.RefWorkflowPhase),
    (ref.MemberRole, ref.RefMemberRole),
    (ref.LogLevel, ref.RefLogLevel),
]


@pytest.mark.parametrize("enum_cls,model_cls", ENUM_TO_MODEL)
def test_intenum_matches_ref_table(db_session, enum_cls, model_cls):
    rows = db_session.execute(select(model_cls)).scalars().all()
    db_ids = sorted(r.id for r in rows)
    py_values = sorted(m.value for m in enum_cls)
    assert py_values == db_ids, (
        f"{enum_cls.__name__} (Python) et {model_cls.__tablename__} (base) ont divergé : "
        f"python={py_values} base={db_ids}"
    )


def test_states_table_has_active_and_inactive(db_session):
    rows = db_session.execute(select(ref.RefStates)).scalars().all()
    codes = {r.code for r in rows}
    assert codes == {"active", "inactive"}
