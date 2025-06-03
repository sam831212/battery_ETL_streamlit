"""merge heads

Revision ID: b1b7c29f7453
Revises: fdc7031ce93e, rename_step_temperature_avg_to_temperature_20250603
Create Date: 2025-06-03 09:23:45.723083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1b7c29f7453'
down_revision: Union[str, None] = ('fdc7031ce93e', 'rename_step_temperature_avg_to_temperature_20250603')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
