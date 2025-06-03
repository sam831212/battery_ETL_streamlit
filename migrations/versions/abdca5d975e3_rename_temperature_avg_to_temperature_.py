"""rename temperature_avg to temperature in experiment table

Revision ID: abdca5d975e3
Revises: b1b7c29f7453
Create Date: 2025-06-03 09:28:16.089602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abdca5d975e3'
down_revision: Union[str, None] = 'b1b7c29f7453'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('experiment', 'temperature_avg', new_column_name='temperature')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('experiment', 'temperature', new_column_name='temperature_avg')
