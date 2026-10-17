"""
app/modules/audit/repositories/audit_repository.py

Repositori data audit events (jejak audit sistem).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.5.
"""

from app.crud.crud_audit import CRUDAudit


class AuditRepository(CRUDAudit):
    """
    Repositori akses data log audit kejadian sistem per organisasi.
    """
