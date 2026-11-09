"""Owner-only application migration and seed, with a transaction advisory lock."""
from pathlib import Path
import os
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from aat_metadata.repositories.base import create_app_engine


ROOT=Path(__file__).resolve().parents[2]


def initialize():
    engine=create_app_engine(owner=True)
    try:
        with engine.begin() as connection:
            if connection.scalar(text('SELECT current_database()'))!='app_metadata':raise RuntimeError('Wrong application database')
            connection.execute(text("SET LOCAL statement_timeout='90s'"))
            connection.execute(text("SET LOCAL lock_timeout='60s'"))
            connection.execute(text('SELECT pg_advisory_xact_lock(718423001)'))
            config=Config();config.set_main_option('script_location',str(ROOT/'backend/alembic'))
            config.attributes['connection']=connection
            command.upgrade(config,'head')
            from aat_api.services.seed import seed
            seed(connection,ROOT)
            # Runtime grants are installed explicitly by T031, not default PUBLIC grants.
            from aat_metadata.repositories.grants import apply_grants
            apply_grants(connection)
    finally:engine.dispose()


if __name__=='__main__':
    try:
        if os.environ.get('AAT_FOUNDATION_DISPOSABLE')!='1':
            from docker.bootstrap.initialize import initialize as initialize_storage
            initialize_storage()
        initialize()
    except Exception as exc:
        # Class only: driver DSN, paths and ciphertext never enter published output.
        raise SystemExit('Application initialization failed ('+type(exc).__name__+'); restore/check original metadata and keys') from None
