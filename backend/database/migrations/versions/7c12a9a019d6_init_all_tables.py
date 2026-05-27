"""init_all_tables

Revision ID: 7c12a9a019d6
Revises:
Create Date: 2026-05-26 11:13:15.101699

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "7c12a9a019d6"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
