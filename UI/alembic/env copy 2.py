from logging.config import fileConfig
import re
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from sqlmodel import SQLModel

# 1. Import your respective model MetaData objects
from database.models import Base
from database.paycheck_models import PaycheckBase, Paycheck, PaycheckLineItem

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2. Map your ini section names to the correct target metadata
target_metadata = {
    "portfolio_db": Base.metadata,
    "paycheck_db": PaycheckBase.metadata,
}

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Retrieve the databases list from alembic.ini
    db_names = config.get_main_option("databases")

    for name in re.split(r',\s*', db_names):
        context.configure(
            url=config.get_section_option(name, "sqlalchemy.url"),
            target_metadata=target_metadata.get(name),
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )

        with context.begin_transaction():
            context.run_migrations(engine_name=name)

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Create an engine for each database definition
    db_names = config.get_main_option("databases")
    engines = {}

    for name in re.split(r',\s*', db_names):
        engines[name] = engine_from_config(
            config.get_section(name) or {},
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    # Run migrations independently for each engine connection
    for name, engine in engines.items():
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata.get(name)
            )

            with context.begin_transaction():
                context.run_migrations(engine_name=name)

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()