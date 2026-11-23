
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from app.db.database import Base, engine

# Import every model so SQLAlchemy registers its tables.
from app.models.organization import Organization
from app.models.user import User
from app.models.document import Document, DocumentChunk


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Configure migrations without a live database connection."""

    url = engine.url

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Configure migrations using the existing database engine."""

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
