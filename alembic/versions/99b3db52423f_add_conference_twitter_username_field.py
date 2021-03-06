"""add conference twitter username field

Revision ID: 99b3db52423f
Revises: ebadb425d3af
Create Date: 2019-05-18 17:59:03.229061

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '99b3db52423f'
down_revision = 'ebadb425d3af'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('conference', sa.Column('twitter_username', sa.String(length=15), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('conference', 'twitter_username')
    # ### end Alembic commands ###
