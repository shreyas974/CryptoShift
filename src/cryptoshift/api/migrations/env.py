"""Alembic environment for the CryptoShift web app (SQLite, online mode only)."""

from alembic import context
from sqlalchemy import create_engine

config = context.config


def run() -> None:
    engine = create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    with engine.connect() as conn:
        context.configure(connection=conn, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run()
