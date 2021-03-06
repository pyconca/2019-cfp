"""social auth user model updates

Revision ID: e51e178df6ae
Revises: add66992d51f
Create Date: 2018-06-02 20:53:31.807729

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e51e178df6ae'
down_revision = 'add66992d51f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('fullname', sa.String(length=256), nullable=False))
    op.drop_column('user', 'name')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('name', sa.VARCHAR(length=256), autoincrement=False, nullable=False))
    op.drop_column('user', 'fullname')
    # ### end Alembic commands ###
