from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from forkscan.infrastructure.database.base import Base
from forkscan.infrastructure.database.models import User, RefreshToken, SubscriptionPlan, Subscription
from alembic import context

# Эта функция должна возвращать строку подключения (лучше брать из env/config)
from forkscan.core.config import settings

# Alembic Config object
config = context.config

# Настрой url из config
config.set_main_option(
    'sqlalchemy.url', str(settings.database_url).replace('+asyncpg', '')
)

# Настрой логирование
fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
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

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
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