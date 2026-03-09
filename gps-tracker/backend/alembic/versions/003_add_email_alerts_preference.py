"""Add email alerts preference to users

Revision ID: 003
Revises: 002
Create Date: 2026-03-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add email_alerts_enabled column to users table
    op.add_column('users', sa.Column('email_alerts_enabled', sa.Boolean(), default=True))
    
    # Set default value for existing users
    op.execute("UPDATE users SET email_alerts_enabled = TRUE")


def downgrade():
    # Remove email_alerts_enabled column
    op.drop_column('users', 'email_alerts_enabled')
