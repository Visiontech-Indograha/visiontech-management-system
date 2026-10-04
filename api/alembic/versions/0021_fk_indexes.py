"""fk_indexes

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0021'
down_revision: Union[str, None] = '0020_change_type_amendment'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Buat index untuk FK yang belum terindeks
    op.execute('CREATE INDEX IF NOT EXISTS ix_attendance_selfie_file_id ON vms.attendance (selfie_file_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_qr_token_issued_by ON vms.qr_token (issued_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_employee_document_uploaded_by ON vms.employee_document (uploaded_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_biometric_consent_recorded_by ON vms.biometric_consent (recorded_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_daily_report_submitted_by ON vms.daily_report (submitted_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notification_organization_id ON vms.notification (organization_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_overtime_log_reviewed_by ON vms.overtime_log (reviewed_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_file_object_uploaded_by ON vms.file_object (uploaded_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_overtime_log_plan_document_id ON vms.overtime_log (plan_document_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_employee_document_verified_by ON vms.employee_document (verified_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_face_check_matched_employee_id ON vms.face_check (matched_employee_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_face_check_default_matched_enrollment_id ON vms.face_check_default (matched_enrollment_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_final_report_reviewed_by ON vms.final_report (reviewed_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_2026m10_site_id ON vms.attendance_2026m10 (site_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_qr_scan_scanned_by ON vms.qr_scan (scanned_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_asset_return_asset_allocation_id ON vms.asset_return (asset_allocation_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_2026m09_site_id ON vms.attendance_2026m09 (site_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_work_plan_task_done_by ON vms.work_plan_task (done_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_offline_event_user_id ON vms.attendance_offline_event (user_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_plan_change_requested_by ON vms.plan_change (requested_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_work_plan_deleted_by ON vms.work_plan (deleted_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_face_check_matched_enrollment_id ON vms.face_check (matched_enrollment_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_asset_allocation_driver_employee_id ON vms.asset_allocation (driver_employee_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_plan_document_accepted_by ON vms.plan_document (accepted_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_final_report_submitted_by ON vms.final_report (submitted_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_work_plan_site_id ON vms.work_plan (site_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_asset_return_requested_by ON vms.asset_return (requested_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_plan_change_document_id ON vms.plan_change (document_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_work_plan_created_by ON vms.work_plan (created_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_asset_return_verified_by ON vms.asset_return (verified_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_2026m10_reviewed_by ON vms.attendance_2026m10 (reviewed_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_2026m09_reviewed_by ON vms.attendance_2026m09 (reviewed_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_employee_assignment_unit_id ON vms.employee_assignment (unit_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_offline_event_organization_id ON vms.attendance_offline_event (organization_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_incident_event_actor_id ON vms.incident_event (actor_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_plan_change_proposed_leader_id ON vms.plan_change (proposed_leader_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_qr_scan_default_image_file_id ON vms.qr_scan_default (image_file_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_incident_event_incident_id ON vms.incident_event (incident_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_2026m10_selfie_file_id ON vms.attendance_2026m10 (selfie_file_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_2026m09_selfie_file_id ON vms.attendance_2026m09 (selfie_file_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_default_site_id ON vms.attendance_default (site_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_employee_document_supersedes_id ON vms.employee_document (supersedes_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_user_role_unit_id ON vms.user_role (unit_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_user_session_rotated_to ON vms.user_session (rotated_to)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_plan_change_decided_by ON vms.plan_change (decided_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_weekly_report_reviewed_by ON vms.weekly_report (reviewed_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_work_plan_leader_employee_id ON vms.work_plan (leader_employee_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_face_enrollment_source_file_id ON vms.face_enrollment (source_file_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_plan_document_issued_by ON vms.plan_document (issued_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_user_session_organization_id ON vms.user_session (organization_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_face_enrollment_enrolled_by ON vms.face_enrollment (enrolled_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_asset_allocation_allocated_by ON vms.asset_allocation (allocated_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_asset_allocation_work_plan_id ON vms.asset_allocation (work_plan_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_device_key_organization_id ON vms.attendance_device_key (organization_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_site_id ON vms.attendance (site_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_face_enrollment_organization_id ON vms.face_enrollment (organization_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_work_plan_pm_employee_id ON vms.work_plan (pm_employee_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_weekly_report_submitted_by ON vms.weekly_report (submitted_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_incident_report_reported_by ON vms.incident_report (reported_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_qr_scan_image_file_id ON vms.qr_scan (image_file_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_document_signature_revoked_by ON vms.document_signature (revoked_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_default_reviewed_by ON vms.attendance_default (reviewed_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notification_work_plan_id ON vms.notification (work_plan_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_work_plan_member_added_by_document_id ON vms.work_plan_member (added_by_document_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_face_check_default_probe_file_id ON vms.face_check_default (probe_file_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_employee_document_file_id ON vms.employee_document (file_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_qr_token_site_id ON vms.qr_token (site_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_incident_report_resolved_by ON vms.incident_report (resolved_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_daily_report_reviewed_by ON vms.daily_report (reviewed_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_document_signature_signing_key_id ON vms.document_signature (signing_key_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_reviewed_by ON vms.attendance (reviewed_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_default_selfie_file_id ON vms.attendance_default (selfie_file_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_face_check_probe_file_id ON vms.face_check (probe_file_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_qr_scan_default_scanned_by ON vms.qr_scan_default (scanned_by)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_document_signature_plan_document_id ON vms.document_signature (plan_document_id)')
    op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_face_check_default_matched_employee_id ON vms.face_check_default (matched_employee_id)')

def downgrade() -> None:
    pass
