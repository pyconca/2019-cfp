"""add demographic survey

Revision ID: 1c38826de235
Revises: 474a5e05c155
Create Date: 2019-03-10 12:53:31.877955

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c38826de235'
down_revision = '474a5e05c155'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('demographic_survey',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('gender', sa.JSON(), nullable=True),
    sa.Column('ethnicity', sa.JSON(), nullable=True),
    sa.Column('past_speaking', sa.JSON(), nullable=True),
    sa.Column('age_group', sa.Enum('UNDER_18', 'UNDER_25', 'UNDER_35', 'UNDER_45', 'UNDER_55', 'UNDER_65', 'OVER_65', name='agegroup'), nullable=True),
    sa.Column('programming_experience', sa.Enum('UNDER_1YR', 'UNDER_3YR', 'UNDER_6YR', 'UNDER_10YR', 'UNDER_20YR', 'OVER_20YR', name='programmingexperience'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.user_id'], ),
    sa.PrimaryKeyConstraint('user_id'),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('demographic_survey')
    # ### end Alembic commands ###
