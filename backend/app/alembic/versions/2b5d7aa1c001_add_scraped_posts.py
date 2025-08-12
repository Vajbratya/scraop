"""Add scraped posts table

Revision ID: 2b5d7aa1c001
Revises: 1a31ce608336
Create Date: 2025-08-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2b5d7aa1c001"
down_revision = "1a31ce608336"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scrapedpost",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company", sa.String(length=128), index=True, nullable=False),
        sa.Column("platform", sa.String(length=64), index=True, nullable=False),
        sa.Column("url", sa.String(length=2048), unique=True, nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=12), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
    )


def downgrade():
    op.drop_table("scrapedpost")
