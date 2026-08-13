"""update_practice_results_wireframe

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-13 18:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add practice_sessions columns
    op.add_column("practice_sessions", sa.Column("overall_summary", sa.Text(), nullable=True))
    op.add_column("practice_sessions", sa.Column("speech_score", sa.Float(), nullable=True))
    op.add_column("practice_sessions", sa.Column("speech_summary", sa.Text(), nullable=True))
    op.add_column("practice_sessions", sa.Column("speech_metrics", sa.JSON(), nullable=True))
    op.add_column("practice_sessions", sa.Column("video_score", sa.Float(), nullable=True))
    op.add_column("practice_sessions", sa.Column("video_summary", sa.Text(), nullable=True))
    op.add_column("practice_sessions", sa.Column("video_metrics", sa.JSON(), nullable=True))
    op.add_column("practice_sessions", sa.Column("suggestions", sa.JSON(), nullable=True))

    # Add practice_question_remarks columns
    op.add_column("practice_question_remarks", sa.Column("candidate_answer", sa.Text(), nullable=True))
    op.add_column("practice_question_remarks", sa.Column("what_was_missing", sa.Text(), nullable=True))
    op.add_column("practice_question_remarks", sa.Column("area_to_focus", sa.Text(), nullable=True))
    op.add_column("practice_question_remarks", sa.Column("score", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("practice_question_remarks", "score")
    op.drop_column("practice_question_remarks", "area_to_focus")
    op.drop_column("practice_question_remarks", "what_was_missing")
    op.drop_column("practice_question_remarks", "candidate_answer")

    op.drop_column("practice_sessions", "suggestions")
    op.drop_column("practice_sessions", "video_metrics")
    op.drop_column("practice_sessions", "video_summary")
    op.drop_column("practice_sessions", "video_score")
    op.drop_column("practice_sessions", "speech_metrics")
    op.drop_column("practice_sessions", "speech_summary")
    op.drop_column("practice_sessions", "speech_score")
    op.drop_column("practice_sessions", "overall_summary")
