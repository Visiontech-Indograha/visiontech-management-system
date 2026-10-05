"""Indeks untuk kolom foreign key yang belum terindeks.

Revision ID: 0021_fk_indexes
Revises: 0020_change_type_amendment
Create Date: 2026-10-05

- Hanya tabel induk/biasa. Tabel berpartisi (`attendance`, `qr_scan`, `face_check`) cukup diindeks di induknya:
  PostgreSQL menurunkan indeks ke semua partisi, termasuk partisi bulan baru. Nama partisi tidak ditulis di sini.
- `CREATE INDEX` biasa (bukan CONCURRENTLY): migrasi berjalan dalam satu transaksi, dan CONCURRENTLY ditolak di
  dalam transaksi serta pada tabel berpartisi. Tabel VMS masih kecil, kuncinya singkat.
- `db/*.sql` memuat indeks yang sama (fondasi skema baru = hasil migrasi ini).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0021_fk_indexes"
down_revision: str | None = "0020_change_type_amendment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (nama indeks, tabel, kolom)
_INDEXES: tuple[tuple[str, str, str], ...] = (
    ("ix_attendance_selfie_file_id", "attendance", "selfie_file_id"),
    ("ix_qr_token_issued_by", "qr_token", "issued_by"),
    ("ix_employee_document_uploaded_by", "employee_document", "uploaded_by"),
    ("ix_biometric_consent_recorded_by", "biometric_consent", "recorded_by"),
    ("ix_daily_report_submitted_by", "daily_report", "submitted_by"),
    ("ix_notification_organization_id", "notification", "organization_id"),
    ("ix_overtime_log_reviewed_by", "overtime_log", "reviewed_by"),
    ("ix_file_object_uploaded_by", "file_object", "uploaded_by"),
    ("ix_overtime_log_plan_document_id", "overtime_log", "plan_document_id"),
    ("ix_employee_document_verified_by", "employee_document", "verified_by"),
    ("ix_face_check_matched_employee_id", "face_check", "matched_employee_id"),
    ("ix_final_report_reviewed_by", "final_report", "reviewed_by"),
    ("ix_qr_scan_scanned_by", "qr_scan", "scanned_by"),
    ("ix_asset_return_asset_allocation_id", "asset_return", "asset_allocation_id"),
    ("ix_work_plan_task_done_by", "work_plan_task", "done_by"),
    ("ix_attendance_offline_event_user_id", "attendance_offline_event", "user_id"),
    ("ix_plan_change_requested_by", "plan_change", "requested_by"),
    ("ix_work_plan_deleted_by", "work_plan", "deleted_by"),
    ("ix_face_check_matched_enrollment_id", "face_check", "matched_enrollment_id"),
    ("ix_asset_allocation_driver_employee_id", "asset_allocation", "driver_employee_id"),
    ("ix_plan_document_accepted_by", "plan_document", "accepted_by"),
    ("ix_final_report_submitted_by", "final_report", "submitted_by"),
    ("ix_work_plan_site_id", "work_plan", "site_id"),
    ("ix_asset_return_requested_by", "asset_return", "requested_by"),
    ("ix_plan_change_document_id", "plan_change", "document_id"),
    ("ix_work_plan_created_by", "work_plan", "created_by"),
    ("ix_asset_return_verified_by", "asset_return", "verified_by"),
    ("ix_employee_assignment_unit_id", "employee_assignment", "unit_id"),
    ("ix_attendance_offline_event_organization_id", "attendance_offline_event", "organization_id"),
    ("ix_incident_event_actor_id", "incident_event", "actor_id"),
    ("ix_plan_change_proposed_leader_id", "plan_change", "proposed_leader_id"),
    ("ix_incident_event_incident_id", "incident_event", "incident_id"),
    ("ix_employee_document_supersedes_id", "employee_document", "supersedes_id"),
    ("ix_user_role_unit_id", "user_role", "unit_id"),
    ("ix_user_session_rotated_to", "user_session", "rotated_to"),
    ("ix_plan_change_decided_by", "plan_change", "decided_by"),
    ("ix_weekly_report_reviewed_by", "weekly_report", "reviewed_by"),
    ("ix_work_plan_leader_employee_id", "work_plan", "leader_employee_id"),
    ("ix_face_enrollment_source_file_id", "face_enrollment", "source_file_id"),
    ("ix_plan_document_issued_by", "plan_document", "issued_by"),
    ("ix_user_session_organization_id", "user_session", "organization_id"),
    ("ix_face_enrollment_enrolled_by", "face_enrollment", "enrolled_by"),
    ("ix_asset_allocation_allocated_by", "asset_allocation", "allocated_by"),
    ("ix_asset_allocation_work_plan_id", "asset_allocation", "work_plan_id"),
    ("ix_attendance_device_key_organization_id", "attendance_device_key", "organization_id"),
    ("ix_attendance_site_id", "attendance", "site_id"),
    ("ix_face_enrollment_organization_id", "face_enrollment", "organization_id"),
    ("ix_work_plan_pm_employee_id", "work_plan", "pm_employee_id"),
    ("ix_weekly_report_submitted_by", "weekly_report", "submitted_by"),
    ("ix_incident_report_reported_by", "incident_report", "reported_by"),
    ("ix_qr_scan_image_file_id", "qr_scan", "image_file_id"),
    ("ix_document_signature_revoked_by", "document_signature", "revoked_by"),
    ("ix_notification_work_plan_id", "notification", "work_plan_id"),
    ("ix_work_plan_member_added_by_document_id", "work_plan_member", "added_by_document_id"),
    ("ix_employee_document_file_id", "employee_document", "file_id"),
    ("ix_qr_token_site_id", "qr_token", "site_id"),
    ("ix_incident_report_resolved_by", "incident_report", "resolved_by"),
    ("ix_daily_report_reviewed_by", "daily_report", "reviewed_by"),
    ("ix_document_signature_signing_key_id", "document_signature", "signing_key_id"),
    ("ix_attendance_reviewed_by", "attendance", "reviewed_by"),
    ("ix_face_check_probe_file_id", "face_check", "probe_file_id"),
    ("ix_document_signature_plan_document_id", "document_signature", "plan_document_id"),
)


def upgrade() -> None:
    for name, table, column in _INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON vms.{table} ({column})")


def downgrade() -> None:
    for name, _table, _column in reversed(_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS vms.{name}")
