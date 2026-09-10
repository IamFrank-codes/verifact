"""Apply the VeriFact schema to Supabase and copy data from a local database.

The target database must be empty. The script preserves primary keys so foreign
key relationships and existing report links remain valid.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, insert, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.db import Base  # noqa: E402
import app.models  # noqa: E402,F401


TABLE_ORDER = (
    'users',
    'articles',
    'sources',
    'password_reset_tokens',
    'verifications',
    'claims',
    'evidence',
    'verification_scores',
    'provider_runs',
)


def migrate_schema(target_url: str) -> None:
    alembic_config = Config(str(ROOT / 'backend' / 'alembic.ini'))
    alembic_config.set_main_option('sqlalchemy.url', target_url.replace('%', '%%'))
    command.upgrade(alembic_config, 'head')


def copy_data(source_url: str, target_url: str) -> int:
    source_engine = create_engine(source_url, pool_pre_ping=True)
    target_engine = create_engine(target_url, pool_pre_ping=True)
    copied = 0

    with source_engine.connect() as source, target_engine.begin() as target:
        for table_name in TABLE_ORDER:
            table = Base.metadata.tables[table_name]
            target_count = target.scalar(select(func.count()).select_from(table))
            if target_count:
                raise RuntimeError(
                    f'Target table {table_name!r} is not empty; refusing to merge or overwrite data.'
                )
            rows = source.execute(select(table)).mappings().all()
            if rows:
                target.execute(insert(table), [dict(row) for row in rows])
                copied += len(rows)
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-url', required=True, help='SQLAlchemy URL for the local database.')
    parser.add_argument('--target-url', required=True, help='SQLAlchemy URL for Supabase PostgreSQL.')
    args = parser.parse_args()

    if not args.target_url.startswith('postgresql'):
        raise ValueError('The target must be a PostgreSQL URL for Supabase.')
    migrate_schema(args.target_url)
    copied = copy_data(args.source_url, args.target_url)
    print(f'Migration complete; copied {copied} rows.')


if __name__ == '__main__':
    main()
