"""merge heads

Revision ID: fdc7031ce93e
Revises: 83131810bc2b, remove_temp_min_max_20250603
Create Date: 2025-06-03 09:15:19.431333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdc7031ce93e'
down_revision: Union[str, None] = ('83131810bc2b', 'remove_temp_min_max_20250603')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
