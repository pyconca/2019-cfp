"""add recording release

Revision ID: f250c66f464e
Revises: 126d519970b8
Create Date: 2018-11-26 20:55:52.959246

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f250c66f464e'
down_revision = '126d519970b8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('conference', sa.Column('recording_release_url', sa.String(length=1024), nullable=False))
    op.add_column('talk', sa.Column('accepted_recording_release', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('talk', 'accepted_recording_release')
    op.drop_column('conference', 'recording_release_url')
    # ### end Alembic commands ###
