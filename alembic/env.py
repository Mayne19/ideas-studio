import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.core.database import Base

# Import models so their tables are registered in Base.metadata
from app.models import user, project, project_member  # noqa: F401
from app.models import category, article, traffic_event  # noqa: F401
from app.models import article_log  # noqa: F401
from app.models import seo_analysis  # noqa: F401
from app.models import optimization_recommendation, notification  # noqa: F401
from app.models import invitation  # noqa: F401
from app.models import project_callout_template  # noqa: F401
from app.models import pipeline  # noqa: F401
from app.models import pipeline_log  # noqa: F401
from app.models import article_version  # noqa: F401
from app.models import media_asset  # noqa: F401
from app.models import webhook  # noqa: F401
from app.models import activity_log  # noqa: F401
from app.models import ai_provider_config  # noqa: F401
from app.models import article_comment  # noqa: F401
from app.models import kanban_column  # noqa: F401

config = context.config
database_url = settings.DATABASE_URL.replace("%", "%%")
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
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
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
