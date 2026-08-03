import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.core.database import Base

# Import models so their tables are registered in Base.metadata — schéma v3
# (ref/core/content/ai/analytics/ops), voir db/migration-v3/01-schema.sql.
from app.models import reference  # noqa: F401
from app.models import core  # noqa: F401
from app.models import content  # noqa: F401
from app.models import ai  # noqa: F401
from app.models import analytics  # noqa: F401
from app.models import ops  # noqa: F401

config = context.config
database_url = settings.database_url.replace("%", "%%")
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    # disable_existing_loggers=False : sinon ce fileConfig désactive silencieusement
    # tous les loggers déjà créés au moment des migrations de démarrage (uvicorn.access,
    # uvicorn.error...), y compris ceux qui journalisent les tracebacks des erreurs 500 —
    # plus aucune requête ni exception n'est journalisée après le démarrage de l'app.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


# Tous les modèles v3 vivent dans des schémas non-default (ref/core/content/
# ai/analytics/ops) — sans include_schemas=True, l'autogenerate d'Alembic ne
# regarde que le schéma par défaut de la connexion et propose de recréer
# toutes les tables existantes à chaque diff. Confirmé en pratique : un diff
# sans ce réglage listait les ~29 tables v3 comme "added" alors qu'elles
# existent déjà.
_SCHEMAS = {"ref", "core", "content", "ai", "analytics", "ops"}


def _include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in _SCHEMAS or name is None
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_name=_include_name,
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=_include_name,
            version_table_schema="public",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
