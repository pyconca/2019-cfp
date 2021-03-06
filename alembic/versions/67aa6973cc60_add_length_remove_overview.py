"""add length, remove overview

Revision ID: 67aa6973cc60
Revises: 4b6f3303e7da
Create Date: 2018-06-03 21:26:35.561744

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67aa6973cc60'
down_revision = '4b6f3303e7da'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('talk', sa.Column('length', sa.Integer(), nullable=True))
    op.execute("update talk set length = 0")
    op.alter_column("talk", "length", nullable=False)

    op.drop_column('talk', 'overview')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('talk', sa.Column('overview', sa.VARCHAR(length=1024), autoincrement=False, nullable=True))
    op.drop_column('talk', 'length')
    # ### end Alembic commands ###
