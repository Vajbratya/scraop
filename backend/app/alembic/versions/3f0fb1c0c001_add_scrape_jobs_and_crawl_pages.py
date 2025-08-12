"""Add scrape jobs and crawl pages

Revision ID: 3f0fb1c0c001
Revises: 2b5d7aa1c001
Create Date: 2025-08-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3f0fb1c0c001"
down_revision = "2b5d7aa1c001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scrapejob",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("seeds", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("allowed_domains", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("include_patterns", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("exclude_patterns", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("max_depth", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("max_pages", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("render_js", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("webhook_url", sa.String(length=2048), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("stats", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "crawlpage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("normalized_url", sa.String(length=2048), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("meta", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["scrapejob.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_crawlpage_url", "crawlpage", ["url"]) 
    op.create_index("ix_crawlpage_normalized_url", "crawlpage", ["normalized_url"]) 


def downgrade():
    op.drop_index("ix_crawlpage_url", table_name="crawlpage")
    op.drop_index("ix_crawlpage_normalized_url", table_name="crawlpage")
    op.drop_table("crawlpage")
    op.drop_table("scrapejob")
