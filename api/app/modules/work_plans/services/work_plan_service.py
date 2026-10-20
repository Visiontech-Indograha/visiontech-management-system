"""
app/modules/work_plans/services/work_plan_service.py

Layanan logika bisnis untuk modul rencana kerja (SK).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3.
"""

from app.services.geocode_service import GeocodeService
from app.services.member_report_service import (
    MemberReportService as BaseMemberReportService,
)
from app.services.plan_amendment_service import (
    PlanAmendmentService as BasePlanAmendmentService,
)
from app.services.plan_assignment_service import (
    PlanAssignmentService as BasePlanAssignmentService,
)
from app.services.plan_attachment_service import (
    PlanAttachmentService as BasePlanAttachmentService,
)
from app.services.plan_change_service import (
    PlanChangeService as BasePlanChangeService,
)
from app.services.plan_day_service import (
    PlanDayService as BasePlanDayService,
)
from app.services.plan_draft_service import (
    PlanDraftService as BasePlanDraftService,
)
from app.services.plan_edit_service import (
    PlanEditService as BasePlanEditService,
)
from app.services.plan_location_service import (
    PlanLocationService as BasePlanLocationService,
)
from app.services.plan_member_service import (
    PlanMemberService as BasePlanMemberService,
)
from app.services.plan_revision_service import (
    PlanRevisionService as BasePlanRevisionService,
)
from app.services.plan_transition_service import (
    PlanTransitionService as BasePlanTransitionService,
)
from app.services.signature_service import SignatureService
from app.shared.documents.pdf_service import (
    html_to_pdf,
    render_final_report_html,
    render_plan_preview_html,
)


class PlanAssignmentService(BasePlanAssignmentService):
    """Layanan seleksi ketersediaan PM dan personel tim."""


class PlanDraftService(BasePlanDraftService):
    """Layanan pembuatan dan konfigurasi draf SK penuh."""


class PlanEditService(BasePlanEditService):
    """Layanan manipulasi dasar SK dan penjadwalan tugas hari."""


class PlanTransitionService(BasePlanTransitionService):
    """Layanan orkestrasi alur status SK (terbit, terima, mulai, selesai)."""


class PlanAmendmentService(BasePlanAmendmentService):
    """Layanan pengajuan dan pengesahan adendum di lapangan."""


class PlanAttachmentService(BasePlanAttachmentService):
    """Layanan pengelolaan lampiran berkas penugasan SK."""


class PlanChangeService(BasePlanChangeService):
    """Layanan perubahan perpanjangan masa tugas dan tim."""


class PlanDayService(BasePlanDayService):
    """Layanan hari kerja dan aktivitas tugas harian."""


class PlanLocationService(BasePlanLocationService):
    """Layanan penentuan lokasi geospasial penugasan SK."""


class PlanMemberService(BasePlanMemberService):
    """Layanan pengelolaan struktur anggota tim SK."""


class MemberReportService(BaseMemberReportService):
    """Layanan pelaporan harian berjenjang anggota dan ketua."""


class PlanRevisionService(BasePlanRevisionService):
    """Layanan revisi draf oleh PM dengan pencatatan diff perubahan."""


__all__ = [
    "GeocodeService",
    "MemberReportService",
    "PlanAmendmentService",
    "PlanAssignmentService",
    "PlanAttachmentService",
    "PlanChangeService",
    "PlanDayService",
    "PlanDraftService",
    "PlanEditService",
    "PlanLocationService",
    "PlanMemberService",
    "PlanRevisionService",
    "PlanTransitionService",
    "SignatureService",
    "html_to_pdf",
    "render_final_report_html",
    "render_plan_preview_html",
]
