"""Relate categories to conferences

Revision ID: a4eb66c18526
Revises: 824e2d900c44
Create Date: 2019-05-26 19:36:56.708709

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4eb66c18526'
down_revision = '824e2d900c44'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('category', sa.Column('conference_id', sa.Integer()))
    op.create_unique_constraint('uix_conference_category', 'category', ['conference_id', 'name'])
    op.drop_constraint('category_name_key', 'category', type_='unique')
    op.create_foreign_key('category_conference_id_fkey', 'category', 'conference', ['conference_id'], ['conference_id'])
    op.execute(''.join((
        'UPDATE category SET conference_id=(',
        'SELECT conference_id FROM conference LIMIT 1)',
    )))
    op.alter_column('category', 'conference_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('category', 'conference_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.drop_constraint('category_conference_id_fkey', 'category', type_='foreignkey')
    op.create_unique_constraint('category_name_key', 'category', ['name'])
    op.drop_constraint('uix_conference_category', 'category', type_='unique')
    op.drop_column('category', 'conference_id')
    # ### end Alembic commands ###
