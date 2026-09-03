"""add ssc hsc test scores phone and msc fields to student_profiles

Revision ID: a1b2c3d4e5f6
Revises: 90e7bcbb5a2c
Create Date: 2026-09-03 14:26:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '90e7bcbb5a2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('student_profiles', sa.Column('phone', sa.String(length=50), nullable=True))
    op.add_column('student_profiles', sa.Column('ssc_exam_type', sa.String(length=50), nullable=True))
    op.add_column('student_profiles', sa.Column('ssc_group', sa.String(length=50), nullable=True))
    op.add_column('student_profiles', sa.Column('ssc_result', sa.String(length=50), nullable=True))
    op.add_column('student_profiles', sa.Column('ssc_school', sa.String(length=255), nullable=True))
    op.add_column('student_profiles', sa.Column('ssc_board', sa.String(length=100), nullable=True))
    op.add_column('student_profiles', sa.Column('ssc_year', sa.Integer(), nullable=True))

    op.add_column('student_profiles', sa.Column('hsc_exam_type', sa.String(length=50), nullable=True))
    op.add_column('student_profiles', sa.Column('hsc_group', sa.String(length=50), nullable=True))
    op.add_column('student_profiles', sa.Column('hsc_result', sa.String(length=50), nullable=True))
    op.add_column('student_profiles', sa.Column('hsc_college', sa.String(length=255), nullable=True))
    op.add_column('student_profiles', sa.Column('hsc_board', sa.String(length=100), nullable=True))
    op.add_column('student_profiles', sa.Column('hsc_year', sa.Integer(), nullable=True))

    op.add_column('student_profiles', sa.Column('sat_score', sa.String(length=100), nullable=True))
    op.add_column('student_profiles', sa.Column('gre_score', sa.String(length=100), nullable=True))
    op.add_column('student_profiles', sa.Column('english_score', sa.String(length=150), nullable=True))

    op.add_column('student_profiles', sa.Column('has_msc', sa.Boolean(), nullable=True))
    op.add_column('student_profiles', sa.Column('msc_degree', sa.String(length=255), nullable=True))
    op.add_column('student_profiles', sa.Column('msc_university', sa.String(length=255), nullable=True))
    op.add_column('student_profiles', sa.Column('msc_gpa', sa.Numeric(precision=3, scale=2), nullable=True))
    op.add_column('student_profiles', sa.Column('msc_year', sa.Integer(), nullable=True))
    op.add_column('student_profiles', sa.Column('msc_thesis', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('student_profiles', 'msc_thesis')
    op.drop_column('student_profiles', 'msc_year')
    op.drop_column('student_profiles', 'msc_gpa')
    op.drop_column('student_profiles', 'msc_university')
    op.drop_column('student_profiles', 'msc_degree')
    op.drop_column('student_profiles', 'has_msc')

    op.drop_column('student_profiles', 'english_score')
    op.drop_column('student_profiles', 'gre_score')
    op.drop_column('student_profiles', 'sat_score')

    op.drop_column('student_profiles', 'hsc_year')
    op.drop_column('student_profiles', 'hsc_board')
    op.drop_column('student_profiles', 'hsc_college')
    op.drop_column('student_profiles', 'hsc_result')
    op.drop_column('student_profiles', 'hsc_group')
    op.drop_column('student_profiles', 'hsc_exam_type')

    op.drop_column('student_profiles', 'ssc_year')
    op.drop_column('student_profiles', 'ssc_board')
    op.drop_column('student_profiles', 'ssc_school')
    op.drop_column('student_profiles', 'ssc_result')
    op.drop_column('student_profiles', 'ssc_group')
    op.drop_column('student_profiles', 'ssc_exam_type')
    op.drop_column('student_profiles', 'phone')
