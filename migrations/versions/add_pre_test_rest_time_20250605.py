"""
Add pre_test_rest_time column to Step table

Revision ID: add_pre_test_rest_time_20250605
Revises: de227a3297e5
Create Date: 2025-06-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_pre_test_rest_time_20250605'
down_revision = 'de227a3297e5'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('step', sa.Column('pre_test_rest_time', sa.Float(), nullable=True))

def downgrade():
    op.drop_column('step', 'pre_test_rest_time')
