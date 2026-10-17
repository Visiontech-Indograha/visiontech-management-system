"""
app/modules/work_plans/repositories/work_plan_repository.py

Repositori data rencana kerja (SK), transisi status, tim personel, adendum, dan laporan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.5.
"""

from app.crud.crud_member_report import CRUDMemberReport
from app.crud.crud_plan_access import CRUDPlanAccess
from app.crud.crud_plan_amendment import CRUDPlanAmendment
from app.crud.crud_plan_assignment import CRUDPlanAssignment
from app.crud.crud_plan_attachment import CRUDPlanAttachment
from app.crud.crud_plan_change import CRUDPlanChange
from app.crud.crud_plan_day import CRUDPlanDay
from app.crud.crud_plan_draft import CRUDPlanDraft
from app.crud.crud_plan_edit import CRUDPlanEdit
from app.crud.crud_plan_location import CRUDPlanLocation
from app.crud.crud_plan_member import CRUDPlanMember
from app.crud.crud_plan_revision import CRUDPlanRevision
from app.crud.crud_plan_transition import CRUDPlanTransition


class PlanAssignmentRepository(CRUDPlanAssignment):
    """Repositori opsi penugasan PM dan personel."""


class PlanDraftRepository(CRUDPlanDraft):
    """Repositori pembuatan dan penyuntingan draf SK lengkap."""


class PlanEditRepository(CRUDPlanEdit):
    """Repositori manipulasi dasar rencana kerja dan hari tugas."""


class PlanTransitionRepository(CRUDPlanTransition):
    """Repositori transisi status siklus hidup SK."""


class PlanAmendmentRepository(CRUDPlanAmendment):
    """Repositori adendum dan usulan perubahan saat SK berjalan."""


class PlanAttachmentRepository(CRUDPlanAttachment):
    """Repositori berkas lampiran pendukung SK."""


class PlanChangeRepository(CRUDPlanChange):
    """Repositori permohonan perpanjangan waktu dan perubahan personel."""


class PlanDayRepository(CRUDPlanDay):
    """Repositori rincian hari kerja dan tugas SK."""


class PlanLocationRepository(CRUDPlanLocation):
    """Repositori penetapan titik lokasi dan koordinat geolokasi SK."""


class PlanMemberRepository(CRUDPlanMember):
    """Repositori susunan anggota tim kerja SK."""


class MemberReportRepository(CRUDMemberReport):
    """Repositori laporan harian anggota tim kerja."""


class PlanRevisionRepository(CRUDPlanRevision):
    """Repositori riwayat revisi rencana kerja oleh PM."""


class PlanAccessRepository(CRUDPlanAccess):
    """Repositori validasi otorisasi akses rencana kerja."""


__all__ = [
    "MemberReportRepository",
    "PlanAccessRepository",
    "PlanAmendmentRepository",
    "PlanAssignmentRepository",
    "PlanAttachmentRepository",
    "PlanChangeRepository",
    "PlanDayRepository",
    "PlanDraftRepository",
    "PlanEditRepository",
    "PlanLocationRepository",
    "PlanMemberRepository",
    "PlanRevisionRepository",
    "PlanTransitionRepository",
]
