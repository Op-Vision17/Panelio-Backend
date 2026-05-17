import asyncio
import os
import re
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import settings
from app.core.database import Base

# IMPORTANT: Import all models for Alembic autogenerate
from app.features.auth.model import RefreshToken, User
from app.features.questions.model import Question
from app.features.vivas.model import Viva

# Alembic Config object
config = context.config

# Set DB URL from app settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

# Logging setup
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate
target_metadata = Base.metadata


def revision_id_generator(context, revision, directives):
    """
    Generate sequential revision IDs:
    0001, 0002, 0003 ...
    """

    script_dir = context.script.dir
    versions_dir = os.path.join(script_dir, "versions")

    max_num = 0

    if os.path.exists(versions_dir):
        for filename in os.listdir(versions_dir):

            if filename.endswith(".py") and not filename.startswith("__"):

                match = re.match(r"^(\d+)_", filename)

                if match:
                    num = int(match.group(1))
                    max_num = max(max_num, num)

    next_num = max_num + 1

    if directives and len(directives) > 0:
        migration_script = directives[0]
        migration_script.rev_id = f"{next_num:04d}"


def run_migrations_offline() -> None:
    """
    Run migrations in offline mode.
    """

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        process_revision_directives=revision_id_generator,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        process_revision_directives=revision_id_generator,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in online mode.
    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
