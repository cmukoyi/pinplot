"""add delivery route support to POI

Revision ID: 004
Revises: 003
Create Date: 2026-03-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Add POI type column (defaults to 'single' for existing records)
    op.add_column('pois', sa.Column('poi_type', sa.String(20), nullable=False, server_default='single'))
    
    # Add destination fields for delivery routes
    op.add_column('pois', sa.Column('destination_latitude', sa.Float(), nullable=True))
    op.add_column('pois', sa.Column('destination_longitude', sa.Float(), nullable=True))
    op.add_column('pois', sa.Column('destination_radius', sa.Float(), nullable=True))
    op.add_column('pois', sa.Column('destination_address', sa.String(500), nullable=True))


def downgrade():
    op.drop_column('pois', 'destination_address')
    op.drop_column('pois', 'destination_radius')
    op.drop_column('pois', 'destination_longitude')
    op.drop_column('pois', 'destination_latitude')
    op.drop_column('pois', 'poi_type')
