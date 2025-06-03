"""remove temperature_min and temperature_max from step table

Revision ID: remove_temp_min_max_20250603
Revises: de4b58ac3df6
Create Date: 2025-06-03

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'remove_temp_min_max_20250603'
down_revision: Union[str, None] = 'de4b58ac3df6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Remove temperature_min and temperature_max columns from step table."""
    with op.batch_alter_table('step') as batch_op:
        batch_op.drop_column('temperature_min')
        batch_op.drop_column('temperature_max')

def downgrade() -> None:
    """Add temperature_min and temperature_max columns back to step table."""
    with op.batch_alter_table('step') as batch_op:
        batch_op.add_column(sa.Column('temperature_min', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('temperature_max', sa.Float(), nullable=True))
