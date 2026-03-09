"""Add state tracking to POI tracker links

Revision ID: 006
Revises: 005
Create Date: 2026-03-08

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    """Add last_known_state column to track tracker position state"""
    # Add last_known_state enum column to poi_tracker_links
    # States: 'unknown' (initial), 'inside' (within geofence), 'outside' (outside geofence)
    op.execute("""
        CREATE TYPE geofence_state AS ENUM ('unknown', 'inside', 'outside')
    """)
    
    op.add_column('poi_tracker_links', 
        sa.Column('last_known_state', 
                  sa.Enum('unknown', 'inside', 'outside', name='geofence_state'),
                  nullable=False,
                  server_default='unknown')
    )
    
    # Add timestamp for when state was last checked/updated
    op.add_column('poi_tracker_links',
        sa.Column('last_state_check', 
                  sa.DateTime(timezone=True),
                  nullable=True)
    )


def downgrade():
    """Remove state tracking columns"""
    op.drop_column('poi_tracker_links', 'last_state_check')
    op.drop_column('poi_tracker_links', 'last_known_state')
    op.execute("DROP TYPE geofence_state")
