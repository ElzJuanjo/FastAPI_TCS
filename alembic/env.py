"""Alembic Environment — EventosTCS."""
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Asegurar que el root del proyecto esté en sys.path ──
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.infra.config.settings import get_settings       # noqa: E402
from src.infra.config.database import Base                # noqa: E402

# Importar TODOS los modelos para que Base.metadata los conozca
import src.domain.entities  # noqa: F401, E402

# ── Alembic Config ──
config = context.config

# Inyectar la URL de conexión desde settings (no desde alembic.ini)
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera SQL sin conectar al servidor."""
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
    """Ejecuta migraciones contra la base de datos."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
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
