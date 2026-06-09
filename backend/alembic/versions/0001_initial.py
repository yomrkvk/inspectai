"""Initial schema — users, inspections, detections, violations, comments

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-09 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("email", sa.String(128), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column("full_name", sa.String(128), nullable=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="inspector"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(), nullable=True),
    )

    # ── inspections ────────────────────────────────────────────────
    op.create_table(
        "inspections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(256), nullable=False),
        sa.Column("original_filename", sa.String(256), nullable=True),
        sa.Column("image_path", sa.String(512), nullable=False),
        sa.Column("annotated_path", sa.String(512), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("image_width", sa.Integer(), nullable=True),
        sa.Column("image_height", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(64), nullable=True),
        # EXIF
        sa.Column("exif_data", sa.JSON(), nullable=True),
        sa.Column("gps_lat", sa.Float(), nullable=True),
        sa.Column("gps_lon", sa.Float(), nullable=True),
        sa.Column("capture_datetime", sa.DateTime(), nullable=True),
        sa.Column("camera_make", sa.String(128), nullable=True),
        sa.Column("camera_model", sa.String(128), nullable=True),
        # Location
        sa.Column("address", sa.String(512), nullable=True),
        sa.Column("district", sa.String(128), nullable=True),
        sa.Column("city", sa.String(128), nullable=True, server_default="Тюмень"),
        # Processing
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("total_detections", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_violations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_inspections_created_at", "inspections", ["created_at"])
    op.create_index("ix_inspections_user_id", "inspections", ["user_id"])
    op.create_index("ix_inspections_status", "inspections", ["status"])

    # ── detections ─────────────────────────────────────────────────
    op.create_table(
        "detections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("inspection_id", sa.String(36), sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bbox_x1", sa.Integer(), nullable=True),
        sa.Column("bbox_y1", sa.Integer(), nullable=True),
        sa.Column("bbox_x2", sa.Integer(), nullable=True),
        sa.Column("bbox_y2", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("class_name", sa.String(64), nullable=True),
        sa.Column("banner_type", sa.String(32), nullable=True),
        sa.Column("classifier_conf", sa.Float(), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
    )
    op.create_index("ix_detections_inspection_id", "detections", ["inspection_id"])

    # ── violations ─────────────────────────────────────────────────
    op.create_table(
        "violations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("detection_id", sa.String(36), sa.ForeignKey("detections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_id", sa.String(36), sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("violation_type", sa.String(64), nullable=True, server_default="other"),
        sa.Column("severity", sa.String(32), nullable=True, server_default="medium"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_id", sa.String(64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_violations_inspection_id", "violations", ["inspection_id"])
    op.create_index("ix_violations_created_at", "violations", ["created_at"])

    # ── comments ───────────────────────────────────────────────────
    op.create_table(
        "comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("inspection_id", sa.String(36), sa.ForeignKey("inspections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(32), nullable=True, server_default="medium"),
        sa.Column("violation_type", sa.String(64), nullable=True, server_default="other"),
        sa.Column("address", sa.String(512), nullable=True),
        sa.Column("gps_lat", sa.Float(), nullable=True),
        sa.Column("gps_lon", sa.Float(), nullable=True),
        sa.Column("photos", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_comments_created_at", "comments", ["created_at"])
    op.create_index("ix_comments_user_id", "comments", ["user_id"])


def downgrade() -> None:
    op.drop_table("comments")
    op.drop_table("violations")
    op.drop_table("detections")
    op.drop_table("inspections")
    op.drop_table("users")
