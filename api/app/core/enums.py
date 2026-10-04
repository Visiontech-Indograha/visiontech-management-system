"""
Enum domain yang identik dengan tipe enum PostgreSQL di `db/01_schema.sql`.

Satu sumber nilai untuk kode Python: pakai anggota enum ini, bukan string lepas, supaya salah ketik
seperti `'EXTENSION'` (seharusnya `'EXTEND'`) atau `'APPLIED'` tidak lolos. Kesetaraan dengan
`pg_enum` dijaga `tests/test_enums.py`.
"""
from enum import StrEnum


class PlanStatus(StrEnum):
    """
    Status dari siklus hidup sebuah Surat Kerja (SK).
    """
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ACCEPTED = "ACCEPTED"
    APPEALED = "APPEALED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETION_REVIEW = "COMPLETION_REVIEW"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DocumentKind(StrEnum):
    """
    Jenis dari dokumen resmi (SK/Adendum).
    """
    INITIAL_ORDER = "INITIAL_ORDER"
    REVISION = "REVISION"
    ADDENDUM = "ADDENDUM"
    PERSONNEL_ADDENDUM = "PERSONNEL_ADDENDUM"


class DocumentStatus(StrEnum):
    """
    Status persetujuan/keberlakuan dari sebuah dokumen resmi.
    """
    AWAITING_ACCEPTANCE = "AWAITING_ACCEPTANCE"
    EFFECTIVE = "EFFECTIVE"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class ChangeType(StrEnum):
    """
    Tipe pengajuan perubahan / adendum SK.
    """
    EXTEND = "EXTEND"
    PERSONNEL = "PERSONNEL"
    AMENDMENT = "AMENDMENT"   # alur SK v2: adendum diajukan ketua saat SK Berjalan


class ChangeStatus(StrEnum):
    """
    Status dari pengajuan perubahan / adendum SK.
    """
    PENDING_PM = "PENDING_PM"
    AWAITING_LEADER_ACCEPTANCE = "AWAITING_LEADER_ACCEPTANCE"
    EFFECTIVE = "EFFECTIVE"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


# nama tipe di PostgreSQL → enum Python
DB_ENUMS: dict[str, type[StrEnum]] = {
    "plan_status": PlanStatus,
    "document_kind": DocumentKind,
    "document_status": DocumentStatus,
    "change_type": ChangeType,
    "change_status": ChangeStatus,
}
