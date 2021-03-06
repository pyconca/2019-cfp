"""add talk.requirements

Revision ID: 219a9aa714da
Revises: 67aa6973cc60
Create Date: 2018-06-04 07:45:37.698446

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '219a9aa714da'
down_revision = '67aa6973cc60'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('talk', sa.Column('requirements', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('talk', 'requirements')
    # ### end Alembic commands ###
