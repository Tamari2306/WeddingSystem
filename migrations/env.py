# migrations/env.py

import sys
import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

# Ensure your app's root path is in the system path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import Base  # Make sure this points to the declarative base

# Alembic Config object
config = context.config

# Logging configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogeneration
target_metadata = Base.metadata

# Read the database URL from the environment
database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL environment variable not set.")

# Apply the database URL to Alembic's config
config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
