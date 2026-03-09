"""Add description column to ble_tags table

Revision ID: 007
Revises: 006
Create Date: 2026-03-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    # Add description column to ble_tags table
    op.add_column('ble_tags', 
        sa.Column('description', sa.String(255), nullable=True, 
                 comment='Vehicle description from MZone API'))


def downgrade():
    # Remove description column from ble_tags table
    op.drop_column('ble_tags', 'description')
