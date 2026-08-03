import contextvars
from datetime import datetime

from sqlalchemy import create_engine, event, text
from sqlalchemy import DateTime
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.core.config import settings


def _make_engine():
    kwargs = {}
    database_url = settings.database_url
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, **kwargs)


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    # Mapped[datetime] -> timestamptz partout (schéma v3, voir 01-schema.sql) ;
    # sans ce mapping, SQLAlchemy infère un DateTime naïf et alembic --autogenerate
    # propose de dropper le "timezone=True" réel de chaque colonne à chaque diff.
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


# ── Isolation multi-tenant (RLS) ───────────────────────────────────────────
#
# `current_project_id` porte le project_id de la requête HTTP ou du job en
# cours. Posé explicitement par les dépendances de routers (get_project_member
# et consorts, app/dependencies/auth.py) et par chaque job APScheduler avant
# toute requête (app/services/worker.py) — jamais implicite.
#
# La politique RLS elle-même (db/migration-v3/rls-a-activer-plus-tard.sql)
# n'est PAS encore activée en base : tant qu'elle ne l'est pas, ce hook est
# un SET LOCAL sans effet (aucune policy ne le lit). Une fois activée, toute
# session qui n'aurait pas posé current_project_id devient aveugle (0 ligne
# sur les tables sous RLS) plutôt que de fuiter entre projets — c'est le
# comportement voulu, pas un bug.
current_project_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_project_id", default=None
)


def set_current_project_id(project_id: str | None) -> None:
    current_project_id.set(project_id)


@event.listens_for(Session, "after_begin")
def _set_rls_project_id(session, transaction, connection):
    if not settings.database_url.startswith("postgresql"):
        return
    project_id = current_project_id.get()
    # set_config(..., is_local=true) : équivalent paramétrable de SET LOCAL,
    # portable quel que soit le driver — SET LOCAL brut n'accepte pas de
    # paramètre lié de façon garantie selon le dialecte.
    connection.execute(text("SELECT set_config('app.project_id', :pid, true)"), {"pid": project_id or ""})


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
