"""Add email delivery records

Revision ID: 7c1a2b3d4e5f
Revises: 8f3b5150e024
Create Date: 2026-05-28 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7c1a2b3d4e5f"
down_revision = "8f3b5150e024"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "email_delivery",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("template", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("email_delivery", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_email_delivery_created_at"), ["created_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_email_delivery_recipient"), ["recipient"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_email_delivery_status"), ["status"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_email_delivery_template"), ["template"], unique=False
        )


def downgrade():
    with op.batch_alter_table("email_delivery", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_email_delivery_template"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_status"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_recipient"))
        batch_op.drop_index(batch_op.f("ix_email_delivery_created_at"))

    op.drop_table("email_delivery")
