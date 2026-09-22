"""add summary to conversations

Revision ID: 01a903037c36
Revises: cc5f9ab0e1e0
Create Date: 2026-09-22 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "01a903037c36"
down_revision: str | None = "cc5f9ab0e1e0"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("conversations", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("conversations", "summary")
