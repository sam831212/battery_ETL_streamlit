"""
Rename step.temperature_avg to step.temperature

Revision ID: rename_step_temperature_avg_to_temperature_20250603
Revises: remove_temp_min_max_20250603
Create Date: 2025-06-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'rename_step_temperature_avg_to_temperature_20250603'
down_revision = 'remove_temp_min_max_20250603'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('step') as batch_op:
        batch_op.alter_column('temperature_avg', new_column_name='temperature')

def downgrade():
    with op.batch_alter_table('step') as batch_op:
        batch_op.alter_column('temperature', new_column_name='temperature_avg')
