# migrations/env.py

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Make sure your models are importable. Adjust path as necessary.
# This assumes your 'models.py' is in the parent directory of 'migrations'.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models import Base # Ensure 'Base' is imported correctly for your models

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This sets up logging based on the [loggers], [handlers], [formatters] sections in alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata # Assuming 'Base' is your SQLAlchemy declarative base

# Set the SQLAlchemy URL from the DATABASE_URL environment variable first.
database_url = os.getenv("DATABASE_URL")

# --- DEBUG PRINT STATEMENT HERE ---
print(f"DEBUG: DATABASE_URL from environment is: {database_url}")
# --- END DEBUG PRINT STATEMENT ---

if database_url:
    # Set the database URL in Alembic's configuration
    config.set_main_option("sqlalchemy.url", database_url)
else:
    # If DATABASE_URL is not set (e.g., local development without Render env vars),
    # Alembic will use the value from alembic.ini (which is "DUMMY_DATABASE_URL").
    # For local testing, you might load from a .env file here:
    # from dotenv import load_dotenv
    # load_dotenv()
    # config.set_main_option("sqlalchemy.url", os.getenv("LOCAL_DB_URL", "sqlite:///./test.db"))
    pass


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is additionally
    passed in this mode to provide added convenience
    for outputting existing schema DDL.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use engine_from_config to create an engine based on the config object.
    # It will use the 'sqlalchemy.url' option, which was set from DATABASE_URL.
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()