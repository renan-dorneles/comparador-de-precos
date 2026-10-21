# ============================================================
# alembic/env.py
# ============================================================
"""Ambiente do Alembic com suporte a SQLAlchemy 2.0 async."""

from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

import asyncio
import os
import sys

# Adiciona o diretório src ao path para importar os modelos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Importa os modelos SQLAlchemy
from comparador_precos.core.database import Base
from comparador_precos.core.config import get_settings

# Configurações do Alembic
config = context.config

# Interpreta o arquivo de configuração para logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Substitui a URL do banco por variável de ambiente ou config
db_url = os.getenv("DATABASE_URL", None)
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Metadata dos modelos para migrações
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Executa migrações em modo offline (sem conexão com BD)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Executa migrações usando uma conexão síncrona."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Executa migrações de forma assíncrona."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Executa migrações em modo online (com conexão com BD)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()