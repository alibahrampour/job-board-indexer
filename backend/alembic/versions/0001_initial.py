"""Baseline schema.

The baseline is created from the SQLAlchemy metadata so it always matches the
models (including the generated tsvector column and its GIN index).
Every later change should be generated with:
    alembic revision --autogenerate -m "describe change"
"""
from alembic import op

import app.models  # noqa: F401
from app.database import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
