from __future__ import with_statement

from logging.config import fileConfig
import logging
import os.path

from alembic import context
from sqlalchemy import engine_from_config, pool

from yakbak.models import db
from yakbak.settings import load_settings_file

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def ignore_social_auth_tables(tablename, schema):
    if tablename.startswith("social_auth_"):
        return False
    return True


def inject_uri_from_settings():
    """
    Use the DB URI from yakbak.toml, overwriting whatever is in alembic.ini.

    """
    alembic_dir = os.path.dirname(__file__)
    yakbak_toml = os.path.join(alembic_dir, "..", "yakbak.toml")
    logging.getLogger("alembic").info("Loading database URI from %s", yakbak_toml)
    settings = load_settings_file(yakbak_toml)
    config.set_main_option("sqlalchemy.url", settings.db.uri)

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    inject_uri_from_settings()

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_symbol=ignore_social_auth_tables,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    inject_uri_from_settings()

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_symbol=ignore_social_auth_tables,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
